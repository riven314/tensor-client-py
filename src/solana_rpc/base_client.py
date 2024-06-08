from abc import ABC, abstractmethod

from solana.rpc.api import Client
from solana.rpc.types import URI
from solders.hash import Hash
from solders.rpc.responses import SendTransactionResp

from src.solana_rpc.utils import get_keypair_from_private_key


class SolanaBaseClient(ABC):
    def __init__(self, url: str, private_key: str) -> None:
        self.keypair = get_keypair_from_private_key(private_key)
        self.client = Client(url)

    @property
    def rpc_endpoint(self) -> URI:
        return self.client._provider.endpoint_uri

    @rpc_endpoint.setter
    def rpc_endpoint(self, url: URI) -> None:
        self.client._provider.endpoint_uri = url

    @property
    def wallet_address(self) -> str:
        return str(self.keypair.pubkey())

    @abstractmethod
    def execute_transaction(
        self, tx_buffer: list[int], recent_blockhash: Hash | None
    ) -> SendTransactionResp: ...
