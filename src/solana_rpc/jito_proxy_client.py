import base64
import json
import os
from random import sample

import base58
import requests
from requests import Response
from requests.exceptions import HTTPError, ProxyError, ReadTimeout, SSLError
from retry import retry
from solana.transaction import Transaction
from solders.hash import Hash
from solders.instruction import Instruction
from solders.pubkey import Pubkey
from solders.rpc.responses import SendTransactionResp
from solders.system_program import TransferParams, transfer

from src.constants import (
    JITO_MAIN_RPC_ENDPOINT,
    JITO_TIP_ACCOUNTS,
    JITO_TIP_IN_SOLAMI,
    EncodingProtocol,
    TransactionStatus,
)
from src.exceptions import BadRequestError
from src.logger import logger
from src.request.proxy_rotator import ProxyRotator
from src.solana_rpc.models import GetBundleStatusesResp, SendBundleResp
from src.solana_rpc.utils import get_keypair_from_private_key


class SolanaProxyJitoClient:
    """
    Reimplement httpx.post request with custom proxy logic
    """

    def __init__(self, private_key: str, proxy_reload_sec: int) -> None:
        self.url = JITO_MAIN_RPC_ENDPOINT
        self.proxy_rotator = ProxyRotator(reload_sec=proxy_reload_sec)
        self.keypair = get_keypair_from_private_key(private_key)

    @property
    def transaction_url(self) -> str:
        return os.path.join(self.url, "api/v1/transactions")

    @property
    def bundle_url(self) -> str:
        return os.path.join(self.url, "api/v1/bundles")

    # unlike native endpoint, it can't search thru the transaction history
    # setting {"searchTransactionHistory": True} as config won't work
    def get_bundle_status(self, bundle_id: str) -> TransactionStatus | None:
        request_kwargs = self._get_bundle_request_kwargs(
            [bundle_id], method_name="getBundleStatuses"
        )
        response = self._rpc_post_request(request_kwargs)
        logger.debug(f"Transaction status: {response.text}")
        response_model = GetBundleStatusesResp(**json.loads(response.text))
        values = response_model.result.value

        if len(values) == 0 or values[0] is None:
            return None
        assert len(values) == 1, f"More than one transaction status: {values}"

        confirmation_status = values[0].confirmation_status
        if confirmation_status == "finalized":
            return TransactionStatus.FINALIZED
        elif confirmation_status == "confirmed":
            return TransactionStatus.CONFIRMED
        elif confirmation_status == "processed":
            return TransactionStatus.PROCESSED
        else:
            raise ValueError(f"Unknown confirmation status: {confirmation_status}")

    def execute_bundle(
        self,
        tx_buffer: list[int],
        recent_blockhash: Hash | None,
    ) -> SendBundleResp:
        assert recent_blockhash, "Recent blockhash is required for Jito transactions"
        transaction = Transaction.deserialize(bytes(tx_buffer))
        response = self.rpc_send_bundle(transaction, recent_blockhash)
        return response

    def execute_transaction(
        self,
        tx_buffer: list[int],
        recent_blockhash: Hash | None,
    ) -> SendTransactionResp:
        assert recent_blockhash, "Recent blockhash is required for Jito transactions"
        transaction = Transaction.deserialize(bytes(tx_buffer))
        response = self.rpc_send_transaction(transaction, recent_blockhash)
        return response

    def rpc_send_bundle(
        self, transaction: Transaction, recent_blockhash: Hash
    ) -> SendBundleResp:
        tip_instruction = self._get_tip_instruction(
            tip_in_solami=int(JITO_TIP_IN_SOLAMI)
        )
        transaction.add(tip_instruction)
        transaction.recent_blockhash = recent_blockhash
        encoded_transaction = self._sign_and_encode_transaction(
            transaction, encoding_protocol=EncodingProtocol.BASE58
        )
        request_kwargs = self._get_bundle_request_kwargs(
            [encoded_transaction], method_name="sendBundle"
        )
        response = self._rpc_post_request(request_kwargs)
        return SendBundleResp(**json.loads(response.text))

    def rpc_send_transaction(
        self, transaction: Transaction, recent_blockhash: Hash
    ) -> SendTransactionResp:
        tip_instruction = self._get_tip_instruction(
            tip_in_solami=int(JITO_TIP_IN_SOLAMI)
        )
        transaction.add(tip_instruction)
        transaction.recent_blockhash = recent_blockhash
        encoded_transaction = self._sign_and_encode_transaction(
            transaction, encoding_protocol=EncodingProtocol.BASE64
        )
        request_kwargs = self._get_transaction_request_kwargs(encoded_transaction)
        response = self._rpc_post_request(request_kwargs)
        return SendTransactionResp.from_json(response.text)  # type: ignore

    # ProxyError reflects malfunction of proxy (often get this error)
    # HTTPError reflects error from requests (Too Many Request Error)
    # SSLError reflects the server refuse the connection because of abuse (we should backoff with longer delay)
    @logger.catch(reraise=True)
    @retry(
        exceptions=(HTTPError, ReadTimeout, SSLError),
        tries=120,
        delay=0.5,
        logger=logger,
    )
    @retry(exceptions=(ProxyError), tries=120, delay=0.5, logger=logger)
    def _rpc_post_request(self, request_kwargs: dict) -> Response:
        proxy = self.proxy_rotator.get_random_proxy()
        logger.info(f"Using proxy: {proxy}")
        request_kwargs["proxies"] = {"https": proxy}

        response = requests.post(**request_kwargs)
        if response.status_code == 400:
            raise BadRequestError(response.text)
        response.raise_for_status()
        return response

    def _get_bundle_request_kwargs(
        self, encoded_bundle: list[str], method_name: str
    ) -> dict:
        params_array = [encoded_bundle]
        return {
            "url": self.bundle_url,
            "headers": {"Content-Type": "application/json"},
            "verify": False,
            "timeout": (5, 10),
            "data": json.dumps(
                {
                    "method": method_name,
                    "jsonrpc": "2.0",
                    "id": 0,
                    "params": params_array,
                }
            ),
        }

    def _get_transaction_request_kwargs(self, encoded_transaction: str) -> dict:
        proxy = self.proxy_rotator.get_random_proxy()
        return {
            "url": self.transaction_url,
            "headers": {"Content-Type": "application/json"},
            "proxies": {"https": proxy},
            "verify": False,
            "timeout": (5, 10),
            "data": json.dumps(
                {
                    "method": "sendTransaction",
                    "jsonrpc": "2.0",
                    "id": 0,
                    "params": [
                        encoded_transaction,
                        {
                            "skipPreflight": True,
                            "preflightCommitment": "finalized",
                            "encoding": "base64",
                            # by default it keep retrying until the transaction is finalized or new blockhash is created
                            "maxRetries": None,
                            "minContextSlot": None,
                        },
                    ],
                }
            ),
        }

    def _sign_and_encode_transaction(
        self, transaction: Transaction, encoding_protocol: EncodingProtocol
    ) -> str:
        transaction.sign(self.keypair)
        serialised_transaction = transaction.serialize()
        if encoding_protocol == EncodingProtocol.BASE58:
            encoded_transaction = base58.b58encode(serialised_transaction).decode(
                "utf-8"
            )
        else:
            encoded_transaction = base64.b64encode(serialised_transaction).decode(
                "utf-8"
            )
        return encoded_transaction

    def _get_tip_instruction(self, tip_in_solami: int) -> Instruction:
        tip_account = sample(JITO_TIP_ACCOUNTS, 1)[0]
        tip_account_pubkey = Pubkey.from_string(tip_account)
        tip_instruction = transfer(
            TransferParams(
                from_pubkey=self.keypair.pubkey(),
                to_pubkey=tip_account_pubkey,
                lamports=tip_in_solami,
            )
        )
        return tip_instruction
