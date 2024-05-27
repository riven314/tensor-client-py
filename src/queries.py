from functools import partial

DEFAULT_RETURN = {"txs": {"lastValidBlockHeight": None, "tx": None, "txV0": None}}


def build_tensor_query(name, sub_name, parameters, return_format):
    param_string = [
        f"${param_name}: {param_type}!" for (param_name, param_type) in parameters
    ]
    params = "\n".join(param_string)
    sub_param_string = [
        f"{param_name}: ${param_name}" for (param_name, _) in parameters
    ]
    sub_params = ", ".join(sub_param_string)
    result_fields = []
    for variable, value in return_format.items():
        if value is None:
            result_fields.append(variable)
        else:
            result_fields.append(variable)
            result_fields.append("{")
            for subvariable, subvalue in value.items():
                if subvalue is None:
                    result_fields.append(subvariable)
            result_fields.append("}")
    result_variables = "\n".join(result_fields)
    return """query %s(
  %s
) {
  %s(%s) {
    %s
  }
}
""" % (
        name,
        params,
        sub_name,
        sub_params,
        result_variables,
    )


COLLECTION_STATS_QUERY = """query CollectionsStats($slug: String!) {
    instrumentTV2(slug: $slug) {
        id
        slug
        firstListDate
        compressed
        name
        statsV2 {
            currency
            buyNowPrice
            buyNowPriceNetFees
            sellNowPrice
            sellNowPriceNetFees
            numListed
            numMints
        }
    }
}
"""

TCOMP_BIDS_QUERY = """
query TcompBids($slug: String!) {
  tcompBids(slug: $slug) {
    address
    amount
    createdAt
    field
    fieldId
    filledQuantity
    margin
    marginNr
    ownerAddress
    quantity
    solBalance
    target
    targetId
  }
}
"""


ACTIVE_LISTINGS_V2_QUERY = """
query ActiveListingsV2(
  $slug: String!
  $sortBy: ActiveListingsSortBy!
  $filters: ActiveListingsFilters
  $limit: Int
  $cursor: ActiveListingsCursorInputV2
) {
  activeListingsV2(
    slug: $slug
    sortBy: $sortBy
    filters: $filters
    limit: $limit
    cursor: $cursor
  ) {
    page {
      endCursor {
        str
      }
      hasMore
    }
    txs {
      mint {
        onchainId
      }
      tx {
        sellerId
        grossAmount
        grossAmountUnit
      }
    }
  }
}
"""


MINT_QUERY = """query Mint($mint: String!) {
  mint(mint: $mint) {
    slug
  } 
}"""


USER_TCOMP_BIDS = """query UserTcompBids($owner: String!) {
  userTcompBids(owner: $owner) {
    bid {
      address
      amount
      field
      fieldId
      filledQuantity
      quantity
      solBalance
      target
      targetId
    }
    collInfo {
      slug
    }
  }
}"""


COLLECTION_SLUG_QUERY = """query CollectionsStats(
  $slugsDisplay: [String!],
) {
  allCollections(
    slugsDisplay: $slugsDisplay
  ) {
    total
    collections {
      id
      slug
      slugDisplay
    }
  }
}"""


TENSORSWAP_ACTIVE_ORDERS_QUERY = """query TensorSwapActiveOrders($slug: String!) {
  tswapOrders(slug: $slug) {
    address
    createdUnix
    curveType
    delta
    mmCompoundFees
    mmFeeBps
    nftsForSale {
      onchainId
    }
    nftsHeld
    ownerAddress
    poolType
    solBalance
    startingPrice
		buyNowPrice
    sellNowPrice
    statsAccumulatedMmProfit
    statsTakerBuyCount
    statsTakerSellCount
    takerBuyCount
    takerSellCount
    updatedAt
  }
}"""

TCOMP_BID_TX_FOR_COLLECTION_QUERY_FACTORY = partial(
    build_tensor_query,
    name="TcompBidTxForCollection",
    sub_name="tcompBidTx",
    return_format=DEFAULT_RETURN,
)


TCOMP_CANCEL_COLLECTION_BID_TX_QUERY_FACTORY = partial(
    build_tensor_query,
    name="TcompCancelCollBidTx",
    sub_name="tcompCancelCollBidTx",
    return_format=DEFAULT_RETURN,
)
