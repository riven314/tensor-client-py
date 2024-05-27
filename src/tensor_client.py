from typing import TYPE_CHECKING

import src.models as models
import src.queries as queries
from src.tensor_base_client import TensorBaseClient
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
            print("No collection found for mint")
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

    def place_nft_collection_bid(self, slug: str, price: float, quantity: int):
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
        return self.execute_query(
            query=queries.TSWAP_PLACE_COLLECTION_BID_QUERY_FACTORY,
            variables=variables,
            name="tswapInitPoolTx",
        )

    def edit_nft_collection_bid(self, pool_address: str, price: float):
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
        return self.execute_query(
            query=queries.TSWAP_EDIT_COLLECTION_BID_QUERY,
            variables=variables,
            name="tswapEditPoolTx",
        )

    def top_up_collection_bid(
        self, whitelist_address: str, top_up: float, price: float
    ):
        wallet_address = self.solana_client.wallet_address
        price_in_solami = str(to_solami(price))
        top_up_in_solami = str(to_solami(top_up))
        config = {
            "poolType": "TOKEN",
            "curveType": "EXPONENTIAL",
            "startingPrice": price_in_solami,
            "delta": "0",
            "mmFeeBps": None,
            "mmCompoundFees": True,
        }
        variables = {
            "action": "DEPOSIT",
            "config": config,
            "lamports": top_up_in_solami,
            "owner": wallet_address,
            "whitelist": whitelist_address,
        }
        return self.execute_query(
            query=queries.TSWAP_TOP_UP_COLLECTION_BID_QUERY,
            variables=variables,
            name="tswapDepositWithdrawSolRawTx",
        )

    def cancel_nft_collection_bid(self, pool_address: str):
        variables = {"pool": pool_address}
        return self.execute_query(
            queries.TSWAP_CANCEL_COLLECTION_BID_TX_QUERY,
            variables,
            name="tswapClosePoolTx",
        )


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
