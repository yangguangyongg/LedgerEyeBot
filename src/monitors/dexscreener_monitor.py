import asyncio
import aiohttp
import os
import logging
import time
from dotenv import load_dotenv
from utils.notifier import Notifier
from utils.config import FILTER_THRESHOLDS, MAX_VALUES, MONITOR_SETTINGS, WEIGHTS
from utils.token_filter import TokenFilter

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
load_dotenv()

LATEST_TOKENS_ENDPOINT = os.getenv("DEX_LATEST_TOKENS_ENDPOINT")
BOOSTED_TOKENS_ENDPOINT = os.getenv("DEX_BOOSTED_TOKENS_ENDPOINT")
POOL_TOKENS_ENDPOINT = os.getenv("DEX_TOKEN_POOL_ENDPOINT")

token_filter = TokenFilter()


def normalize(value, max_value):
    if max_value <= 0:
        return 0
    return min(value / max_value, 1) * 100


def calculate_potential_score(token_data):
    try:
        evaluation = token_filter.evaluate_token(token_data)
        metrics = evaluation["metrics"]
        volume = token_data.get("volume", {}).get("h24", 0)
        price_change_m5 = token_data.get("priceChange", {}).get("m5", 0)
        price_change_h1 = token_data.get("priceChange", {}).get("h1", 0)
        txns_buys_m5 = token_data.get("txns", {}).get("m5", {}).get("buys", 0)
        txns_buys_h1 = token_data.get("txns", {}).get("h1", {}).get("buys", 0)
        txns_sells_m5 = token_data.get("txns", {}).get("m5", {}).get("sells", 0)
        txns_m5 = txns_buys_m5 + txns_sells_m5
        buy_sell_ratio_m5 = metrics.get("buy_sell_ratio_m5", 0)
        buy_sell_ratio_h1 = metrics.get("buy_sell_ratio_h1", 0)
        volume_acceleration = metrics.get("volume_acceleration", 0)
        liquidity_ratio = metrics.get("volume_liquidity_ratio", 0)
        boost_amount = metrics.get("boost_amount", 0)
        has_website = metrics.get("has_website", False)
        has_twitter = metrics.get("has_twitter", False)

        base_token = token_data.get("baseToken", {})
        token_address = base_token.get("address", "N/A")
        logging.info(
            f"token_address: {token_address}, volume: {volume}, price_change_m5: {price_change_m5}, price_change_h1: {price_change_h1}, buys_h24: {txns_buys_m5}, sells_h24: {txns_buys_h1}, txns_sells_m5: {txns_sells_m5}, txns_m5: {txns_m5}")

        volume_score = normalize(volume, MAX_VALUES["volume_h24"]) * WEIGHTS["volume_h24"]
        price_m5_score = normalize(price_change_m5, MAX_VALUES["price_change_m5"]) * WEIGHTS["price_change_m5"]
        price_h1_score = normalize(price_change_h1, MAX_VALUES["price_change_h1"]) * WEIGHTS["price_change_h1"]
        txns_buys_m5_score = normalize(txns_buys_m5, MAX_VALUES["txns_buys_m5"]) * WEIGHTS["txns_buys_m5"]
        txns_buys_h1_score = normalize(txns_buys_h1, MAX_VALUES["txns_buys_h1"]) * WEIGHTS["txns_buys_h1"]
        txns_sells_m5_score = (100 - normalize(txns_sells_m5, MAX_VALUES["txns_sells_m5"])) * WEIGHTS["txns_sells_m5"]
        txns_score = normalize(txns_m5, MAX_VALUES["txns_m5"]) * WEIGHTS["txns_m5"]
        buy_sell_ratio_m5_score = normalize(buy_sell_ratio_m5, MAX_VALUES["buy_sell_ratio_m5"]) * WEIGHTS["buy_sell_ratio_m5"]
        buy_sell_ratio_h1_score = normalize(buy_sell_ratio_h1, MAX_VALUES["buy_sell_ratio_h1"]) * WEIGHTS["buy_sell_ratio_h1"]
        volume_acceleration_score = normalize(volume_acceleration, MAX_VALUES["volume_acceleration"]) * WEIGHTS["volume_acceleration"]
        liquidity_ratio_score = normalize(liquidity_ratio, MAX_VALUES["liquidity_ratio"]) * WEIGHTS["liquidity_ratio"]

        bonus_score = 0
        if buy_sell_ratio_m5 >= FILTER_THRESHOLDS["min_buy_sell_ratio_m5"] * 1.25:
            bonus_score += 6
        if buy_sell_ratio_h1 >= FILTER_THRESHOLDS["min_buy_sell_ratio_h1"] * 1.25:
            bonus_score += 3
        if volume_acceleration >= FILTER_THRESHOLDS["min_volume_acceleration"] * 1.5:
            bonus_score += 4
        if boost_amount > 0:
            bonus_score += 3
        if has_website and has_twitter:
            bonus_score += 2

        penalty_score = min(len(evaluation["reasons"]) * 6, 18)
        total_score = (
            volume_score
            + price_m5_score
            + price_h1_score
            + txns_buys_m5_score
            + txns_buys_h1_score
            + txns_sells_m5_score
            + txns_score
            + buy_sell_ratio_m5_score
            + buy_sell_ratio_h1_score
            + volume_acceleration_score
            + liquidity_ratio_score
            + bonus_score
            - penalty_score
        )
        return round(total_score, 2)
    except Exception as e:
        logging.error(f"calculate_potential_score error: {e}")
        return 0.00


async def fetch_json(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.info(f"Error fetching {url}: {response.status}")
                    return None
    except Exception as e:
        logging.error(f"fetch_json error: {e}")
        return None


async def get_latest_tokens():
    data = await fetch_json(LATEST_TOKENS_ENDPOINT)
    if data is None:
        logging.info("Error fetching latest token profiles")
        return []

    logging.info("Latest tokens fetched")
    return data


async def get_boosted_tokens():
    data = await fetch_json(BOOSTED_TOKENS_ENDPOINT)

    if isinstance(data, list):
        return data
    return []


async def fetch_pool_tokens(chain_id, token_address):
    try:
        url = f"{POOL_TOKENS_ENDPOINT}/{chain_id}/{token_address}"
        data = await fetch_json(url)

        if isinstance(data, list):
            pool_data = data
        elif isinstance(data, dict) and "pairs" in data:
            pool_data = data["pairs"]
        else:
            return None

        if not pool_data:
            return None

        # A token may have multiple trading pairs, select the highest liquidity pair to score the token
        best_pool_data = max(pool_data, key=lambda x: x.get("liquidity", {}).get("usd", 0), default=None)
        return best_pool_data
    except Exception as e:
        logging.error(f"Error fetching pool tokens: {e}")
        return None


class DexScreenerMonitor:
    def __init__(self, notifier: Notifier, interval=60):
        self.notifier = notifier
        self.interval = interval
        self.last_token_ids = set()
        self.last_boosted_ids = set()
        self.pending_alerts = {}
        self.alerted_tokens = {}
        self.min_confirmations = MONITOR_SETTINGS["min_confirmations"]
        self.confirmation_window_seconds = MONITOR_SETTINGS["confirmation_window_seconds"]
        self.alert_cooldown_seconds = MONITOR_SETTINGS["alert_cooldown_seconds"]
        self.score_threshold = MONITOR_SETTINGS["boosted_token_threshold_score"]

    async def process_latest_tokens(self):
        """Monitor newly listed tokens."""
        tokens = await get_latest_tokens()
        if not tokens:
            print("No new tokens")
            return

        new_tokens = [token for token in tokens if token["tokenAddress"] not in self.last_token_ids]
        if not new_tokens:
            return

        for token in new_tokens:
            message = (
                f"🚀 **New Token Listed**\n\n"
                f"**Chain:** {token['chainId'].capitalize()}\n"
                f"**Token Address:** `{token['tokenAddress']}`\n"
                f"🔗 [View on DexScreener]({token['url']})\n"
                f"📝 Description: {token.get('description', 'No description available')}\n"
            )
            await self.notifier.send_message(message)

        self.last_token_ids.update(token["tokenAddress"] for token in new_tokens)

    async def process_boosted_tokens(self):
        try:
            tokens = await get_boosted_tokens()
            if not tokens:
                return

            for token in tokens:
                chain_id = token.get("chainId")
                token_address = token.get("tokenAddress")
                if not chain_id or not token_address:
                    continue

                pool_token_detail = await fetch_pool_tokens(chain_id, token_address)
                if not pool_token_detail:
                    continue

                evaluation = token_filter.evaluate_token(pool_token_detail)
                if not evaluation["passed"]:
                    logging.info(
                        f"Token {token_address} does not meet the filter criteria: {', '.join(evaluation['reasons'])}"
                    )
                    self.pending_alerts.pop(token_address, None)
                    continue

                potential_score = calculate_potential_score(pool_token_detail)
                logging.info(f"token_address: {token_address}, Potential score: {potential_score}")
                if potential_score >= self.score_threshold:
                    await self.process_candidate_alert(pool_token_detail, potential_score, evaluation)
                else:
                    self.pending_alerts.pop(token_address, None)
        except Exception as e:
            logging.error(f"Error processing boosted tokens: {e}")

    async def process_candidate_alert(self, token_data, potential_score, evaluation):
        base_token = token_data.get("baseToken", {})
        token_address = base_token.get("address", "N/A")
        now = time.time()
        last_alert_time = self.alerted_tokens.get(token_address)
        if last_alert_time and now - last_alert_time < self.alert_cooldown_seconds:
            logging.info(f"Token {token_address} skipped due to cooldown")
            return

        candidate = self.pending_alerts.get(token_address)
        if not candidate or now - candidate["first_seen_at"] > self.confirmation_window_seconds:
            self.pending_alerts[token_address] = {
                "confirmations": 1,
                "first_seen_at": now,
                "latest_score": potential_score,
                "evaluation": evaluation,
            }
            logging.info(f"Token {token_address} recorded for first confirmation")
            return

        candidate["confirmations"] += 1
        candidate["latest_score"] = max(candidate["latest_score"], potential_score)
        candidate["evaluation"] = evaluation

        if candidate["confirmations"] < self.min_confirmations:
            logging.info(
                f"Token {token_address} awaiting confirmation {candidate['confirmations']}/{self.min_confirmations}"
            )
            return

        await self.send_potential_token_alert(
            token_data,
            candidate["latest_score"],
            candidate["confirmations"],
            candidate["evaluation"],
        )
        self.alerted_tokens[token_address] = now
        self.pending_alerts.pop(token_address, None)

    async def send_potential_token_alert(self, token_data, potential_score, confirmations, evaluation):
        base_token = token_data.get("baseToken", {})
        name = base_token.get("name", "Unknown")
        symbol = base_token.get("symbol", "N/A")
        address = base_token.get("address", "N/A")
        chain_id = token_data.get("chainId", "N/A")
        liquidity = token_data.get("liquidity", {}).get("usd", 0)
        volume = token_data.get("volume", {}).get("h24", 0)
        price_change = token_data.get("priceChange", {}).get("h24", 0)
        buys = token_data.get("txns", {}).get("h24", {}).get("buys", 0)
        sells = token_data.get("txns", {}).get("h24", {}).get("sells", 0)
        metrics = evaluation.get("metrics", {})
        buy_sell_ratio_m5 = metrics.get("buy_sell_ratio_m5", 0)
        buy_sell_ratio_h1 = metrics.get("buy_sell_ratio_h1", 0)
        volume_acceleration = metrics.get("volume_acceleration", 0)
        fdv_liquidity_ratio = metrics.get("fdv_liquidity_ratio", 0)
        token_age_hours = metrics.get("token_age_hours", 0)
        url = f"https://dexscreener.com/{chain_id}/{address}"

        message = (
            f"🚀 **Potential Token Alert** 🚀\n\n"
            f"🔹 **{name}** ($ {symbol})\n"
            f"🔗 **Chain ID:** {chain_id}\n"
            f"📜 **Contract Address:** `{address}`\n"
            f"💰 **Liquidity:** ${liquidity:,.0f}\n"
            f"📊 **24H Trading Volume:** ${volume:,.0f}\n"
            f"📈 **24H Price Change:** {price_change:.2f}%\n"
            f"🛒 **Buy Transactions:** {buys}\n"
            f"📉 **Sell Transactions:** {sells}\n"
            f"⚖️ **Buy/Sell Ratio (5m):** {buy_sell_ratio_m5:.2f}\n"
            f"⚖️ **Buy/Sell Ratio (1h):** {buy_sell_ratio_h1:.2f}\n"
            f"⏱️ **Volume Acceleration:** {volume_acceleration:.2f}\n"
            f"🏦 **FDV/Liquidity Ratio:** {fdv_liquidity_ratio:.2f}\n"
            f"🕰️ **Token Age:** {token_age_hours:.1f}h\n"
            f"✅ **Confirmations:** {confirmations}\n"
            f"🔥 **Potential Score:** {potential_score:.2f}\n\n"
            f"🔍 [View on DexScreener]({url})"
        )

        await self.notifier.send_message(message)

    async def run(self):
        """Main monitoring loop."""
        while True:
            try:
                # await self.process_latest_tokens()
                await self.process_boosted_tokens()
            except Exception as e:
                logging.error(f"DexScreenerMonitor error: {e}")

            await asyncio.sleep(self.interval)
