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

    def get_active_bids(self, slug: str) -> list[models.TensorswapActiveOrderResponse]:
        variables = {"slug": slug}
        data = self.send_query(queries.TENSORSWAP_ACTIVE_ORDERS_QUERY, variables)
        active_bids = [
            models.TensorswapActiveOrderResponse(**order)
            for order in data["tswapOrders"]
        ]
        active_bids = sorted(
            [bid for bid in active_bids if bid.is_in_effect],
            key=lambda x: x.bid_price,
            reverse=True,
        )
        return active_bids

    # TODO: untest
    # def get_active_listings(
    #     self, slug: str, sort_by: str, filters: dict, limit: int, cursor: dict = None
    # ) -> models.ActiveListingsV2Response:
    #     variables = {
    #         "slug": slug,
    #         "sortBy": sort_by,
    #         "filters": filters,
    #         "limit": limit,
    #         "cursor": cursor,
    #     }
    #     data = self.send_query(queries.ACTIVE_LISTINGS_V2_QUERY, variables)
    #     model = models.ActiveListingsV2Response(**data["activeListingsV2"])
    #     return model

    # TODO: no pydantic model
    def get_user_bids(self) -> dict:
        wallet_address = self.solana_client.wallet_address
        variables = {"owner": wallet_address}
        data = self.send_query(queries.USER_TCOMP_BIDS, variables)
        return data

    def set_nft_collection_bid(self, slug: str, price: float, quantity: int):
        return self.set_cnft_collection_bid(slug, price, quantity)

    # TODO: configurable by more arguments
    def set_cnft_collection_bid(self, slug: str, price: float, quantity: int):
        wallet_address = self.solana_client.wallet_address
        variables = {
            "owner": wallet_address,
            "price": str(to_solami(price)),
            "quantity": quantity,
            "slug": slug,
        }
        query = queries.TCOMP_BID_TX_FOR_COLLECTION_QUERY_FACTORY(
            parameters=[
                ("owner", "String"),
                ("price", "Decimal"),
                ("quantity", "Float"),
                ("slug", "String"),
            ]
        )
        return self.execute_query(query, variables, name="tcompBidTx")

    def cancel_nft_collection_bid(self, bid_address: str):
        return self.cancel_cnft_collection_bid(bid_address)

    def cancel_cnft_collection_bid(self, bid_address: str):
        variables = {"bidStateAddress": bid_address}
        query = queries.TCOMP_CANCEL_COLLECTION_BID_TX_QUERY_FACTORY(
            parameters=[
                ("bidStateAddress", "String"),
            ]
        )
        return self.execute_query(query, variables, name="tcompCancelCollBidTx")
