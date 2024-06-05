from typing import TYPE_CHECKING, Any

import requests
from retry import retry

from src.constants import TENSOR_URL
from src.exceptions import (
    InvalidAPIKeyError,
    TensorServerOverloadError,
    UnclassifiedStatusCodeError,
    UnknownAPIError,
)
from src.logger import logger
from src.solana_rpc.jito_client import SolanaJitoClient
from src.solana_rpc.native_client import SolanaNativeClient

if TYPE_CHECKING:
    from solders.rpc.responses import SendTransactionResp


class TensorBaseClient:
    def __init__(self, api_key: str, private_key: str):
        self.api_key = api_key
        self.init_client()
        self.solana_client = SolanaNativeClient(private_key=private_key)
        self.jito_client = SolanaJitoClient(private_key=private_key)

    def init_client(self) -> None:
        """
        Initialize the Tensor Trade client and the `requests` session.

        Arguments:
            api_key (str): The Tensor Trade API authentication key.
        """
        self.session = requests.session()
        self.session.headers = {
            "Content-Type": "application/json",
            "User-Agent": "tensortradepy",
            "X-TENSOR-API-KEY": self.api_key,
        }

    @retry(
        exceptions=(
            TensorServerOverloadError,
            UnclassifiedStatusCodeError,
            UnknownAPIError,
        ),
        tries=4,
        delay=3,
        backoff=2,
        logger=logger,
    )
    def send_query(self, query: str, variables: dict[str, Any]) -> dict:
        """
        Send a query to the Tensor Trade API.

        Arguments:
            query (str): The GraphQL query.
            variables (dict): The GraphQL variables.
        """
        resp = self.session.post(
            TENSOR_URL,
            json={"query": query, "variables": variables},
        )

        if resp.status_code == 403:
            raise InvalidAPIKeyError
        elif resp.status_code == 520:
            raise TensorServerOverloadError
        elif resp.status_code != 200:
            raise UnclassifiedStatusCodeError(
                f"Unclassified Status code: {resp.status_code}, Text: {resp.text}"
            )
        elif resp.status_code == 200 and "errors" in resp.json():
            raise UnknownAPIError(resp.json()["errors"])

        return resp.json().get("data", {})

    def execute_query_by_native(
        self, query: str, variables: dict[str, Any], name: str
    ) -> "tuple[dict, SendTransactionResp]":
        tensor_resp = self.send_query(query, variables)
        tx_buffer = self._extract_transaction(tensor_resp, name)
        send_tx_resp = self.solana_client.execute_transaction(tx_buffer)
        return tensor_resp, send_tx_resp

    def execute_query_by_jito(
        self, query: str, variables: dict[str, Any], name: str
    ) -> "tuple[dict, SendTransactionResp]":
        tensor_resp = self.send_query(query, variables)
        tx_buffer = self._extract_transaction(tensor_resp, name)
        recent_blockhash = self.solana_client.get_latest_blockhash()
        send_tx_resp = self.jito_client.execute_transaction(tx_buffer, recent_blockhash)
        return tensor_resp, send_tx_resp

    def _extract_transaction(self, data: dict, name: str) -> list[int]:
        return data[name]["txs"][0]["tx"]["data"]
