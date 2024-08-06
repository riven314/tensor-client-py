"""
TODO:
1. fill up the missing function
2. test run end to end
3. add pyproject.toml for setting up venv (log guru)
4. integrate with telegram bot
"""

import datetime
import os
from bisect import bisect
from time import sleep

from retry import retry
from solana.rpc.core import RPCException
from solders.rpc.responses import SendTransactionResp

from src.constants import RPCMethod, TransactionStatus
from src.exceptions import PoolAddressChangedError, TransactionMissingError
from src.logger import logger
from src.solana_rpc.models import SendBundleResp
from src.tensor.client import TensorClient
from src.tensor.models import TswapActiveOrderResponse, UserTswapBidResponse

API_KEY = os.environ.get("API_KEY")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
SLUG_DISPLAY = "bando_kids"
RANK = 10
DISCOUNT = 0.94
DELTA_THRESHOLD = 0.03
NEXT_STEP_SEC = 5

if not API_KEY or not PRIVATE_KEY:
    raise Exception("API_KEY and PRIVATE_KEY is required")


def get_bot_bid_price(
    active_bids: list[TswapActiveOrderResponse], is_show_log: bool
) -> float:
    # bid_prices = [bid.bid_price for bid in active_bids]
    # if len(bid_prices) >= RANK:
    #     bid_price = bid_prices[RANK - 1]
    # else:
    #     bid_price = bid_prices[-1]
    #     logger.info(
    #         f"Less then {RANK} active bids, following the last bid price: {bid_price:.5f} SOL"
    #     )
    # assert bid_price is not None
    # return bid_price
    bid_prices = [bid.bid_price for bid in active_bids if bid.bid_price]
    top_bid_price = bid_prices[0]
    discounted_bid_price = round(top_bid_price * DISCOUNT, 5)

    bid_prices = [bid.bid_price for bid in active_bids if bid.bid_price]
    rank_n = 5
    rank_bid_price = (
        bid_prices[rank_n - 1] if len(bid_prices) >= rank_n else bid_prices[-1]
    )
    if discounted_bid_price > rank_bid_price:
        target_bid_price = rank_bid_price - 0.01
        if is_show_log:
            logger.info(
                f"Discounted bid price ({discounted_bid_price:.5f} SOL) is higher than "
                f"the {rank_n}-th bid price ({rank_bid_price:.5f} SOL), "
                f"using adjusted rank bid price ({target_bid_price:.5f} SOL)."
            )
    else:
        target_bid_price = discounted_bid_price
    return target_bid_price


def is_price_drift_too_much(
    active_bids: list[TswapActiveOrderResponse], user_bid: UserTswapBidResponse
) -> tuple[bool, float]:
    # user_bid_price = user_bid.bid_price
    # bid_prices = [bid.bid_price for bid in active_bids]
    # assert user_bid_price
    # current_rank = bisect(bid_prices, user_bid_price)
    # target_bid_price = get_bot_bid_price(active_bids)
    # return abs(current_rank - RANK) >= 2 and user_bid_price != target_bid_price
    user_bid_price = user_bid.bid_price
    assert user_bid_price
    target_bid_price = get_bot_bid_price(active_bids, is_show_log=False)
    delta = abs(user_bid_price - target_bid_price) / target_bid_price
    is_drifted = delta >= DELTA_THRESHOLD
    delta_perc = round(delta * 100, 2)
    return is_drifted, delta_perc


def wait_until_transaction_finalised(
    client: TensorClient,
    transaction_resp: SendTransactionResp | SendBundleResp,
    sleep_sec: int = 2,
    timeout_sec: int = 30,
) -> None:
    tx_hash_id = (
        transaction_resp.value
        if isinstance(transaction_resp, SendTransactionResp)
        else transaction_resp.result
    )

    init_time = datetime.datetime.now(datetime.UTC)
    tx_status = client.get_transaction_status(transaction_resp)
    is_tx_processed = False
    while tx_status != TransactionStatus.FINALIZED:
        if tx_status is not None:
            is_tx_processed = True

        now = datetime.datetime.now(datetime.UTC)
        if not is_tx_processed and (
            now - init_time >= datetime.timedelta(seconds=timeout_sec)
        ):
            raise TransactionMissingError(
                f"Transaction ({tx_hash_id}) is missing for more than {timeout_sec} secs, aborting it..."
            )

        logger.debug(
            f"Transaction status ({tx_hash_id}) not finalized ({tx_status}), repoll after {sleep_sec} seconds..."
        )
        sleep(sleep_sec)
        tx_status = client.get_transaction_status(transaction_resp)


def place_nft_collection_bid_with_wait(
    client: TensorClient, slug: str, bot_bid_price: float, rpc_method: RPCMethod
) -> None:
    _, send_tx_resp = client.place_nft_collection_bid(
        slug=slug, price=bot_bid_price, quantity=1, rpc_method=rpc_method
    )
    logger.info(f"Submitted place bid transaction.")
    wait_until_transaction_finalised(client, send_tx_resp)


def top_up_collection_bid_with_wait(
    client: TensorClient, pool_address: str, amount: float, rpc_method: RPCMethod
) -> None:
    try:
        _, top_up_tx_resp = client.top_up_collection_bid(
            pool_address=pool_address,
            amount=amount,
            rpc_method=rpc_method,
        )
    except RPCException:
        raise PoolAddressChangedError("Pool address has changed, aborting edit bid...")
    except Exception:
        raise

    logger.info(f"Submitted top up sol transaction.")
    wait_until_transaction_finalised(client, top_up_tx_resp)


def edit_nft_collection_bid_with_wait(
    client: TensorClient, pool_address: str, price: float, rpc_method: RPCMethod
) -> None:
    try:
        _, edit_tx_resp = client.edit_nft_collection_bid(
            pool_address=pool_address,
            price=price,
            rpc_method=rpc_method,
        )
    except RPCException:
        raise PoolAddressChangedError("Pool address has changed, aborting edit bid...")
    except Exception:
        raise

    logger.info(f"Submitted edit bid transaction.")
    wait_until_transaction_finalised(client, edit_tx_resp)


@logger.catch(reraise=True)
@retry(
    exceptions=(TransactionMissingError, PoolAddressChangedError),
    tries=3,
    delay=2,
    logger=logger,
)
def run_one_step(client: TensorClient, slug: str, rpc_method: RPCMethod):
    user_bids = client.get_user_nft_bids()
    active_bids = client.get_collection_bids(slug=slug)

    if len(user_bids) == 0:
        logger.info("No bot bid active, placing a new bid")
        active_bids = client.get_collection_bids(slug=slug)
        bot_bid_price = get_bot_bid_price(active_bids, is_show_log=True)
        # wait and check the transaction is in effect
        place_nft_collection_bid_with_wait(
            client, slug, bot_bid_price, rpc_method=rpc_method
        )
        logger.info(f"Bot placed new bid at {bot_bid_price:.8f} SOL")
        return

    if len(user_bids) > 1:
        logger.warning("User has more than 1 active bid, its problematic!!")
        return

    if not user_bids[0].is_in_effect:
        logger.info("User bid is not in effect, probably its filled.")
        return

    user_bid = user_bids[0]
    is_price_shifted, delta_perc = is_price_drift_too_much(active_bids, user_bid)
    if is_price_shifted:
        logger.info(
            f"Bot bid price has drifted too much ({delta_perc:.2f}%), update the existing bid"
        )
        new_bot_bid_price = get_bot_bid_price(active_bids, is_show_log=True)
        sol_delta = new_bot_bid_price - user_bid.sol_balance
        if sol_delta > 0:
            top_up_sol = round(sol_delta * 1.01, 8)
            logger.info(f"Topping up SOL balance by: {top_up_sol:.8f} SOL")
            top_up_collection_bid_with_wait(
                client, user_bid.pool_address, top_up_sol, rpc_method=rpc_method
            )
            logger.info(f"Completed topup of SOL balance by: {top_up_sol:.8f} SOL")

        logger.info(f"Bot updating bid price to: {new_bot_bid_price:.8f} SOL")
        edit_nft_collection_bid_with_wait(
            client, user_bid.pool_address, new_bot_bid_price, rpc_method=rpc_method
        )
        logger.info(f"Bot updated bid price at {new_bot_bid_price:.8f} SOL")

    else:
        logger.debug(
            f"Bot bid price is not drifted ({delta_perc:.2f}%), no action needed (sleeping {NEXT_STEP_SEC} sec)"
        )


client = TensorClient(api_key=API_KEY, private_key=PRIVATE_KEY)
slug = client.get_slug_from_display(slug_display=SLUG_DISPLAY)
assert slug

collection_stats = client.get_collection_stats(slug=slug)
if collection_stats.compressed:
    raise Exception("Collection is compressed, cannot run bot")

current_rpc_method = RPCMethod.JITO
logger.info(
    f"Running bot on collection: {SLUG_DISPLAY}, current RPC method: {current_rpc_method}"
)

while True:
    sleep(NEXT_STEP_SEC)

    try:
        run_one_step(client, slug, rpc_method=current_rpc_method)
    except TransactionMissingError:
        current_rpc_method = (
            RPCMethod.NATIVE if current_rpc_method == RPCMethod.JITO else RPCMethod.JITO
        )
        logger.error(
            "Encounter multiple times of TransactionMissingError, "
            f"switch RPC method to {current_rpc_method} on next step..."
        )
    except Exception as e:
        logger.error("Encounter unknown exception, skip to next step...")
        logger.exception(e)
