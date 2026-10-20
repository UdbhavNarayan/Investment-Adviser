# Daily Investment Report

A Python report generator for a manually maintained investment portfolio. It retrieves
historical daily prices, values configured holdings in HKD, summarizes historical
trend and downside-risk measures, and prints a daily report. It does not
connect to HSBC or EasyInvest and cannot place trades.

## Setup

1. Edit [`config.json`](./config.json): enter actual share quantities, confirm each
   instrument's ticker, currency, market, bucket, and within-bucket target weight.
   Example holdings are illustrative and have zero shares by default. Weights in each
   bucket must sum to 1.0.
2. Install dependencies using Python 3.10 or later:

   ```sh
   python -m pip install -r requirements.txt
   ```

3. Generate a report:

   ```sh
   python optimizer.py
   ```

The report is printed to the terminal and saved as `optimizer_report.md`; the structured
data for the web dashboard is written to `frontend/public/report.json`. It uses
Yahoo Finance data via `yfinance`; network access is required. A scheduled GitHub
Actions workflow runs daily at 02:00 UTC (10:00 Hong Kong time).
You can also run it manually from the Actions tab. The generated Markdown is available
as a workflow artifact and in the GitHub Actions job summary. A built static dashboard
is also uploaded as a separate workflow artifact.

## TypeScript dashboard

After generating a report, start the local frontend:

```sh
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite (normally `http://127.0.0.1:5173`). The dashboard
visualizes portfolio value, target allocation, price trends, volatility, monthly VaR,
holdings, and the suggested order routes. Use **Refresh** after generating a new report.
To create a production build, run `npm run build` from `frontend`; the static site is
written to `frontend/dist`.

The default monthly contribution is HK$10,000, with up to HK$10,000 from the configured
HK$30,000 spare-cash balance included in each report. Reports refresh daily, but these
amounts and the resulting allocations are monthly planning estimates—not a suggestion
to repeat the investment every day. The script does not update that balance or holdings
after a purchase; update `spare_cash_remaining_hkd` and share quantities manually to
prevent stale inputs from being reused.

Historical forecasts and VaR are estimates, not guarantees or investment advice.
Check the exact instrument, prices, fees, board lots, and current HSBC/EasyInvest
transaction rules before acting on any report.
