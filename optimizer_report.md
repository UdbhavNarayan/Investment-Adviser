# Daily Investment Report

Generated: 2026-10-20 HKT

> **Planning estimate only:** This report is not financial advice, a guaranteed forecast, or a trade instruction. Historical returns and VaR do not predict future results or cap losses. Verify prices, fees, currency, product eligibility, board lots, and HSBC/EasyInvest terms before placing any order. No trades are made. This report refreshes daily; the budget and proposed cash injection are monthly planning amounts, not instructions to invest them every day.

## Current portfolio and allocation drift

- Current portfolio market value: **HK$0.00**
- Monthly salary in config: **HK$38,000.00**
- Monthly investment budget: **HK$10,000.00**
- Spare cash planned for this month's deployment: **HK$10,000.00** (configured remaining balance: HK$30,000.00)
- Total planned cash injection: **HK$20,000.00**

| Bucket | Current value | Current share | Target | Drift | Targeted injection (pre-risk) |
| --- | --- | --- | --- | --- | --- |
| Steady Growth Core | HK$0.00 | N/A | 60.00% | N/A | HK$12,000.00 |
| Higher Risk/Reward | HK$0.00 | N/A | 40.00% | N/A | HK$8,000.00 |

Drift is current share minus target share; negative drift means underweight. When the current portfolio is empty, current share and drift are N/A.



### Holdings valuation

| Ticker | Asset | Bucket | Shares | Latest price (HKD) | Value (HKD) | Data status |
| --- | --- | --- | --- | --- | --- | --- |
| 2800.HK | Tracker Fund of Hong Kong | Steady Growth Core | 0 | HK$24.60 | HK$0.00 | OK |
| VT | Vanguard Total World Stock ETF (example) | Steady Growth Core | 0 | HK$1,232.92 | HK$0.00 | OK |
| 03006.HK | HKEX example holding 03006 | Higher Risk/Reward | 0 | N/A | HK$0.00 | ValueError: No daily close data returned. |
| 03119.HK | HKEX example holding 03119 | Higher Risk/Reward | 0 | N/A | HK$0.00 | ValueError: No daily close data returned. |
| 03132.HK | HKEX example holding 03132 | Higher Risk/Reward | 0 | N/A | HK$0.00 | ValueError: No daily close data returned. |

## Quantitative trend forecasts

Short-term momentum compares the latest HKD-converted price with its 20-session simple moving average (SMA). The long-term status compares price with the 200-session SMA; trajectory compares that SMA with its value 20 sessions ago. The 12-month projection compounds the last 252 sessions' average daily log return; it is a historical-drift scenario, not a prediction.

| Ticker | Price vs SMA20 | Short-term momentum | Long-term status | 200-day SMA trajectory | Historical annualized growth | 12-month value scenario |
| --- | --- | --- | --- | --- | --- | --- |
| 2800.HK | -1.65% | Below SMA20 | Below 200-day SMA | Falling | -7.88% | HK$0.00 |
| VT | -1.17% | Below SMA20 | Above 200-day SMA | Rising | 17.12% | HK$0.00 |
| 03006.HK | N/A | Insufficient history | Insufficient history | Insufficient history | N/A | N/A |
| 03119.HK | N/A | Insufficient history | Insufficient history | Insufficient history | N/A | N/A |
| 03132.HK | N/A | Insufficient history | Insufficient history | Insufficient history | N/A | N/A |

The 12-month value scenario applies to the current position only and excludes future contributions, taxes, fees, and changes in holdings.
Aggregate 12-month historical-drift scenario for currently valued positions: **HK$0.00** (excludes contributions and positions without sufficient history).

## Tuition capital risk analytics

- Current portfolio annualized volatility (standard deviation of daily HKD log returns × √252): **N/A**
- Historical 95% monthly VaR estimate (rolling 21-session return 5th percentile): **N/A**
- **Worst-case month dollar swing estimate:** **N/A** on current portfolio value HK$0.00

This VaR is a historical percentile estimate, not a worst-case bound; losses can exceed it. N/A means there was insufficient aligned historical data or no valued holdings. Portfolio risk uses current holding weights and HKD-converted returns.

### Per-asset risk

| Ticker | Annualized volatility | Annualized downside volatility | Historical 95% monthly VaR |
| --- | --- | --- | --- |
| 2800.HK | 21.96% | 16.36% | 7.61% |
| VT | 15.56% | 10.63% | 4.95% |
| 03006.HK | N/A | N/A | N/A |
| 03119.HK | N/A | N/A | N/A |
| 03132.HK | N/A | N/A | N/A |

## Deficit and planned allocation

Target pool for this calculation: **HK$20,000.00** (current portfolio plus monthly budget and planned spare-cash deployment).

| Bucket | Current value | Target value in pool | Positive deficit | Targeted injection | Allocated to assets | Withheld / unallocated |
| --- | --- | --- | --- | --- | --- | --- |
| Steady Growth Core | HK$0.00 | HK$12,000.00 | HK$12,000.00 | HK$12,000.00 | HK$12,000.00 | HK$0.00 |
| Higher Risk/Reward | HK$0.00 | HK$8,000.00 | HK$8,000.00 | HK$8,000.00 | HK$0.00 | HK$8,000.00 |

New allocations are withheld from an asset when its annualized downside volatility exceeds the configured limit of **35.00%** or its downside risk cannot be calculated. Eligible assets in the same bucket receive the reweighted amount; if none are eligible, that amount remains unallocated rather than being redirected across buckets. The table shows the exact amount withheld from each bucket's target-based injection.

- **03006.HK:** Downside volatility unavailable; new allocation withheld.
- **03119.HK:** Downside volatility unavailable; new allocation withheld.
- **03132.HK:** Downside volatility unavailable; new allocation withheld.

## Execution instructions

These are suggested order routes based on configured asset metadata; verify the exact instrument and current broker rules in EasyInvest before acting.

### One-Time Orders

- **2800.HK** (Tracker Fund of Hong Kong): approximately **HK$6,000.00** — HKEX-listed HKD instruments are exempt from the stated HK$7,800 overseas-fund minimum; check board lots and fees.

### Open Monthly Investment Plans

- **VT** (Vanguard Total World Stock ETF (example)): approximately **HK$6,000.00** — below HK$7,800. Use/open a **Monthly Investment Plan (DCA) inside EasyInvest**; do not place this as a one-time overseas fund/ETF cash purchase under the stated HSBC rule.

Amounts are planning allocations, not guaranteed executable order sizes. This script does not update `config.json`; after deploying spare cash or changing holdings, manually update `spare_cash_remaining_hkd` and each asset's `shares` to prevent the next report from repeating stale inputs.

## Data quality and assumptions

- Data source: Yahoo Finance (`yfinance`), daily auto-adjusted close, period `2y`.
- All portfolio valuation and return series are converted to HKD; USD holdings use the fetched USD/HKD series.
- Historical data is not guaranteed complete or timely. Missing series, short histories, and asset-level fetch errors are reported rather than silently treated as zero-price observations.
- Configured zero-share example assets are illustrative only. Edit `config.json` with verified holdings, currency, market, target weights, and actual shares.

- 03006.HK data issue: ValueError: No daily close data returned.
- 03119.HK data issue: ValueError: No daily close data returned.
- 03132.HK data issue: ValueError: No daily close data returned.
