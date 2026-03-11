import os
from dotenv import load_dotenv

load_dotenv()


def env_int(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return int(value)


def env_float(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return float(value)

MAX_VALUES = {
    "volume_h24": env_float("DEX_MAX_VOLUME_H24", 250000),
    "price_change_m5": env_float("DEX_MAX_PRICE_CHANGE_M5", 12),
    "price_change_h1": env_float("DEX_MAX_PRICE_CHANGE_H1", 40),
    "txns_buys_m5": env_float("DEX_MAX_TXNS_BUYS_M5", 80),
    "txns_buys_h1": env_float("DEX_MAX_TXNS_BUYS_H1", 240),
    "txns_sells_m5": env_float("DEX_MAX_TXNS_SELLS_M5", 60),
    "txns_m5": env_float("DEX_MAX_TXNS_M5", 140),
    "buy_sell_ratio_m5": env_float("DEX_MAX_BUY_SELL_RATIO_M5", 4),
    "buy_sell_ratio_h1": env_float("DEX_MAX_BUY_SELL_RATIO_H1", 3),
    "volume_acceleration": env_float("DEX_MAX_VOLUME_ACCELERATION", 0.4),
    "liquidity_ratio": env_float("DEX_MAX_VOLUME_LIQUIDITY_RATIO", 6),
}

WEIGHTS = {
    "volume_h24": env_float("DEX_WEIGHT_VOLUME_H24", 0.15),
    "price_change_m5": env_float("DEX_WEIGHT_PRICE_CHANGE_M5", 0.2),
    "price_change_h1": env_float("DEX_WEIGHT_PRICE_CHANGE_H1", 0.15),
    "txns_buys_m5": env_float("DEX_WEIGHT_TXNS_BUYS_M5", 0.1),
    "txns_buys_h1": env_float("DEX_WEIGHT_TXNS_BUYS_H1", 0.1),
    "txns_sells_m5": env_float("DEX_WEIGHT_TXNS_SELLS_M5", 0.05),
    "txns_m5": env_float("DEX_WEIGHT_TXNS_M5", 0.05),
    "buy_sell_ratio_m5": env_float("DEX_WEIGHT_BUY_SELL_RATIO_M5", 0.1),
    "buy_sell_ratio_h1": env_float("DEX_WEIGHT_BUY_SELL_RATIO_H1", 0.05),
    "volume_acceleration": env_float("DEX_WEIGHT_VOLUME_ACCELERATION", 0.03),
    "liquidity_ratio": env_float("DEX_WEIGHT_VOLUME_LIQUIDITY_RATIO", 0.02),
}

FILTER_THRESHOLDS = {
    "min_liquidity": env_float("DEX_FILTER_MIN_LIQUIDITY", 80000),
    "min_volume_h24": env_float("DEX_FILTER_MIN_VOLUME_H24", 30000),
    "min_buys_h24": env_float("DEX_FILTER_MIN_BUYS_H24", 40),
    "min_price_change_m5": env_float("DEX_FILTER_MIN_PRICE_CHANGE_M5", 1.5),
    "min_price_change_h1": env_float("DEX_FILTER_MIN_PRICE_CHANGE_H1", 5),
    "min_buy_sell_ratio_m5": env_float("DEX_FILTER_MIN_BUY_SELL_RATIO_M5", 1.8),
    "min_buy_sell_ratio_h1": env_float("DEX_FILTER_MIN_BUY_SELL_RATIO_H1", 1.2),
    "min_txns_m5": env_float("DEX_FILTER_MIN_TXNS_M5", 20),
    "min_volume_acceleration": env_float("DEX_FILTER_MIN_VOLUME_ACCELERATION", 0.12),
    "max_volume_acceleration": env_float("DEX_FILTER_MAX_VOLUME_ACCELERATION", 0.35),
    "min_volume_liquidity_ratio": env_float("DEX_FILTER_MIN_VOLUME_LIQUIDITY_RATIO", 0.5),
    "max_volume_liquidity_ratio": env_float("DEX_FILTER_MAX_VOLUME_LIQUIDITY_RATIO", 8),
    "max_fdv_liquidity_ratio": env_float("DEX_FILTER_MAX_FDV_LIQUIDITY_RATIO", 20),
    "min_token_age_minutes": env_int("DEX_FILTER_MIN_TOKEN_AGE_MINUTES", 10),
    "max_token_age_hours": env_int("DEX_FILTER_MAX_TOKEN_AGE_HOURS", 72),
    "min_social_links": env_int("DEX_FILTER_MIN_SOCIAL_LINKS", 2),
    "require_website_or_twitter": env_int("DEX_FILTER_REQUIRE_WEBSITE_OR_TWITTER", 1),
    "min_boost_amount": env_float("DEX_FILTER_MIN_BOOST_AMOUNT", 0),
}

MONITOR_SETTINGS = {
    "boosted_token_threshold_score": env_float("DEX_BOOSTED_TOKEN_THRESHOLD_SCORE", 65),
    "min_confirmations": env_int("DEX_ALERT_MIN_CONFIRMATIONS", 2),
    "confirmation_window_seconds": env_int("DEX_ALERT_CONFIRMATION_WINDOW_SECONDS", 900),
    "alert_cooldown_seconds": env_int("DEX_ALERT_COOLDOWN_SECONDS", 21600),
}
