#!/usr/bin/env python3
"""Generate a historical-data-based monthly portfolio review in Markdown.

This script provides estimates and planning information, not investment advice
or trade execution. It never connects to an HSBC or EasyInvest account.
"""

from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
REPORT_PATH = ROOT / "optimizer_report.md"
REPORT_JSON_PATH = ROOT / "frontend" / "public" / "report.json"
TRADING_DAYS_PER_YEAR = 252
TRADING_DAYS_PER_MONTH = 21
GLOBAL_ORDER_MINIMUM_HKD = 7800.0
BUCKET_NAMES = {"steady": "Steady Growth Core", "risk": "Higher Risk/Reward"}


@dataclass
class AssetAnalysis:
    ticker: str
    config: dict[str, Any]
    prices_hkd: pd.Series | None = None
    returns: pd.Series | None = None
    current_price_hkd: float | None = None
    position_value_hkd: float = 0.0
    annualized_volatility: float | None = None
    downside_volatility: float | None = None
    monthly_var_fraction: float | None = None
    sma20_hkd: float | None = None
    sma200_hkd: float | None = None
    sma200_prior_hkd: float | None = None
    annualized_growth: float | None = None
    data_issue: str | None = None


def load_config() -> dict[str, Any]:
    try:
        with CONFIG_PATH.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Unable to read {CONFIG_PATH.name}: {error}") from error

    required = {
        "monthly_salary_hkd",
        "monthly_investment_budget_hkd",
        "spare_cash_remaining_hkd",
        "spare_cash_deployment_per_month_hkd",
        "target_allocation",
        "maximum_annualized_downside_volatility",
        "history_period",
        "assets",
    }
    missing = sorted(required - config.keys())
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")
    if not isinstance(config["assets"], dict) or not config["assets"]:
        raise ValueError("config.json must define at least one asset.")

    targets = config["target_allocation"]
    if not isinstance(targets, dict) or set(targets) != {"steady", "risk"}:
        raise ValueError("target_allocation must contain exactly 'steady' and 'risk'.")
    if any(
        not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        for value in targets.values()
    ):
        raise ValueError("Allocation targets must be non-negative numbers.")
    if not math.isclose(sum(targets.values()), 1.0, abs_tol=1e-8):
        raise ValueError("The steady and risk target ratios must sum to 1.0.")

    for key in (
        "monthly_salary_hkd",
        "monthly_investment_budget_hkd",
        "spare_cash_remaining_hkd",
        "spare_cash_deployment_per_month_hkd",
        "maximum_annualized_downside_volatility",
    ):
        value = config[key]
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{key} must be a non-negative number.")

    for ticker, asset in config["assets"].items():
        if not isinstance(asset, dict):
            raise ValueError(f"{ticker}: asset configuration must be an object.")
        if asset.get("bucket") not in BUCKET_NAMES:
            raise ValueError(f"{ticker}: bucket must be 'steady' or 'risk'.")
        if asset.get("market") not in {"HKEX", "GLOBAL"}:
            raise ValueError(f"{ticker}: market must be 'HKEX' or 'GLOBAL'.")
        if asset.get("currency") not in {"HKD", "USD"}:
            raise ValueError(f"{ticker}: currency must be 'HKD' or 'USD'.")
        if asset["market"] == "HKEX" and asset["currency"] != "HKD":
            raise ValueError(f"{ticker}: HKEX assets must be configured in HKD.")
        shares = asset.get("shares")
        weight = asset.get("target_weight_in_bucket")
        if (
            not isinstance(shares, (int, float))
            or not math.isfinite(shares)
            or shares < 0
        ):
            raise ValueError(f"{ticker}: shares must be a non-negative number.")
        if (
            not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or weight < 0
        ):
            raise ValueError(f"{ticker}: target_weight_in_bucket must be non-negative.")
        if not isinstance(asset.get("name"), str) or not asset["name"].strip():
            raise ValueError(f"{ticker}: name must be a non-empty string.")

    for bucket in BUCKET_NAMES:
        weights = [
            asset["target_weight_in_bucket"]
            for asset in config["assets"].values()
            if asset["bucket"] == bucket
        ]
        if not weights or not math.isclose(sum(weights), 1.0, abs_tol=1e-8):
            raise ValueError(f"Asset weights in the {bucket!r} bucket must sum to 1.0.")
    return config


def fetch_close(ticker: str, period: str) -> pd.Series:
    """Fetch adjusted daily closes and normalize yfinance's column variants."""
    frame = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if frame is None or frame.empty or "Close" not in frame.columns.get_level_values(0):
        raise ValueError("No daily close data returned.")
    closes = frame["Close"]
    if isinstance(closes, pd.DataFrame):
        if ticker in closes.columns:
            closes = closes[ticker]
        elif closes.shape[1] == 1:
            closes = closes[closes.columns[0]]
        else:
            raise ValueError("Daily close response contains unexpected columns.")
    closes = pd.to_numeric(closes, errors="coerce").dropna()
    closes.index = pd.to_datetime(closes.index).tz_localize(None)
    closes = closes[~closes.index.duplicated(keep="last")].sort_index()
    if closes.empty or (closes <= 0).any():
        raise ValueError("Daily close data is empty or contains non-positive prices.")
    return closes.astype(float)


def analyze_asset(
    ticker: str, asset_config: dict[str, Any], period: str, fx_hkd_per_usd: pd.Series | None
) -> AssetAnalysis:
    analysis = AssetAnalysis(ticker=ticker, config=asset_config)
    try:
        closes = fetch_close(ticker, period)
        if asset_config["currency"] == "USD":
            if fx_hkd_per_usd is None or fx_hkd_per_usd.empty:
                raise ValueError("USD/HKD exchange-rate history is unavailable.")
            prices = pd.concat(
                [closes.rename("asset"), fx_hkd_per_usd.rename("fx")], axis=1
            ).sort_index()
            prices["fx"] = prices["fx"].ffill(limit=5)
            prices = prices.dropna()
            if prices.empty:
                raise ValueError("No overlapping USD asset and USD/HKD price history.")
            hkd_prices = prices["asset"] * prices["fx"]
        else:
            hkd_prices = closes

        hkd_prices = hkd_prices.dropna().astype(float)
        if hkd_prices.empty:
            raise ValueError("No usable HKD-converted prices.")
        analysis.prices_hkd = hkd_prices
        returns: pd.Series = pd.Series(
            np.log(hkd_prices / hkd_prices.shift(1)),
            index=hkd_prices.index,
        ).dropna()
        analysis.returns = returns
        analysis.current_price_hkd = float(hkd_prices.iloc[-1])
        analysis.position_value_hkd = (
            analysis.current_price_hkd * float(asset_config["shares"])
        )

        if len(returns) >= 2:
            analysis.annualized_volatility = float(
                returns.std(ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR)
            )
            negative_returns = returns.clip(upper=0)
            analysis.downside_volatility = float(
                math.sqrt(float(np.mean(np.square(negative_returns))))
                * math.sqrt(TRADING_DAYS_PER_YEAR)
            )

        if len(returns) >= TRADING_DAYS_PER_MONTH:
            monthly_log_returns = returns.rolling(TRADING_DAYS_PER_MONTH).sum().dropna()
            analysis.monthly_var_fraction = max(
                0.0, -float(monthly_log_returns.quantile(0.05))
            )

        if len(hkd_prices) >= 20:
            analysis.sma20_hkd = float(hkd_prices.tail(20).mean())
        if len(hkd_prices) >= 200:
            analysis.sma200_hkd = float(hkd_prices.tail(200).mean())
            if len(hkd_prices) >= 220:
                analysis.sma200_prior_hkd = float(hkd_prices.iloc[-220:-20].mean())
        if len(returns) >= TRADING_DAYS_PER_YEAR:
            analysis.annualized_growth = float(
            math.exp(float(returns.tail(TRADING_DAYS_PER_YEAR).mean())
                         * TRADING_DAYS_PER_YEAR)
                - 1.0
            )
    except Exception as error:
        analysis.data_issue = f"{type(error).__name__}: {error}"
    return analysis


def fmt_hkd(value: float | None) -> str:
    return "N/A" if value is None or not math.isfinite(value) else f"HK${value:,.2f}"


def fmt_pct(value: float | None) -> str:
    return "N/A" if value is None or not math.isfinite(value) else f"{value * 100:.2f}%"


def markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(markdown_cell(value) for value in row) + " |"
        for row in rows
    )
    return "\n".join(lines)


def portfolio_returns(analyses: dict[str, AssetAnalysis], total_value: float) -> pd.Series:
    if total_value <= 0:
        return pd.Series(dtype=float)
    weighted_returns: list[pd.Series] = []
    for analysis in analyses.values():
        if analysis.returns is None or analysis.position_value_hkd <= 0:
            continue
        weight = analysis.position_value_hkd / total_value
        weighted_returns.append(analysis.returns.rename(analysis.ticker) * weight)
    if not weighted_returns:
        return pd.Series(dtype=float)
    return pd.concat(weighted_returns, axis=1).dropna().sum(axis=1)


def calculate_allocations(
    config: dict[str, Any],
    analyses: dict[str, AssetAnalysis],
    bucket_values: dict[str, float],
    total_value: float,
    holdings_data_complete: bool,
) -> tuple[dict[str, float], dict[str, float], float, float]:
    monthly_budget = float(config["monthly_investment_budget_hkd"])
    spare_deployment = min(
        float(config["spare_cash_remaining_hkd"]),
        float(config["spare_cash_deployment_per_month_hkd"]),
    )
    injection = monthly_budget + spare_deployment
    target_pool = total_value + injection
    deficits = {
        bucket: max(
            0.0,
            target_pool * float(config["target_allocation"][bucket]) - bucket_values[bucket],
        )
        for bucket in BUCKET_NAMES
    }
    positive_deficit = sum(deficits.values())
    bucket_allocations = {bucket: 0.0 for bucket in BUCKET_NAMES}
    if holdings_data_complete and injection > 0 and positive_deficit > 0:
        for bucket in BUCKET_NAMES:
            bucket_allocations[bucket] = injection * deficits[bucket] / positive_deficit

    asset_allocations = {ticker: 0.0 for ticker in analyses}
    risk_limit = float(config["maximum_annualized_downside_volatility"])
    for bucket, amount in bucket_allocations.items():
        if amount <= 0:
            continue
        eligible: list[tuple[str, float]] = []
        for ticker, analysis in analyses.items():
            asset = analysis.config
            if asset["bucket"] != bucket or asset["target_weight_in_bucket"] <= 0:
                continue
            downside_volatility = analysis.downside_volatility
            if downside_volatility is None:
                continue
            elif downside_volatility > risk_limit:
                continue
            else:
                eligible.append((ticker, float(asset["target_weight_in_bucket"])))
        eligible_weight = sum(weight for _, weight in eligible)
        if eligible_weight <= 0:
            continue
        for ticker, weight in eligible:
            asset_allocations[ticker] = amount * weight / eligible_weight

    return bucket_allocations, asset_allocations, injection, spare_deployment


def build_report_bundle(config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    period = str(config["history_period"])
    fx_hkd_per_usd: pd.Series | None = None
    fx_issue: str | None = None
    try:
        fx_hkd_per_usd = fetch_close("HKD=X", period)
    except Exception as error:
        fx_issue = f"{type(error).__name__}: {error}"

    analyses = {
        ticker: analyze_asset(ticker, asset_config, period, fx_hkd_per_usd)
        for ticker, asset_config in config["assets"].items()
    }
    bucket_values = {
        bucket: sum(
            analysis.position_value_hkd
            for analysis in analyses.values()
            if analysis.config["bucket"] == bucket
        )
        for bucket in BUCKET_NAMES
    }
    total_value = sum(bucket_values.values())
    holdings_data_complete = all(
        float(analysis.config["shares"]) == 0 or analysis.current_price_hkd is not None
        for analysis in analyses.values()
    )
    (
        bucket_allocations,
        asset_allocations,
        injection,
        spare_deployment,
    ) = calculate_allocations(
        config, analyses, bucket_values, total_value, holdings_data_complete
    )
    portfolio_projection_hkd = sum(
        analysis.position_value_hkd * (1 + analysis.annualized_growth)
        for analysis in analyses.values()
        if analysis.annualized_growth is not None
    )
    bucket_asset_allocations = {
        bucket: sum(
            asset_allocations[ticker]
            for ticker, analysis in analyses.items()
            if analysis.config["bucket"] == bucket
        )
        for bucket in BUCKET_NAMES
    }
    bucket_unallocated = {
        bucket: max(0.0, bucket_allocations[bucket] - bucket_asset_allocations[bucket])
        for bucket in BUCKET_NAMES
    }

    actual_ratios: dict[str, float | None] = {
        bucket: bucket_values[bucket] / total_value if total_value > 0 else None
        for bucket in BUCKET_NAMES
    }
    portfolio_daily_returns = portfolio_returns(analyses, total_value)
    portfolio_volatility: float | None = None
    portfolio_var_hkd: float | None = None
    portfolio_var_fraction: float | None = None
    if len(portfolio_daily_returns) >= 2:
        portfolio_volatility = float(
            portfolio_daily_returns.std(ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR)
        )
    if len(portfolio_daily_returns) >= TRADING_DAYS_PER_MONTH:
        monthly_log_returns = (
            portfolio_daily_returns.rolling(TRADING_DAYS_PER_MONTH).sum().dropna()
        )
        portfolio_var_fraction = max(0.0, -float(monthly_log_returns.quantile(0.05)))
        portfolio_var_hkd = total_value * portfolio_var_fraction

    today = datetime.now().astimezone().strftime("%Y-%m-%d %Z")
    lines = [
        "# Daily Investment Report",
        "",
        f"Generated: {today}",
        "",
        "> **Planning estimate only:** This report is not financial advice, a guaranteed "
        "forecast, or a trade instruction. Historical returns and VaR do not predict "
        "future results or cap losses. Verify prices, fees, currency, product eligibility, "
        "board lots, and HSBC/EasyInvest terms before placing any order. No trades are made. "
        "This report refreshes daily; the budget and proposed cash injection are monthly "
        "planning amounts, not instructions to invest them every day.",
        "",
        "## Current portfolio and allocation drift",
        "",
        f"- Current portfolio market value: **{fmt_hkd(total_value)}**",
        f"- Monthly salary in config: **{fmt_hkd(float(config['monthly_salary_hkd']))}**",
        f"- Monthly investment budget: **{fmt_hkd(float(config['monthly_investment_budget_hkd']))}**",
        f"- Spare cash planned for this month's deployment: **{fmt_hkd(spare_deployment)}** "
        f"(configured remaining balance: {fmt_hkd(float(config['spare_cash_remaining_hkd']))})",
        f"- Total planned cash injection: **{fmt_hkd(injection)}**",
        "",
    ]
    allocation_rows: list[list[Any]] = []
    for bucket in BUCKET_NAMES:
        target = float(config["target_allocation"][bucket])
        actual = actual_ratios[bucket]
        drift = actual - target if actual is not None else None
        allocation_rows.append(
            [
                BUCKET_NAMES[bucket],
                fmt_hkd(bucket_values[bucket]),
                fmt_pct(actual),
                fmt_pct(target),
                fmt_pct(drift),
                fmt_hkd(bucket_allocations[bucket]),
            ]
        )
    lines.extend(
        [
            markdown_table(
                [
                    "Bucket",
                    "Current value",
                    "Current share",
                    "Target",
                    "Drift",
                    "Targeted injection (pre-risk)",
                ],
                allocation_rows,
            ),
            "",
            "Drift is current share minus target share; negative drift means underweight. "
            "When the current portfolio is empty, current share and drift are N/A.",
            "",
            (
                "**Warning:** At least one configured holding has no usable latest price. "
                "The displayed portfolio value is incomplete and all new allocation "
                "recommendations have been withheld."
                if not holdings_data_complete
                else ""
            ),
            "",
            "### Holdings valuation",
            "",
        ]
    )
    holding_rows = []
    for ticker, analysis in analyses.items():
        holding_rows.append(
            [
                ticker,
                analysis.config["name"],
                BUCKET_NAMES[analysis.config["bucket"]],
                f"{float(analysis.config['shares']):g}",
                fmt_hkd(analysis.current_price_hkd),
                fmt_hkd(analysis.position_value_hkd),
                analysis.data_issue or "OK",
            ]
        )
    lines.extend(
        [
            markdown_table(
                ["Ticker", "Asset", "Bucket", "Shares", "Latest price (HKD)", "Value (HKD)", "Data status"],
                holding_rows,
            ),
            "",
            "## Quantitative trend forecasts",
            "",
            "Short-term momentum compares the latest HKD-converted price with its 20-session "
            "simple moving average (SMA). The long-term status compares price with the "
            "200-session SMA; trajectory compares that SMA with its value 20 sessions ago. "
            "The 12-month projection compounds the last 252 sessions' average daily log "
            "return; it is a historical-drift scenario, not a prediction.",
            "",
        ]
    )
    trend_rows: list[list[Any]] = []
    for ticker, analysis in analyses.items():
        price = analysis.current_price_hkd
        short_gap = (
            price / analysis.sma20_hkd - 1
            if price is not None and analysis.sma20_hkd
            else None
        )
        long_status = (
            "Above 200-day SMA"
            if price is not None and analysis.sma200_hkd and price >= analysis.sma200_hkd
            else "Below 200-day SMA"
            if price is not None and analysis.sma200_hkd
            else "Insufficient history"
        )
        if analysis.sma200_hkd is not None and analysis.sma200_prior_hkd:
            trajectory = (
                "Rising"
                if analysis.sma200_hkd > analysis.sma200_prior_hkd
                else "Falling"
                if analysis.sma200_hkd < analysis.sma200_prior_hkd
                else "Flat"
            )
        else:
            trajectory = "Insufficient history"
        projected_value = (
            analysis.position_value_hkd * (1 + analysis.annualized_growth)
            if analysis.annualized_growth is not None
            else None
        )
        momentum_status = (
            "Above SMA20"
            if short_gap is not None and short_gap >= 0
            else "Below SMA20"
            if short_gap is not None
            else "Insufficient history"
        )
        trend_rows.append(
            [
                ticker,
                fmt_pct(short_gap),
                momentum_status,
                long_status,
                trajectory,
                fmt_pct(analysis.annualized_growth),
                fmt_hkd(projected_value),
            ]
        )
    lines.extend(
        [
            markdown_table(
                [
                    "Ticker",
                    "Price vs SMA20",
                    "Short-term momentum",
                    "Long-term status",
                    "200-day SMA trajectory",
                    "Historical annualized growth",
                    "12-month value scenario",
                ],
                trend_rows,
            ),
            "",
            "The 12-month value scenario applies to the current position only and excludes "
            "future contributions, taxes, fees, and changes in holdings.",
            f"Aggregate 12-month historical-drift scenario for currently valued positions: "
            f"**{fmt_hkd(portfolio_projection_hkd)}** (excludes contributions and positions "
            "without sufficient history).",
            "",
            "## Tuition capital risk analytics",
            "",
            f"- Current portfolio annualized volatility (standard deviation of daily "
            f"HKD log returns × √252): **{fmt_pct(portfolio_volatility)}**",
            f"- Historical 95% monthly VaR estimate (rolling 21-session return 5th "
            f"percentile): **{fmt_pct(portfolio_var_fraction)}**",
            f"- **Worst-case month dollar swing estimate:** **{fmt_hkd(portfolio_var_hkd)}** "
            f"on current portfolio value {fmt_hkd(total_value)}",
            "",
            "This VaR is a historical percentile estimate, not a worst-case bound; losses "
            "can exceed it. N/A means there was insufficient aligned historical data or "
            "no valued holdings. Portfolio risk uses current holding weights and "
            "HKD-converted returns.",
            "",
            "### Per-asset risk",
            "",
        ]
    )
    risk_rows = [
        [
            ticker,
            fmt_pct(analysis.annualized_volatility),
            fmt_pct(analysis.downside_volatility),
            fmt_pct(analysis.monthly_var_fraction),
        ]
        for ticker, analysis in analyses.items()
    ]
    lines.extend(
        [
            markdown_table(
                ["Ticker", "Annualized volatility", "Annualized downside volatility", "Historical 95% monthly VaR"],
                risk_rows,
            ),
            "",
            "## Deficit and planned allocation",
            "",
            f"Target pool for this calculation: **{fmt_hkd(total_value + injection)}** "
            f"(current portfolio plus monthly budget and planned spare-cash deployment).",
            "",
            markdown_table(
                [
                    "Bucket",
                    "Current value",
                    "Target value in pool",
                    "Positive deficit",
                    "Targeted injection",
                    "Allocated to assets",
                    "Withheld / unallocated",
                ],
                [
                    [
                        BUCKET_NAMES[bucket],
                        fmt_hkd(bucket_values[bucket]),
                        fmt_hkd(
                            (total_value + injection)
                            * float(config["target_allocation"][bucket])
                        ),
                        fmt_hkd(
                            max(
                                0.0,
                                (total_value + injection)
                                * float(config["target_allocation"][bucket])
                                - bucket_values[bucket],
                            )
                        ),
                        fmt_hkd(bucket_allocations[bucket]),
                        fmt_hkd(bucket_asset_allocations[bucket]),
                        fmt_hkd(bucket_unallocated[bucket]),
                    ]
                    for bucket in BUCKET_NAMES
                ],
            ),
            "",
            f"New allocations are withheld from an asset when its annualized downside "
            f"volatility exceeds the configured limit of "
            f"**{fmt_pct(float(config['maximum_annualized_downside_volatility']))}** "
            "or its downside risk cannot be calculated. Eligible assets in the same "
            "bucket receive the reweighted amount; if none are eligible, that amount "
            "remains unallocated rather than being redirected across buckets. The table "
            "shows the exact amount withheld from each bucket's target-based injection.",
            "",
        ]
    )
    for ticker, reason in (
        (ticker, reason)
        for ticker, analysis in analyses.items()
        if analysis.downside_volatility is None
        or analysis.downside_volatility
        > float(config["maximum_annualized_downside_volatility"])
        for reason in [
            "Downside volatility unavailable; new allocation withheld."
            if analysis.downside_volatility is None
            else (
                f"Downside volatility {fmt_pct(analysis.downside_volatility)} exceeds "
                f"the configured limit {fmt_pct(float(config['maximum_annualized_downside_volatility']))}."
            )
        ]
    ):
        lines.append(f"- **{ticker}:** {reason}")
    lines.extend(
        [
            "",
            "## Execution instructions",
            "",
            "These are suggested order routes based on configured asset metadata; verify "
            "the exact instrument and current broker rules in EasyInvest before acting.",
            "",
            "### One-Time Orders",
            "",
        ]
    )
    one_time_orders = []
    monthly_plans = []
    for ticker, amount in asset_allocations.items():
        if amount <= 0.005:
            continue
        analysis = analyses[ticker]
        if analysis.config["market"] == "HKEX":
            one_time_orders.append(
                f"- **{ticker}** ({analysis.config['name']}): approximately "
                f"**{fmt_hkd(amount)}** — HKEX-listed HKD instruments are exempt from "
                "the stated HK$7,800 overseas-fund minimum; check board lots and fees."
            )
        elif amount >= GLOBAL_ORDER_MINIMUM_HKD:
            one_time_orders.append(
                f"- **{ticker}** ({analysis.config['name']}): approximately "
                f"**{fmt_hkd(amount)}** — at or above the configured HK$7,800 threshold."
            )
        else:
            monthly_plans.append(
                f"- **{ticker}** ({analysis.config['name']}): approximately "
                f"**{fmt_hkd(amount)}** — below HK$7,800. Use/open a **Monthly Investment "
                "Plan (DCA) inside EasyInvest**; do not place this as a one-time overseas "
                "fund/ETF cash purchase under the stated HSBC rule."
            )
    lines.extend(one_time_orders or ["- No eligible one-time orders are currently recommended."])
    lines.extend(["", "### Open Monthly Investment Plans", ""])
    lines.extend(monthly_plans or ["- No below-threshold global-fund DCA plans are currently recommended."])
    lines.extend(
        [
            "",
            "Amounts are planning allocations, not guaranteed executable order sizes. "
            "This script does not update `config.json`; after deploying spare cash or "
            "changing holdings, manually update `spare_cash_remaining_hkd` and each "
            "asset's `shares` to prevent the next report from repeating stale inputs.",
            "",
            "## Data quality and assumptions",
            "",
            f"- Data source: Yahoo Finance (`yfinance`), daily auto-adjusted close, period `{period}`.",
            "- All portfolio valuation and return series are converted to HKD; USD holdings "
            "use the fetched USD/HKD series.",
            "- Historical data is not guaranteed complete or timely. Missing series, "
            "short histories, and asset-level fetch errors are reported rather than "
            "silently treated as zero-price observations.",
            "- Configured zero-share example assets are illustrative only. Edit `config.json` "
            "with verified holdings, currency, market, target weights, and actual shares.",
            "",
        ]
    )
    if fx_issue:
        lines.append(f"- USD/HKD fetch issue: {fx_issue}")
    for ticker, analysis in analyses.items():
        if analysis.data_issue:
            lines.append(f"- {ticker} data issue: {analysis.data_issue}")

    available_history = {
        ticker: analysis.prices_hkd
        for ticker, analysis in analyses.items()
        if analysis.prices_hkd is not None
    }
    history_frame = (
        pd.concat(available_history, axis=1).sort_index().tail(90)
        if available_history
        else pd.DataFrame()
    )
    history_records: list[dict[str, Any]] = []
    if not history_frame.empty:
        normalized_history = history_frame.copy()
        for ticker in normalized_history.columns:
            available = normalized_history[ticker].dropna()
            if available.empty:
                continue
            normalized_history[ticker] = normalized_history[ticker] / available.iloc[0] * 100
        history_dates = normalized_history.index.to_numpy(dtype="datetime64[ns]")
        history_values = normalized_history.to_numpy()
        for date, values in zip(history_dates, history_values, strict=True):
            history_records.append(
                {
                    "date": np.datetime_as_string(date, unit="D"),
                    "assets": {
                        ticker: (
                            round(float(value), 4)
                            if pd.notna(value) and math.isfinite(float(value))
                            else None
                        )
                        for ticker, value in zip(normalized_history.columns, values, strict=True)
                    },
                }
            )

    def json_number(value: float | None) -> float | None:
        return (
            float(value)
            if value is not None and math.isfinite(float(value))
            else None
        )

    holdings_data = []
    for ticker, analysis in analyses.items():
        price = analysis.current_price_hkd
        short_gap = (
            price / analysis.sma20_hkd - 1
            if price is not None and analysis.sma20_hkd
            else None
        )
        if analysis.sma200_hkd is not None and analysis.sma200_prior_hkd is not None:
            long_trend = (
                "Rising"
                if analysis.sma200_hkd > analysis.sma200_prior_hkd
                else "Falling"
                if analysis.sma200_hkd < analysis.sma200_prior_hkd
                else "Flat"
            )
        else:
            long_trend = None
        growth = analysis.annualized_growth
        projected_value = (
            analysis.position_value_hkd * (1 + growth) if growth is not None else None
        )
        allocation = asset_allocations[ticker]
        if allocation <= 0:
            order_type = "none"
        elif analysis.config["market"] == "HKEX":
            order_type = "one-time"
        elif allocation >= GLOBAL_ORDER_MINIMUM_HKD:
            order_type = "one-time"
        else:
            order_type = "monthly-plan"
        holdings_data.append(
            {
                "ticker": ticker,
                "name": analysis.config["name"],
                "bucket": analysis.config["bucket"],
                "bucketLabel": BUCKET_NAMES[analysis.config["bucket"]],
                "market": analysis.config["market"],
                "currency": analysis.config["currency"],
                "shares": float(analysis.config["shares"]),
                "targetWeightInBucket": float(
                    analysis.config["target_weight_in_bucket"]
                ),
                "priceHkd": json_number(price),
                "valueHkd": round(analysis.position_value_hkd, 2),
                "allocationHkd": round(allocation, 2),
                "orderType": order_type,
                "momentumPercent": json_number(short_gap * 100 if short_gap is not None else None),
                "priceVsSma20": (
                    "Above" if short_gap is not None and short_gap >= 0
                    else "Below" if short_gap is not None else None
                ),
                "sma20Hkd": json_number(analysis.sma20_hkd),
                "longTermStatus": (
                    "Above 200-day SMA"
                    if price is not None and analysis.sma200_hkd and price >= analysis.sma200_hkd
                    else "Below 200-day SMA"
                    if price is not None and analysis.sma200_hkd
                    else None
                ),
                "longTrend": long_trend,
                "sma200Hkd": json_number(analysis.sma200_hkd),
                "annualizedGrowthPercent": json_number(
                    growth * 100 if growth is not None else None
                ),
                "projectedValueHkd": json_number(projected_value),
                "annualizedVolatilityPercent": json_number(
                    analysis.annualized_volatility * 100
                    if analysis.annualized_volatility is not None else None
                ),
                "downsideVolatilityPercent": json_number(
                    analysis.downside_volatility * 100
                    if analysis.downside_volatility is not None else None
                ),
                "monthlyVarPercent": json_number(
                    analysis.monthly_var_fraction * 100
                    if analysis.monthly_var_fraction is not None else None
                ),
                "dataIssue": analysis.data_issue,
            }
        )

    bucket_data = []
    for bucket in BUCKET_NAMES:
        target_ratio = float(config["target_allocation"][bucket])
        current_ratio = actual_ratios[bucket]
        target_value = (total_value + injection) * target_ratio
        bucket_data.append(
            {
                "id": bucket,
                "name": BUCKET_NAMES[bucket],
                "valueHkd": round(bucket_values[bucket], 2),
                "currentPercent": json_number(
                    current_ratio * 100 if current_ratio is not None else None
                ),
                "targetPercent": target_ratio * 100,
                "driftPercent": json_number(
                    (current_ratio - target_ratio) * 100
                    if current_ratio is not None else None
                ),
                "targetValueHkd": round(target_value, 2),
                "deficitHkd": round(max(0.0, target_value - bucket_values[bucket]), 2),
                "targetedInjectionHkd": round(bucket_allocations[bucket], 2),
                "allocatedHkd": round(bucket_asset_allocations[bucket], 2),
                "unallocatedHkd": round(bucket_unallocated[bucket], 2),
            }
        )

    warnings = []
    if not holdings_data_complete:
        warnings.append(
            "At least one held position has no usable latest price. Valuation is "
            "incomplete and new allocations have been withheld."
        )
    if fx_issue:
        warnings.append(f"USD/HKD exchange-rate data issue: {fx_issue}")
    for ticker, analysis in analyses.items():
        if analysis.data_issue:
            warnings.append(f"{ticker}: {analysis.data_issue}")
        elif (
            analysis.downside_volatility is None
            or analysis.downside_volatility
            > float(config["maximum_annualized_downside_volatility"])
        ):
            warnings.append(
                f"{ticker}: new allocation withheld because downside risk is unavailable "
                "or above the configured limit."
            )

    report_data = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "currency": str(config.get("currency", "HKD")),
        "historyPeriod": period,
        "summary": {
            "portfolioValueHkd": round(total_value, 2),
            "monthlySalaryHkd": float(config["monthly_salary_hkd"]),
            "monthlyBudgetHkd": float(config["monthly_investment_budget_hkd"]),
            "spareCashRemainingHkd": float(config["spare_cash_remaining_hkd"]),
            "spareCashDeploymentHkd": round(spare_deployment, 2),
            "cashInjectionHkd": round(injection, 2),
            "targetPoolHkd": round(total_value + injection, 2),
            "projectedValueHkd": json_number(portfolio_projection_hkd),
            "annualizedVolatilityPercent": json_number(
                portfolio_volatility * 100 if portfolio_volatility is not None else None
            ),
            "monthlyVarPercent": json_number(
                portfolio_var_fraction * 100
                if portfolio_var_fraction is not None else None
            ),
            "monthlyVarHkd": json_number(portfolio_var_hkd),
            "holdingsDataComplete": holdings_data_complete,
        },
        "buckets": bucket_data,
        "holdings": holdings_data,
        "history": history_records,
        "warnings": warnings,
    }
    return "\n".join(lines), report_data


def build_report(config: dict[str, Any]) -> str:
    report, _ = build_report_bundle(config)
    return report


def main() -> int:
    try:
        config = load_config()
        report, report_data = build_report_bundle(config)
        REPORT_PATH.write_text(report + "\n", encoding="utf-8")
        REPORT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON_PATH.write_text(
            json.dumps(report_data, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(report)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with Path(summary_path).open("a", encoding="utf-8") as summary_file:
                summary_file.write(report + "\n")
        return 0
    except (RuntimeError, ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
