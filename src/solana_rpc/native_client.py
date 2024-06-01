from solana.transaction import Transaction
from solders.rpc.responses import SendTransactionResp

from src.constants import SOLANA_RPC_ENDPOINT
from src.solana_rpc.base_client import SolanaBaseClient


class SolanaNativeClient(SolanaBaseClient):
    def __init__(self, private_key: str) -> None:
        url = SOLANA_RPC_ENDPOINT
        super().__init__(url=url, private_key=private_key)

    def execute_transaction(self, tx_buffer: list[int]) -> SendTransactionResp:
        transaction = Transaction.deserialize(bytes(tx_buffer))
        response = self.client.send_transaction(transaction, self.keypair)
        return response
