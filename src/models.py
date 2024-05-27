from pydantic import BaseModel

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


class TensorswapActiveOrderResponse(BaseModel):
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


class UserBidResponse(BaseModel):
    address: str
    amount: str
    field: str | None
    fieldId: str | None
    filledQuantity: int
    quantity: int
    solBalance: str
    target: str
    targetId: str

    @property
    def sol_balance(self) -> float:
        return from_solami(float(self.solBalance))
