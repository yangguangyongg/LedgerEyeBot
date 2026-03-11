import logging
import time

from utils.config import FILTER_THRESHOLDS


class TokenFilter:
    def __init__(self):
        self.thresholds = FILTER_THRESHOLDS

    def evaluate_token(self, token_data):
        try:
            liquidity = token_data.get("liquidity", {}).get("usd", 0)
            volume_h24 = token_data.get("volume", {}).get("h24", 0)
            volume_h1 = token_data.get("volume", {}).get("h1", 0)
            volume_m5 = token_data.get("volume", {}).get("m5", 0)
            price_change_m5 = token_data.get("priceChange", {}).get("m5", 0)
            price_change_h1 = token_data.get("priceChange", {}).get("h1", 0)
            price_change_h6 = token_data.get("priceChange", {}).get("h6", 0)
            price_change_h24 = token_data.get("priceChange", {}).get("h24", 0)
            fdv = token_data.get("fdv", 0) or 1
            pair_created_at = token_data.get("pairCreatedAt", 0) / 1000
            token_age_seconds = max(time.time() - pair_created_at, 0)
            token_age_minutes = token_age_seconds / 60
            token_age_hours = token_age_seconds / 3600
            buys_h24 = token_data.get("txns", {}).get("h24", {}).get("buys", 0)
            buys_m5 = token_data.get("txns", {}).get("m5", {}).get("buys", 0)
            sells_m5 = token_data.get("txns", {}).get("m5", {}).get("sells", 0)
            buys_h1 = token_data.get("txns", {}).get("h1", {}).get("buys", 0)
            sells_h1 = token_data.get("txns", {}).get("h1", {}).get("sells", 0)
            txns_m5 = buys_m5 + sells_m5
            buy_sell_ratio_m5 = buys_m5 / max(sells_m5, 1)
            buy_sell_ratio_h1 = buys_h1 / max(sells_h1, 1)
            volume_acceleration = volume_m5 / max(volume_h1, 1)
            volume_liquidity_ratio = volume_h24 / max(liquidity, 1)
            fdv_ratio = fdv / max(liquidity, 1)
            boosts = token_data.get("boosts", {})
            boost_amount = boosts.get("active", 0) or boosts.get("totalAmount", 0) or 0
            info = token_data.get("info", {})
            socials = info.get("socials") or []
            websites = info.get("websites") or []
            social_links = len(socials) + len(websites)
            has_website = bool(websites)
            has_twitter = any(
                social.get("type", "").lower() in {"twitter", "x"}
                for social in socials
                if isinstance(social, dict)
            )
            reasons = []

            logging.info(f"liquidity: {liquidity}, volume_24h: {volume_h24}, price_change_m5: {price_change_m5},"
                         f" fdv: {fdv}, txns_5m: {txns_m5}, token_age_hours: {token_age_hours:.2f}, buys_24h: {buys_h24},"
                         f" volume_5m: {volume_m5}, buy_sell_ratio_m5: {buy_sell_ratio_m5:.2f},"
                         f" buy_sell_ratio_h1: {buy_sell_ratio_h1:.2f}, fdv_ratio: {fdv_ratio:.2f}")

            thresholds = self.thresholds

            if liquidity < thresholds["min_liquidity"]:
                reasons.append("liquidity_below_threshold")
            if volume_h24 < thresholds["min_volume_h24"]:
                reasons.append("volume_h24_below_threshold")
            if buys_h24 < thresholds["min_buys_h24"]:
                reasons.append("buys_h24_below_threshold")
            if price_change_m5 < thresholds["min_price_change_m5"]:
                reasons.append("price_change_m5_below_threshold")
            if price_change_h1 < thresholds["min_price_change_h1"]:
                reasons.append("price_change_h1_below_threshold")
            if buy_sell_ratio_m5 < thresholds["min_buy_sell_ratio_m5"]:
                reasons.append("buy_sell_ratio_m5_below_threshold")
            if buy_sell_ratio_h1 < thresholds["min_buy_sell_ratio_h1"]:
                reasons.append("buy_sell_ratio_h1_below_threshold")
            if txns_m5 < thresholds["min_txns_m5"]:
                reasons.append("txns_m5_below_threshold")
            if volume_acceleration < thresholds["min_volume_acceleration"]:
                reasons.append("volume_acceleration_below_threshold")
            if volume_acceleration > thresholds["max_volume_acceleration"]:
                reasons.append("volume_acceleration_above_threshold")
            if volume_liquidity_ratio < thresholds["min_volume_liquidity_ratio"]:
                reasons.append("volume_liquidity_ratio_below_threshold")
            if volume_liquidity_ratio > thresholds["max_volume_liquidity_ratio"]:
                reasons.append("volume_liquidity_ratio_above_threshold")
            if fdv_ratio > thresholds["max_fdv_liquidity_ratio"]:
                reasons.append("fdv_liquidity_ratio_above_threshold")
            if token_age_minutes < thresholds["min_token_age_minutes"]:
                reasons.append("token_too_new")
            if token_age_hours > thresholds["max_token_age_hours"]:
                reasons.append("token_too_old")
            if social_links < thresholds["min_social_links"]:
                reasons.append("insufficient_social_links")
            if thresholds["require_website_or_twitter"] and not (has_website or has_twitter):
                reasons.append("missing_website_or_twitter")
            if boost_amount < thresholds["min_boost_amount"]:
                reasons.append("boost_amount_below_threshold")

            # filter out highly suspicious pumps with weak participation
            if volume_m5 > 0.5 * max(volume_h24, 1) and txns_m5 < 12:
                reasons.append("possible_volume_manipulation")

            if (
                price_change_m5 < thresholds["min_price_change_m5"]
                and price_change_h1 < thresholds["min_price_change_h1"]
                and price_change_h6 < thresholds["min_price_change_h1"]
                and price_change_h24 < thresholds["min_price_change_h1"]
            ):
                reasons.append("no_multitimeframe_momentum")

            return {
                "passed": not reasons,
                "reasons": reasons,
                "metrics": {
                    "liquidity": liquidity,
                    "volume_h24": volume_h24,
                    "volume_h1": volume_h1,
                    "volume_m5": volume_m5,
                    "price_change_m5": price_change_m5,
                    "price_change_h1": price_change_h1,
                    "price_change_h6": price_change_h6,
                    "price_change_h24": price_change_h24,
                    "buys_h24": buys_h24,
                    "buys_m5": buys_m5,
                    "sells_m5": sells_m5,
                    "buys_h1": buys_h1,
                    "sells_h1": sells_h1,
                    "txns_m5": txns_m5,
                    "buy_sell_ratio_m5": buy_sell_ratio_m5,
                    "buy_sell_ratio_h1": buy_sell_ratio_h1,
                    "volume_acceleration": volume_acceleration,
                    "volume_liquidity_ratio": volume_liquidity_ratio,
                    "fdv_liquidity_ratio": fdv_ratio,
                    "token_age_minutes": token_age_minutes,
                    "token_age_hours": token_age_hours,
                    "social_links": social_links,
                    "boost_amount": boost_amount,
                    "has_website": has_website,
                    "has_twitter": has_twitter,
                },
            }
        except Exception as e:
            print(f"TokenFilter error: {e}")
            return {"passed": False, "reasons": [f"token_filter_error:{e}"], "metrics": {}}

    def filter_token(self, token_data):
        return self.evaluate_token(token_data)["passed"]
