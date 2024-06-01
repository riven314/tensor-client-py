from abc import ABC, abstractmethod

from solana.rpc.api import Client
from solders.hash import Hash
from solders.keypair import Keypair
from solders.rpc.responses import SendTransactionResp


class SolanaBaseClient(ABC):
    def __init__(self, url: str, private_key: str) -> None:
        self.url = url
        self.keypair = self.get_keypair_from_private_key(private_key)
        self.client = Client(self.url)

    @property
    def wallet_address(self) -> str:
        return str(self.keypair.pubkey())

    @abstractmethod
    def execute_transaction(
        self, tx_buffer: list[int], recent_blockhash: Hash | None
    ) -> SendTransactionResp: ...

    @staticmethod
    def get_keypair_from_private_key(private_key: str) -> Keypair:
        return Keypair.from_base58_string(private_key)
