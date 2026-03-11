import asyncio
import json
import time
from pathlib import Path

from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer

CLUSTER = "https://api.mainnet-beta.solana.com"
PAYER_JSON = "payer.json"
AMOUNT_SOL = 0.01
SLEEP_SEC = 0.5

RECIPIENTS = [

]
# ==================


async def main():
    payer_secret = json.loads(Path(PAYER_JSON).read_text("utf-8"))
    payer = Keypair.from_secret_key(bytes(payer_secret))

    client = AsyncClient(CLUSTER)
    print(f"RPC: {CLUSTER}")
    print(f"Payer: {payer.public_key}")
    print(f"Recipients: {len(RECIPIENTS)}")
    lamports = int(AMOUNT_SOL * 1_000_000_000)

    for idx, addr in enumerate(RECIPIENTS, start=1):
        try:
            to_pubkey = PublicKey(addr)

            tx = Transaction()
            tx.add(
                transfer(
                    TransferParams(
                        from_pubkey=payer.public_key,
                        to_pubkey=to_pubkey,
                        lamports=lamports,
                    )
                )
            )

            resp = await client.send_transaction(tx, payer, opts=TxOpts(skip_preflight=False))
            sig = resp.value
            print(f"[{idx}/{len(RECIPIENTS)}] OK -> {addr} | tx: {sig}")
        except Exception as e:
            print(f"[{idx}/{len(RECIPIENTS)}] FAILED -> {addr} | {e}")

        if SLEEP_SEC > 0:
            time.sleep(SLEEP_SEC)

    await client.close()
    print("All Done")


if __name__ == "__main__":
    asyncio.run(main())
