from solders.rpc.responses import SendTransactionResp
from solders.transaction_status import TransactionConfirmationStatus

import src.tensor.models as models
import src.tensor.queries as queries
from src.logger import logger
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
            key=lambda x: x.bid_price,
            reverse=True,
        )
        return active_bids

    def place_nft_collection_bid(
        self, slug: str, price: float, quantity: int, rpc: str
    ):
        assert rpc in ("native", "jito"), "Invalid RPC type"

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

        rpc_method = (
            self.execute_query_by_native
            if rpc == "native"
            else self.execute_query_by_jito
        )
        return rpc_method(
            query=queries.TSWAP_PLACE_COLLECTION_BID_QUERY_FACTORY,
            variables=variables,
            name="tswapInitPoolTx",
        )

    def edit_nft_collection_bid(self, pool_address: str, price: float, rpc: str):
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
        rpc_method = (
            self.execute_query_by_native
            if rpc == "native"
            else self.execute_query_by_jito
        )
        return rpc_method(
            query=queries.TSWAP_EDIT_COLLECTION_BID_QUERY,
            variables=variables,
            name="tswapEditPoolTx",
        )

    def top_up_collection_bid(self, pool_address: str, amount: float, rpc: str):
        amount_in_solami = str(to_solami(amount))
        variables = {
            "action": "DEPOSIT",
            "lamports": amount_in_solami,
            "pool": pool_address,
        }
        rpc_method = (
            self.execute_query_by_native
            if rpc == "native"
            else self.execute_query_by_jito
        )
        return rpc_method(
            query=queries.TSWAP_TOP_UP_COLLECTION_BID_QUERY,
            variables=variables,
            name="tswapDepositWithdrawSolTx",
        )

    def cancel_nft_collection_bid(self, pool_address: str, rpc: str):
        variables = {"pool": pool_address}
        rpc_method = (
            self.execute_query_by_native
            if rpc == "native"
            else self.execute_query_by_jito
        )
        return rpc_method(
            queries.TSWAP_CANCEL_COLLECTION_BID_QUERY_FACTORY,
            variables,
            name="tswapClosePoolTx",
        )

    def get_transaction_status(
        self, transaction_resp: SendTransactionResp
    ) -> TransactionConfirmationStatus | None:
        return self.solana_client.get_transaction_status(transaction_resp)


#     send_tx_resp = client.set_cnft_collection_bid(slug=slug, price=0.18, quantity=1)
#     status_tx = client.solana_client.client.get_signature_statuses([send_tx_resp.value])
#     while ((status := status_tx.value[0]) is None) or (
#         (status := status_tx.value[0].confirmation_status)
#     ) != TransactionConfirmationStatus.Finalized:
#         print(f"Transaction is not finalized ({status}), waiting until its finalized")
#         sleep(1)
#         status_tx = client.solana_client.client.get_signature_statuses(
#             [send_tx_resp.value]
#         )
