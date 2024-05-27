from solana.rpc.api import Client
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.rpc.responses import SendTransactionResp


class SolanaClient:
    def __init__(self, private_key: str) -> None:
        self.url = "https://api.mainnet-beta.solana.com"
        self.keypair = get_keypair_from_private_key(private_key)
        self.client = Client(self.url)

    @property
    def wallet_address(self) -> str:
        return str(self.keypair.pubkey())

    def execute_transaction(self, tx_buffer: list[int]) -> SendTransactionResp:
        transaction = Transaction.deserialize(bytes(tx_buffer))
        response = self.client.send_transaction(transaction, self.keypair)
        return response


def get_keypair_from_private_key(private_key: str) -> Keypair:
    return Keypair.from_base58_string(private_key)
