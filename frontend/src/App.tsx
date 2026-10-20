import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type {
  BucketSummary,
  HistoryPoint,
  Holding,
  InvestmentReport,
} from "./types";

const bucketColors: Record<string, string> = {
  steady: "#216b57",
  risk: "#e28b56",
};

const chartColors = ["#216b57", "#d48350", "#6d83b4", "#9b75ae", "#4c9da2"];
const currencyFormatter = new Intl.NumberFormat("en-HK", {
  style: "currency",
  currency: "HKD",
  maximumFractionDigits: 0,
});

function money(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value)
    ? "—"
    : currencyFormatter.format(value);
}

function percent(value: number | null | undefined, digits = 1): string {
  return value == null || !Number.isFinite(value)
    ? "—"
    : `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

function dateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("en-HK", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "Asia/Hong_Kong",
      }).format(date);
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function Icon({
  name,
  size = 18,
}: {
  name: "grid" | "chart" | "shield" | "settings" | "refresh" | "arrow" | "info";
  size?: number;
}) {
  const paths: Record<typeof name, ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
    chart: <><path d="M4 19V5" /><path d="M4 19h17" /><path d="m7 15 4-4 3 2 6-7" /><path d="M16 6h4v4" /></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.5.9l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.5-.9l-1.7.7-1.4-2.4 1.4-1.1a8 8 0 0 1 0-1.8l-1.4-1.1 1.4-2.4 1.7.7a8 8 0 0 1 1.5-.9l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.5.9l1.7-.7 1.4 2.4-1.4 1.1a8 8 0 0 1 0 1.8Z" transform="translate(-1 -1)" /></>,
    refresh: <><path d="M20 7v5h-5" /><path d="M4 17v-5h5" /><path d="M5.6 9a7 7 0 0 1 11.6-2L20 12M4 12l2.8 5a7 7 0 0 0 11.6-2" /></>,
    arrow: <><path d="M7 17 17 7" /><path d="M8 7h9v9" /></>,
    info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8h.01" /></>,
  };
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}

function Card({
  children,
  className = "",
  id,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return <section className={`card ${className}`} id={id}>{children}</section>;
}

function MetricCard({
  label,
  value,
  detail,
  icon,
  tone = "green",
}: {
  label: string;
  value: string;
  detail: string;
  icon: "chart" | "shield" | "grid" | "info";
  tone?: "green" | "orange" | "blue" | "purple";
}) {
  return (
    <Card className="metric-card">
      <div className={`metric-icon ${tone}`}><Icon name={icon} size={19} /></div>
      <p className="eyebrow">{label}</p>
      <strong className="metric-value">{value}</strong>
      <p className="metric-detail">{detail}</p>
    </Card>
  );
}

function AllocationDonut({ buckets }: { buckets: BucketSummary[] }) {
  const radius = 62;
  const circumference = 2 * Math.PI * radius;
  const first = Math.max(0, Math.min(100, buckets[0]?.targetPercent ?? 60)) / 100;
  return (
    <div className="donut-wrap">
      <svg className="donut" viewBox="0 0 160 160" role="img" aria-label="Portfolio target allocation: 60 percent steady and 40 percent higher risk">
        <circle cx="80" cy="80" r={radius} fill="none" stroke="#edf0ec" strokeWidth="16" />
        <circle
          cx="80"
          cy="80"
          r={radius}
          fill="none"
          stroke={bucketColors[buckets[0]?.id ?? "steady"]}
          strokeWidth="16"
          strokeDasharray={`${circumference * first} ${circumference}`}
          transform="rotate(-90 80 80)"
          strokeLinecap="round"
        />
        <circle
          cx="80"
          cy="80"
          r={radius}
          fill="none"
          stroke={bucketColors[buckets[1]?.id ?? "risk"]}
          strokeWidth="16"
          strokeDasharray={`${circumference * (1 - first)} ${circumference}`}
          strokeDashoffset={-circumference * first}
          transform="rotate(-90 80 80)"
          strokeLinecap="round"
        />
        <text x="80" y="76" textAnchor="middle" className="donut-center-value">
          {buckets.length ? `${Math.round(buckets[0].targetPercent)} / ${Math.round(buckets[1]?.targetPercent ?? 0)}` : "—"}
        </text>
        <text x="80" y="96" textAnchor="middle" className="donut-center-label">target split</text>
      </svg>
      <div className="donut-legend">
        {buckets.map((bucket) => (
          <div className="legend-item" key={bucket.id}>
            <span className="legend-dot" style={{ background: bucketColors[bucket.id] }} />
            <span>{bucket.name}</span>
            <strong>{bucket.targetPercent.toFixed(0)}%</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function HistoryChart({
  history,
  holdings,
}: {
  history: HistoryPoint[];
  holdings: Holding[];
}) {
  const [period, setPeriod] = useState<30 | 90>(90);
  const plotted = history.slice(-period);
  const visibleHoldings = holdings.filter((holding) =>
    plotted.some((point) => point.assets[holding.ticker] != null),
  );
  const values = plotted.flatMap((point) =>
    visibleHoldings
      .map((holding) => point.assets[holding.ticker])
      .filter((value): value is number => value != null && Number.isFinite(value)),
  );
  const minimum = values.length ? Math.min(...values) : 90;
  const maximum = values.length ? Math.max(...values) : 110;
  const span = Math.max(maximum - minimum, 1);
  const chart = { left: 46, right: 630, top: 16, bottom: 172 };
  const x = (index: number) =>
    chart.left + (plotted.length <= 1 ? 0 : (index / (plotted.length - 1)) * (chart.right - chart.left));
  const y = (value: number) =>
    chart.bottom - ((value - minimum) / span) * (chart.bottom - chart.top);
  const ticks = [0, 1, 2, 3].map((index) => maximum - (span * index) / 3);

  return (
    <Card className="chart-card" id="performance">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Market movement</p>
          <h2>Price trend</h2>
          <p className="section-subtitle">Daily adjusted prices, rebased to 100 for comparison</p>
        </div>
        <div className="segmented-control" aria-label="Chart history range">
          <button className={period === 30 ? "selected" : ""} onClick={() => setPeriod(30)}>1M</button>
          <button className={period === 90 ? "selected" : ""} onClick={() => setPeriod(90)}>3M</button>
        </div>
      </div>
      <div className="chart-area">
        {plotted.length === 0 || visibleHoldings.length === 0 ? (
          <div className="empty-chart">
            <span className="empty-icon"><Icon name="chart" size={22} /></span>
            <strong>Price history will appear here</strong>
            <span>Run the Python report generator to fetch the latest market data.</span>
          </div>
        ) : (
          <svg className="line-chart" viewBox="0 0 650 210" role="img" aria-label="Rebased price history for configured holdings">
            {ticks.map((tick) => (
              <g key={tick}>
                <line x1={chart.left} x2={chart.right} y1={y(tick)} y2={y(tick)} className="chart-grid" />
                <text x="0" y={y(tick) + 4} className="chart-axis-label">{tick.toFixed(0)}</text>
              </g>
            ))}
            {visibleHoldings.map((holding, holdingIndex) => {
              const color = chartColors[holdingIndex % chartColors.length];
              const points = plotted
                .map((point, index) => {
                  const value = point.assets[holding.ticker];
                  return value == null ? null : `${x(index)},${y(value)}`;
                })
                .filter((point): point is string => point !== null);
              return points.length > 1 ? (
                <polyline
                  key={holding.ticker}
                  points={points.join(" ")}
                  fill="none"
                  stroke={color}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              ) : null;
            })}
            <text x={chart.left} y="199" className="chart-axis-label">{plotted[0]?.date.slice(5)}</text>
            <text x={chart.right} y="199" textAnchor="end" className="chart-axis-label">{plotted[plotted.length - 1]?.date.slice(5)}</text>
          </svg>
        )}
      </div>
      <div className="chart-legend">
        {visibleHoldings.map((holding) => (
          <span className="chart-legend-item" key={holding.ticker}>
            <i style={{ background: chartColors[visibleHoldings.indexOf(holding) % chartColors.length] }} />
            {holding.ticker}
          </span>
        ))}
      </div>
      <p className="chart-footnote">Indexed prices are not portfolio returns and do not include your historical transaction dates or cash flows.</p>
    </Card>
  );
}

function AllocationCard({ buckets }: { buckets: BucketSummary[] }) {
  return (
    <Card className="allocation-card">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Portfolio mix</p>
          <h2>Allocation targets</h2>
        </div>
        <span className="subtle-badge">60 / 40 strategy</span>
      </div>
      <AllocationDonut buckets={buckets} />
      <div className="bucket-bars">
        {buckets.map((bucket) => (
          <div className="bucket-row" key={bucket.id}>
            <div className="bucket-row-top">
              <span>{bucket.name}</span>
              <strong>{bucket.currentPercent == null ? "—" : `${bucket.currentPercent.toFixed(1)}%`}</strong>
            </div>
            <div className="progress-track">
              <span
                className="progress-fill"
                style={{
                  width: `${Math.max(0, Math.min(100, bucket.currentPercent ?? 0))}%`,
                  background: bucketColors[bucket.id],
                }}
              />
              <i style={{ left: `${bucket.targetPercent}%` }} title={`Target ${bucket.targetPercent}%`} />
            </div>
            <div className="bucket-meta">
              <span>{money(bucket.valueHkd)} current</span>
              <span className={bucket.driftPercent != null && bucket.driftPercent < 0 ? "negative" : "positive"}>
                Drift {percent(bucket.driftPercent)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function TrendBadge({ holding }: { holding: Holding }) {
  if (holding.priceVsSma20 == null) {
    return <span className="status-badge neutral">Not enough data</span>;
  }
  return (
    <span className={`status-badge ${holding.priceVsSma20 === "Above" ? "good" : "caution"}`}>
      {holding.priceVsSma20 === "Above" ? "Above 20-day avg" : "Below 20-day avg"}
    </span>
  );
}

function HoldingsTable({ holdings }: { holdings: Holding[] }) {
  return (
    <Card className="holdings-card" id="holdings">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Your positions</p>
          <h2>Holdings &amp; trend</h2>
        </div>
        <span className="subtle-badge">{holdings.length} assets tracked</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Asset</th>
              <th>Market value</th>
              <th>Momentum</th>
              <th>12-month scenario</th>
              <th>Annual volatility</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((holding) => (
              <tr key={holding.ticker}>
                <td>
                  <div className="asset-cell">
                    <span className={`asset-avatar ${holding.bucket}`}>{initials(holding.ticker.replace(".HK", ""))}</span>
                    <span className="asset-details">
                      <strong>{holding.ticker}</strong>
                      <small>{holding.name}</small>
                    </span>
                  </div>
                </td>
                <td>
                  <strong>{money(holding.valueHkd)}</strong>
                  <small className="table-subline">{holding.shares.toLocaleString()} shares</small>
                </td>
                <td>
                  <TrendBadge holding={holding} />
                  <small className="table-subline">{percent(holding.momentumPercent)} vs SMA20</small>
                </td>
                <td>
                  <strong>{money(holding.projectedValueHkd)}</strong>
                  <small className={`table-subline ${holding.annualizedGrowthPercent != null && holding.annualizedGrowthPercent < 0 ? "negative" : "positive"}`}>
                    {percent(holding.annualizedGrowthPercent)} historical drift
                  </small>
                </td>
                <td>
                  <strong>{percent(holding.annualizedVolatilityPercent)}</strong>
                  <small className="table-subline">{holding.longTermStatus ?? "Long-term trend unavailable"}</small>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="chart-footnote">Historical growth scenarios and volatility are estimates, not predictions or guarantees.</p>
    </Card>
  );
}

function RecommendationCard({ holdings }: { holdings: Holding[] }) {
  const oneTime = holdings.filter((holding) => holding.orderType === "one-time" && holding.allocationHkd > 0);
  const plans = holdings.filter((holding) => holding.orderType === "monthly-plan" && holding.allocationHkd > 0);
  const withheld = holdings.filter((holding) => holding.allocationHkd <= 0 && holding.dataIssue == null && holding.downsideVolatilityPercent == null);
  return (
    <Card className="recommendation-card" id="actions">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Monthly planning guide</p>
          <h2>Suggested next steps</h2>
        </div>
        <span className="subtle-badge">No trades placed</span>
      </div>
      <div className="action-columns">
        <div className="action-group">
          <div className="action-title"><span className="action-icon green"><Icon name="arrow" size={16} /></span><strong>One-time orders</strong></div>
          {oneTime.length ? oneTime.map((holding) => (
            <div className="action-item" key={holding.ticker}>
              <div><strong>{holding.ticker}</strong><small>{holding.market === "HKEX" ? "HKEX listed · check board lots" : "Global asset · at/above threshold"}</small></div>
              <strong>{money(holding.allocationHkd)}</strong>
            </div>
          )) : <p className="empty-action">No one-time order amounts are currently recommended.</p>}
        </div>
        <div className="action-group">
          <div className="action-title"><span className="action-icon orange"><Icon name="info" size={16} /></span><strong>EasyInvest monthly plans</strong></div>
          {plans.length ? plans.map((holding) => (
            <div className="action-item" key={holding.ticker}>
              <div><strong>{holding.ticker}</strong><small>Below HK$7,800 · use a DCA plan</small></div>
              <strong>{money(holding.allocationHkd)}</strong>
            </div>
          )) : <p className="empty-action">No below-threshold global fund plan is recommended right now.</p>}
        </div>
      </div>
      {withheld.length > 0 && (
        <div className="withheld-note">
          <Icon name="info" size={16} />
          <span>Some new allocations are withheld because downside risk data is unavailable or above your configured limit: {withheld.map((holding) => holding.ticker).join(", ")}.</span>
        </div>
      )}
      <p className="execution-note">This is a planning guide, not a trade instruction. Confirm prices, fees, board lots, instrument eligibility, and current HSBC/EasyInvest rules before acting.</p>
    </Card>
  );
}

function LoadingScreen() {
  return (
    <main className="loading-screen">
      <div className="loading-mark">N</div>
      <span className="loading-spinner" />
      <strong>Loading your report</strong>
      <span>Reading the latest generated portfolio data…</span>
    </main>
  );
}

function App() {
  const [report, setReport] = useState<InvestmentReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadReport = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/report.json${manual ? `?t=${Date.now()}` : ""}`, {
        cache: manual ? "no-store" : "default",
      });
      if (!response.ok) {
        throw new Error(
          response.status === 404
            ? "No generated report was found. Run `python optimizer.py` from the project root, then refresh this page."
            : `Could not load the report (HTTP ${response.status}).`,
        );
      }
      const payload: unknown = await response.json();
      if (
        typeof payload !== "object" ||
        payload === null ||
        !("summary" in payload) ||
        !("holdings" in payload) ||
        !Array.isArray(payload.holdings)
      ) {
        throw new Error("The generated report data has an unexpected format. Run `python optimizer.py` again.");
      }
      setReport(payload as InvestmentReport);
    } catch (caught) {
      setReport(null);
      setError(caught instanceof Error ? caught.message : "Unable to load the report.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  const orderedHoldings = useMemo(
    () => report?.holdings ?? [],
    [report],
  );

  if (loading) return <LoadingScreen />;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="Northstar overview">
          <span className="brand-mark">N</span>
          <span><strong>northstar</strong><small>INVESTMENT DESK</small></span>
        </a>
        <p className="nav-caption">WORKSPACE</p>
        <nav className="side-nav" aria-label="Main navigation">
          <a className="active" href="#overview"><Icon name="grid" /><span>Overview</span></a>
          <a href="#holdings"><Icon name="chart" /><span>Holdings &amp; trends</span></a>
          <a href="#risk"><Icon name="shield" /><span>Risk overview</span></a>
          <a href="#actions"><Icon name="settings" /><span>Plan &amp; actions</span></a>
        </nav>
        <div className="sidebar-bottom">
          <div className="data-status"><span className="online-dot" /><span><strong>Report data</strong><small>Generated by your local Python app</small></span></div>
          <div className="sidebar-disclaimer">Private by design<br />No brokerage connection</div>
        </div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><b>/</b><strong>Overview</strong></div>
          <div className="topbar-actions">
            <span className="updated-label"><span className="online-dot" />{report ? `Updated ${dateTime(report.generatedAt)}` : "No report loaded"}</span>
            <button className="refresh-button" onClick={() => void loadReport(true)} disabled={refreshing}>
              <span className={refreshing ? "spinning" : ""}><Icon name="refresh" size={16} /></span>
              {refreshing ? "Refreshing" : "Refresh"}
            </button>
            <span className="profile-avatar">U</span>
          </div>
        </header>

        <div className="dashboard">
          <section className="welcome-row">
            <div>
              <p className="eyebrow">PERSONAL PORTFOLIO · DAILY SNAPSHOT</p>
              <h1>Good day<span className="title-period">.</span></h1>
              <p className="welcome-copy">A clearer view of your investments, momentum, and risk.</p>
            </div>
            <div className="snapshot-date">
              <span className="calendar-glyph">◷</span>
              <span><small>REPORT DATE</small><strong>{report ? dateTime(report.generatedAt) : "Awaiting report"}</strong></span>
            </div>
          </section>

          {error && (
            <div className="error-banner" role="alert">
              <Icon name="info" size={18} />
              <div><strong>Report unavailable</strong><p>{error}</p></div>
              <button onClick={() => void loadReport(true)}>Try again</button>
            </div>
          )}

          {report && (
            <>
              {report.warnings.length > 0 && (
                <div className="warning-banner" role="status">
                  <span className="warning-mark">!</span>
                  <div><strong>Review data notes</strong><p>{report.warnings.length} data or risk note{report.warnings.length === 1 ? "" : "s"} need attention. See details below.</p></div>
                  <a href="#actions">View notes <Icon name="arrow" size={14} /></a>
                </div>
              )}

              <section className="metrics-grid" aria-label="Portfolio summary">
                <MetricCard
                  label="Total portfolio value"
                  value={money(report.summary.portfolioValueHkd)}
                  detail={`${report.holdings.filter((holding) => holding.shares > 0).length} active positions · HKD`}
                  icon="grid"
                  tone="green"
                />
                <MetricCard
                  label="12-month scenario"
                  value={money(report.summary.projectedValueHkd)}
                  detail="Historical drift · not a prediction"
                  icon="chart"
                  tone="blue"
                />
                <MetricCard
                  label="Annualized volatility"
                  value={percent(report.summary.annualizedVolatilityPercent)}
                  detail="Daily return standard deviation × √252"
                  icon="shield"
                  tone="orange"
                />
                <MetricCard
                  label="95% monthly VaR estimate"
                  value={money(report.summary.monthlyVarHkd)}
                  detail={report.summary.monthlyVarPercent == null ? "Insufficient portfolio history" : `${report.summary.monthlyVarPercent.toFixed(1)}% historical monthly swing`}
                  icon="info"
                  tone="purple"
                />
              </section>

              <section className="overview-grid">
                <AllocationCard buckets={report.buckets} />
                <HistoryChart history={report.history} holdings={report.holdings} />
              </section>

              <section id="risk" className="risk-strip">
                <div className="risk-strip-icon"><Icon name="shield" size={20} /></div>
                <div className="risk-strip-copy">
                  <strong>Downside risk, in plain sight</strong>
                  <span>Estimated 95% worst historical month dollar swing on the current portfolio.</span>
                </div>
                <div className="risk-strip-value">
                  <strong>{money(report.summary.monthlyVarHkd)}</strong>
                  <span>of {money(report.summary.portfolioValueHkd)} portfolio value</span>
                </div>
              </section>

              <HoldingsTable holdings={orderedHoldings} />
              <RecommendationCard holdings={orderedHoldings} />

              {report.warnings.length > 0 && (
                <Card className="data-notes">
                  <div className="section-heading compact">
                    <div><p className="eyebrow">Transparency</p><h2>Data &amp; risk notes</h2></div>
                  </div>
                  <ul>{report.warnings.map((warning, index) => <li key={`${warning}-${index}`}>{warning}</li>)}</ul>
                </Card>
              )}

              <footer className="page-footer">
                <span><span className="online-dot" />Your report is generated locally from market data</span>
                <span>Planning estimates only · Not investment advice</span>
              </footer>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
