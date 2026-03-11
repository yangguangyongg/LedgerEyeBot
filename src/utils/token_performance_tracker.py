import json
import logging
import os
import time
from datetime import datetime, timezone


class TokenPerformanceTracker:
    def __init__(self, storage_dir, review_windows, summary_interval_seconds):
        self.storage_dir = storage_dir
        self.review_windows = sorted(review_windows)
        self.summary_interval_seconds = summary_interval_seconds
        self.state_path = os.path.join(self.storage_dir, "tracker_state.json")
        self.summary_path = os.path.join(self.storage_dir, "rejection_summary.md")
        self.last_summary_at = 0
        self.state = {
            "active": {},
            "completed": [],
        }
        os.makedirs(self.storage_dir, exist_ok=True)
        self._load_state()

    def record_evaluation(self, token_data, evaluation, potential_score, score_threshold):
        base_token = token_data.get("baseToken", {})
        token_address = base_token.get("address")
        chain_id = token_data.get("chainId")
        price_usd = self._safe_float(token_data.get("priceUsd"))
        if not token_address or not chain_id or price_usd <= 0:
            return

        existing = self.state["active"].get(token_address)
        if existing:
            existing["last_seen_at"] = time.time()
            existing["latest_score"] = max(existing.get("latest_score", 0), potential_score)
            existing["latest_reasons"] = evaluation.get("reasons", [])
            existing["latest_status"] = self._status_label(evaluation["passed"], potential_score, score_threshold)
            self._save_state()
            return

        now = time.time()
        self.state["active"][token_address] = {
            "token_address": token_address,
            "chain_id": chain_id,
            "symbol": base_token.get("symbol", "N/A"),
            "name": base_token.get("name", "Unknown"),
            "price_usd": price_usd,
            "first_seen_at": now,
            "last_seen_at": now,
            "initial_score": potential_score,
            "latest_score": potential_score,
            "initial_status": self._status_label(evaluation["passed"], potential_score, score_threshold),
            "latest_status": self._status_label(evaluation["passed"], potential_score, score_threshold),
            "initial_reasons": evaluation.get("reasons", []),
            "latest_reasons": evaluation.get("reasons", []),
            "initial_metrics": evaluation.get("metrics", {}),
            "reviews": {},
        }
        self._save_state()

    async def review_due_tokens(self, fetch_pool_tokens):
        now = time.time()
        completed_addresses = []
        updated = False

        for token_address, record in list(self.state["active"].items()):
            pending_windows = [
                window for window in self.review_windows
                if str(window) not in record["reviews"] and now - record["first_seen_at"] >= window
            ]
            if not pending_windows:
                continue

            token_data = await fetch_pool_tokens(record["chain_id"], token_address)
            if not token_data:
                continue

            current_price = self._safe_float(token_data.get("priceUsd"))
            if current_price <= 0:
                continue

            for window in pending_windows:
                gain_pct = self._calculate_gain_pct(record["price_usd"], current_price)
                record["reviews"][str(window)] = {
                    "checked_at": now,
                    "price_usd": current_price,
                    "gain_pct": gain_pct,
                }
                updated = True

            if all(str(window) in record["reviews"] for window in self.review_windows):
                completed_addresses.append(token_address)

        for token_address in completed_addresses:
            self.state["completed"].append(self.state["active"].pop(token_address))
            updated = True

        if updated:
            self._save_state()

    def maybe_update_summary(self):
        now = time.time()
        if now - self.last_summary_at < self.summary_interval_seconds:
            return None

        table = self.build_rejection_summary_table()
        self.last_summary_at = now
        with open(self.summary_path, "w", encoding="utf-8") as file:
            file.write(table)
        return table

    def build_rejection_summary_table(self):
        rows = self._build_reason_rows()
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        label_map = {900: "15m", 3600: "1h", 14400: "4h"}
        window_labels = [label_map.get(window, f"{window}s") for window in self.review_windows]
        header = [
            f"# Rejection Summary ({generated_at})",
            "",
            "| Reason | Count | "
            + " | ".join(f"Avg {label}" for label in window_labels)
            + " | Win Rate 1h |",
            "| --- | ---: | "
            + " | ".join("---:" for _ in window_labels)
            + " | ---: |",
        ]

        if not rows:
            header.append(
                "| No data | 0 | "
                + " | ".join("-" for _ in window_labels)
                + " | - |"
            )
            return "\n".join(header) + "\n"

        for row in rows:
            averages = " | ".join(f"{value}%" for value in row["averages"])
            header.append(
                f"| {row['reason']} | {row['count']} | {averages} | {row['win_rate_1h']}% |"
            )
        return "\n".join(header) + "\n"

    def _build_reason_rows(self):
        completed = self.state["completed"]
        reason_stats = {}

        for record in completed:
            reasons = record.get("initial_reasons", [])
            if not reasons:
                continue

            for reason in reasons:
                stat = reason_stats.setdefault(reason, {
                    "count": 0,
                    "gains": {window: [] for window in self.review_windows},
                })
                stat["count"] += 1

                for window in self.review_windows:
                    review = record["reviews"].get(str(window))
                    if review:
                        stat["gains"][window].append(review["gain_pct"])

        rows = []
        for reason, stat in sorted(reason_stats.items(), key=lambda item: item[1]["count"], reverse=True):
            one_hour_gains = stat["gains"].get(3600, [])
            win_rate = 0
            if one_hour_gains:
                wins = len([gain for gain in one_hour_gains if gain > 0])
                win_rate = round(wins / len(one_hour_gains) * 100, 2)

            rows.append({
                "reason": reason,
                "count": stat["count"],
                "averages": [self._average(stat["gains"][window]) for window in self.review_windows],
                "win_rate_1h": win_rate,
            })
        return rows

    @staticmethod
    def _status_label(passed_filter, potential_score, score_threshold):
        if passed_filter and potential_score >= score_threshold:
            return "candidate"
        if passed_filter:
            return "passed_filter"
        return "rejected"

    @staticmethod
    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _calculate_gain_pct(initial_price, current_price):
        if initial_price <= 0:
            return 0.0
        return round(((current_price - initial_price) / initial_price) * 100, 2)

    @staticmethod
    def _average(values):
        if not values:
            return 0
        return round(sum(values) / len(values), 2)

    def _load_state(self):
        if not os.path.exists(self.state_path):
            return

        try:
            with open(self.state_path, "r", encoding="utf-8") as file:
                self.state = json.load(file)
        except Exception as exc:
            logging.error(f"Failed to load tracker state: {exc}")

    def _save_state(self):
        with open(self.state_path, "w", encoding="utf-8") as file:
            json.dump(self.state, file, ensure_ascii=True, indent=2)
