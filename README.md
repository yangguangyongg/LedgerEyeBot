# LedgerEyeBot

LedgerEyeBot is a Python-based crypto monitoring bot focused on surfacing token opportunities and sending alerts to Telegram. The current implementation primarily monitors DexScreener data, filters boosted tokens, scores their short-term momentum, and pushes potential-token alerts to a Telegram chat.

## What the project does

The repository currently contains two runnable entry points:

- `main.py`: starts the monitoring bot
- `airdrop.py`: sends SOL to a list of recipient wallets on Solana

The main monitoring flow is centered on DexScreener:

- Polls the DexScreener boosted-token endpoint
- Fetches pool data for each candidate token
- Filters out weak or suspicious tokens using liquidity, volume, price movement, transaction count, and social-presence checks
- Calculates a weighted potential score from market activity
- Sends alerts to Telegram when the score passes a configured threshold

The codebase also contains early blockchain-monitoring modules for Solana and Ethereum wallet tracking:

- `src/monitors/solana_monitor.py`
- `src/monitors/ethereum_monitor.py`

These modules are present in the repository, but they are not currently enabled in `main.py`. The Solana transaction parsing path is still incomplete, so the default supported runtime path today is the DexScreener monitor.

## Project structure

```text
.
├── main.py                      # Main monitoring entry point
├── airdrop.py                   # Solana batch transfer script
├── requirements.txt
├── Dockerfile
└── src
    ├── monitors
    │   ├── base_blockchain_monitor.py
    │   ├── dexscreener_monitor.py
    │   ├── ethereum_monitor.py
    │   └── solana_monitor.py
    └── utils
        ├── chain_analytics.py
        ├── config.py
        ├── notifier.py
        ├── task_manager.py
        └── token_filter.py
```

## Requirements

- Python 3.11
- A Telegram bot token
- A Telegram chat ID for receiving alerts
- RPC endpoints if you plan to use Solana or Ethereum related scripts
- DexScreener API endpoints configured through environment variables

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root. You can start from `.env.example`.

### Required for the current default monitor

```env
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
DEX_LATEST_TOKENS_ENDPOINT=
DEX_BOOSTED_TOKENS_ENDPOINT=
DEX_TOKEN_POOL_ENDPOINT=
DEX_BOOSTED_TOKEN_THRESHOLD_SCORE=
```

### Optional RPC settings

```env
SOLANA_RPC_URL=
ETHEREUM_RPC_URL=
ETH_MONITOR_INTERVAL=
```

### Optional scoring settings

If you want to tune the DexScreener scoring model in `src/utils/config.py`, set these values in `.env`:

```env
DEX_MAX_VOLUME_H24=
DEX_MAX_PRICE_CHANGE_M5=
DEX_MAX_PRICE_CHANGE_H1=
DEX_MAX_TXNS_BUYS_M5=
DEX_MAX_TXNS_BUYS_H1=
DEX_MAX_TXNS_SELLS_M5=
DEX_MAX_TXNS_M5=

DEX_WEIGHT_VOLUME_H24=
DEX_WEIGHT_PRICE_CHANGE_M5=
DEX_WEIGHT_PRICE_CHANGE_H1=
DEX_WEIGHT_TXNS_BUYS_M5=
DEX_WEIGHT_TXNS_BUYS_H1=
DEX_WEIGHT_TXNS_SELLS_M5=
DEX_WEIGHT_TXNS_M5=
```

If these scoring values are not configured, the score calculation may not behave as expected.

## How to run

### Start the monitoring bot

```bash
python main.py
```

What this currently starts:

- Telegram notifier
- async task manager
- DexScreener boosted-token monitoring loop

### Run with Docker

```bash
docker build -t ledgereyebot .
docker run --env-file .env ledgereyebot
```

### Run the SOL airdrop script

`airdrop.py` is a separate utility for sending SOL to multiple Solana addresses.

Before running it, make sure:

- `payer.json` exists and contains the payer private key array
- `RECIPIENTS` in `airdrop.py` has been filled
- `CLUSTER` and `AMOUNT_SOL` are set correctly

Then run:

```bash
python airdrop.py
```

## Current behavior and limitations

- `main.py` currently enables only the DexScreener monitor
- Solana wallet monitoring code exists, but transaction parsing is still placeholder/TODO level
- Ethereum wallet monitoring code exists, but it is not enabled in the default entry point
- There are no automated tests in the current repository
- `.env.example` does not yet include all optional scoring variables used by the code

## Telegram alerts

The bot sends Markdown-formatted Telegram messages for:

- potential token alerts from DexScreener scoring
- optionally, future Solana or Ethereum transaction alerts once those monitors are enabled

## License

No license file is currently included in this repository.
