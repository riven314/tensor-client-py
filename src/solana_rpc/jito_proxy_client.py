import base64
import json
from random import sample

import requests
from requests.exceptions import HTTPError, ProxyError, SSLError
from retry import retry
from solana.transaction import Transaction
from solders.hash import Hash
from solders.instruction import Instruction
from solders.pubkey import Pubkey
from solders.rpc.responses import SendTransactionResp
from solders.system_program import TransferParams, transfer

from src.constants import JITO_MAIN_RPC_ENDPOINT, JITO_TIP_ACCOUNTS, JITO_TIP_IN_SOLAMI
from src.logger import logger
from src.request.proxy_rotator import ProxyRotator
from src.solana_rpc.utils import get_keypair_from_private_key


class SolanaProxyJitoClient:
    """
    Reimplement httpx.post request with custom proxy logic
    """

    def __init__(self, private_key: str, proxy_reload_sec: int) -> None:
        self.url = JITO_MAIN_RPC_ENDPOINT
        self.proxy_rotator = ProxyRotator(reload_sec=proxy_reload_sec)
        self.keypair = get_keypair_from_private_key(private_key)

    def execute_transaction(
        self,
        tx_buffer: list[int],
        recent_blockhash: Hash | None,
    ) -> SendTransactionResp:
        assert recent_blockhash, "Recent blockhash is required for Jito transactions"
        transaction = Transaction.deserialize(bytes(tx_buffer))
        response = self.send_jito_transaction(transaction, recent_blockhash)
        return response

    # ProxyError reflects malfunction of proxy
    # HTTPError reflects error from requests (Too Many Request Error)
    @logger.catch(reraise=True)
    @retry(exceptions=(HTTPError,), tries=60, delay=1, logger=logger)
    @retry(exceptions=(ProxyError, SSLError), tries=60, delay=1, logger=logger)
    def send_jito_transaction(
        self, transaction: Transaction, recent_blockhash: Hash
    ) -> SendTransactionResp:
        tip_instruction = self._get_tip_instruction(
            tip_in_solami=int(JITO_TIP_IN_SOLAMI)
        )
        transaction.add(tip_instruction)
        transaction.recent_blockhash = recent_blockhash
        encoded_transaction = self._sign_and_encode_transaction(transaction)

        request_kwargs = self._get_request_kwargs(encoded_transaction)
        response = requests.post(**request_kwargs)
        response.raise_for_status()
        return SendTransactionResp.from_json(response.text)  # type: ignore

    def _get_request_kwargs(self, encoded_transaction: str) -> dict:
        proxy = self.proxy_rotator.get_random_proxy()
        request_kwargs = {
            "url": self.url,
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

        return request_kwargs

    def _sign_and_encode_transaction(self, transaction: Transaction) -> str:
        transaction.sign(self.keypair)
        serialised_transaction = transaction.serialize()
        encoded_transaction = base64.b64encode(serialised_transaction).decode("utf-8")
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
