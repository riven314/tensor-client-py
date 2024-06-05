from pydantic import BaseModel

from src.logger import logger
from src.utils import from_solami


class CollectionStats(BaseModel):
    currency: str | None
    buyNowPrice: str
    buyNowPriceNetFees: str
    sellNowPrice: str
    sellNowPriceNetFees: str
    numListed: int
    numMints: int


class CollectionStatsResponse(BaseModel):
    id: str
    slug: str
    firstListDate: int
    compressed: bool
    name: str
    statsV2: CollectionStats

    @property
    def top_ask_price(self):
        return from_solami(float(self.statsV2.buyNowPrice))

    @property
    def top_bid_price(self):
        return from_solami(float(self.statsV2.sellNowPrice))


class TcompBid(BaseModel):
    address: str
    amount: str
    createdAt: str
    field: str
    fieldId: str
    filledQuantity: str
    margin: str
    marginNr: str
    ownerAddress: str
    quantity: str
    solBalance: str
    target: str
    targetId: str
    attributes: list


class TcompBidsResponse(BaseModel):
    tcompBids: list[TcompBid]


class ActiveListingMint(BaseModel):
    onchainId: str


class ActiveListingTx(BaseModel):
    sellerId: str
    grossAmount: str
    grossAmountUnit: str


class ActiveListingsPage(BaseModel):
    str: str
    hasMore: bool


class ActiveListingsV2Response(BaseModel):
    page: ActiveListingsPage
    txs: list[ActiveListingTx]


class TswapActiveOrderResponse(BaseModel):
    address: str
    createdUnix: int
    curveType: str
    delta: str
    mmCompoundFees: bool
    mmFeeBps: int | None
    nftsForSale: list[dict]
    nftsHeld: int
    ownerAddress: str
    poolType: str
    solBalance: str
    startingPrice: str
    buyNowPrice: str | None
    sellNowPrice: str
    statsAccumulatedMmProfit: str
    statsTakerBuyCount: int
    statsTakerSellCount: int
    takerBuyCount: int
    takerSellCount: int
    updatedAt: int

    @property
    def bid_price(self) -> float:
        return from_solami(float(self.sellNowPrice))

    @property
    def sol_balance(self) -> float:
        return from_solami(float(self.solBalance))

    @property
    def is_in_effect(self) -> bool:
        return self.sol_balance >= self.bid_price


class TswapBidPool(BaseModel):
    address: str
    currentActive: bool
    buyNowPrice: str | None
    createdAt: int
    sellNowPrice: str | None
    solBalance: str
    startingPrice: str
    whitelistAddress: str


class UserTswapBidResponse(BaseModel):
    collName: str
    slug: str
    pool: TswapBidPool

    @property
    def whitelist_address(self) -> str:
        return self.pool.whitelistAddress

    @property
    def pool_address(self) -> str:
        return self.pool.address

    @property
    def sol_balance(self) -> float:
        return from_solami(float(self.pool.solBalance))

    @property
    def bid_price(self) -> float:
        assert self.pool.sellNowPrice
        return from_solami(float(self.pool.sellNowPrice))

    @property
    def is_in_effect(self) -> bool:
        if not self.bid_price:
            logger.warning(f"Bid price is None, something is wrong: {self.pool}")
            return False
        return self.sol_balance >= self.bid_price
