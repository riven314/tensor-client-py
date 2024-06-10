from retry import retry
from solana.exceptions import SolanaRpcException
from solana.transaction import Transaction
from solders.hash import Hash
from solders.rpc.responses import SendTransactionResp
from solders.transaction_status import TransactionConfirmationStatus

from src.constants import SOLANA_RPC_ENDPOINT, TransactionStatus
from src.logger import logger
from src.solana_rpc.base_client import SolanaBaseClient


class SolanaNativeClient(SolanaBaseClient):
    def __init__(self, private_key: str) -> None:
        url = SOLANA_RPC_ENDPOINT
        super().__init__(url=url, private_key=private_key)

    @logger.catch(reraise=True)
    @retry(exceptions=(SolanaRpcException,), tries=4, delay=3, backoff=2, logger=logger)
    def execute_transaction(
        self, tx_buffer: list[int], recent_blockhash: Hash | None = None
    ) -> SendTransactionResp:
        transaction = Transaction.deserialize(bytes(tx_buffer))
        response = self.client.send_transaction(
            transaction, self.keypair, recent_blockhash=recent_blockhash
        )
        return response

    def get_latest_blockhash(self) -> Hash:
        blockhash_resp = self.client.get_latest_blockhash()
        return self.client._process_blockhash_resp(
            blockhash_resp, used_immediately=True
        )

    @retry(exceptions=(SolanaRpcException,), tries=4, delay=2, backoff=2, logger=logger)
    def get_transaction_status(
        self,
        transaction_resp: SendTransactionResp,
        search_transaction_history: bool = True,
    ) -> TransactionStatus | None:
        # search_transaction_history is False, it would only search on the recent status cache from RPC node
        status_resp = self.client.get_signature_statuses(
            [transaction_resp.value],
            search_transaction_history=search_transaction_history,
        )
        logger.debug(f"Transaction status: {status_resp.to_json()}")
        assert (
            len(status_resp.value) == 1
        ), f"More than one transaction status: {status_resp.value}"
        if status_resp.value[0] is None:
            return None

        confirmation_status = status_resp.value[0].confirmation_status
        if confirmation_status == TransactionConfirmationStatus.Finalized:
            return TransactionStatus.FINALIZED
        elif confirmation_status == TransactionConfirmationStatus.Confirmed:
            return TransactionStatus.CONFIRMED
        elif confirmation_status == TransactionConfirmationStatus.Processed:
            return TransactionStatus.PROCESSED
        else:
            raise ValueError(f"Unknown confirmation status: {confirmation_status}")
