from typing import Union

from solders.rpc.responses import SendTransactionResp

import src.tensor.models as models
import src.tensor.queries as queries
from src.constants import RPCMethod, TransactionStatus
from src.logger import logger
from src.solana_rpc.models import SendBundleResp
from src.tensor.base_client import TensorBaseClient
from src.utils import to_solami


class TensorClient(TensorBaseClient):
    def __init__(self, api_key: str, private_key: str):
        super().__init__(api_key, private_key)

    def get_collection_stats(self, slug: str) -> models.CollectionStatsResponse:
        variables = {"slug": slug}
        data = self.send_query(queries.COLLECTION_STATS_QUERY, variables)
        model = models.CollectionStatsResponse(**data["instrumentTV2"])
        return model

    def get_slug_from_display(self, slug_display: str) -> str | None:
        variables = {"slugsDisplay": [slug_display]}
        data = self.send_query(queries.COLLECTION_SLUG_QUERY, variables)
        if len(data["allCollections"]["collections"]) == 0:
            logger.warning("No collection found for mint")
            return None
        return data["allCollections"]["collections"][0]["slug"]

    def get_user_nft_bids(self) -> list[models.UserTswapBidResponse]:
        wallet_address = self.solana_client.wallet_address
        variables = {"owner": wallet_address}
        data = self.send_query(queries.USER_TSWAP_ORDERS, variables)
        return [models.UserTswapBidResponse(**bid) for bid in data["userTswapOrders"]]

    def get_collection_bids(self, slug: str) -> list[models.TswapActiveOrderResponse]:
        variables = {"slug": slug}
        data = self.send_query(queries.TSWAP_ACTIVE_ORDERS_QUERY, variables)
        active_bids = [
            models.TswapActiveOrderResponse(**order) for order in data["tswapOrders"]
        ]
        active_bids = sorted(
            [bid for bid in active_bids if bid.is_in_effect],
            key=lambda x: x.bid_price if x.bid_price else -1,
            reverse=True,
        )
        return active_bids

    def place_nft_collection_bid(
        self, slug: str, price: float, quantity: int, rpc_method: RPCMethod
    ):
        wallet_address = self.solana_client.wallet_address
        price_in_solami = str(to_solami(price))
        deposit_in_solami = str(to_solami(price * quantity))
        variables = {
            "config": {
                "poolType": "TOKEN",
                "curveType": "EXPONENTIAL",
                "startingPrice": price_in_solami,
                "delta": "0",
                "mmFeeBps": None,
                "mmCompoundFees": True,
            },
            "owner": wallet_address,
            "slug": slug,
            "depositLamports": deposit_in_solami,
            "topUpMarginWhenBidding": True,
            "priorityMicroLamports": 50000,
        }
        return self._execute_query(
            query=queries.TSWAP_PLACE_COLLECTION_BID_QUERY,
            variables=variables,
            name="tswapInitPoolTx",
            rpc_method=rpc_method,
        )

    def edit_nft_collection_bid(
        self, pool_address: str, price: float, rpc_method: RPCMethod
    ):
        price_in_solami = str(to_solami(price))
        new_config = {
            "poolType": "TOKEN",
            "curveType": "EXPONENTIAL",
            "startingPrice": price_in_solami,
            "delta": "0",
            "mmFeeBps": None,
            "mmCompoundFees": True,
        }
        variables = {
            "pool": pool_address,
            "newConfig": new_config,
        }
        return self._execute_query(
            query=queries.TSWAP_EDIT_COLLECTION_BID_QUERY,
            variables=variables,
            name="tswapEditPoolTx",
            rpc_method=rpc_method,
        )

    def top_up_collection_bid(
        self, pool_address: str, amount: float, rpc_method: RPCMethod
    ):
        amount_in_solami = str(to_solami(amount))
        variables = {
            "action": "DEPOSIT",
            "lamports": amount_in_solami,
            "pool": pool_address,
        }
        return self._execute_query(
            query=queries.TSWAP_TOP_UP_COLLECTION_BID_QUERY,
            variables=variables,
            name="tswapDepositWithdrawSolTx",
            rpc_method=rpc_method,
        )

    def cancel_nft_collection_bid(self, pool_address: str, rpc_method: RPCMethod):
        variables = {"pool": pool_address}
        return self._execute_query(
            query=queries.TSWAP_CANCEL_COLLECTION_BID_QUERY,
            variables=variables,
            name="tswapClosePoolTx",
            rpc_method=rpc_method,
        )

    def get_transaction_status(
        self, transaction_resp: SendTransactionResp | SendBundleResp
    ) -> TransactionStatus | None:
        if isinstance(transaction_resp, SendTransactionResp):
            return self.solana_client.get_transaction_status(transaction_resp)
        else:
            return self.jito_client.get_bundle_status(transaction_resp.result)

    def _execute_query(
        self,
        query: str,
        variables: dict,
        name: str,
        rpc_method: RPCMethod,
    ) -> tuple[dict, Union[SendTransactionResp, SendBundleResp]]:
        logger.info(f"Executing tensor query in {rpc_method} mode")
        rpc_func = (
            self.execute_query_by_jito
            if rpc_method == RPCMethod.JITO
            else self.execute_query_by_native
        )
        return rpc_func(query=query, variables=variables, name=name)  # type: ignore
