export type BucketId = "steady" | "risk";
export type OrderType = "one-time" | "monthly-plan" | "none";

export interface ReportSummary {
  portfolioValueHkd: number;
  monthlySalaryHkd: number;
  monthlyBudgetHkd: number;
  spareCashRemainingHkd: number;
  spareCashDeploymentHkd: number;
  cashInjectionHkd: number;
  targetPoolHkd: number;
  projectedValueHkd: number | null;
  annualizedVolatilityPercent: number | null;
  monthlyVarPercent: number | null;
  monthlyVarHkd: number | null;
  holdingsDataComplete: boolean;
}

export interface BucketSummary {
  id: BucketId;
  name: string;
  valueHkd: number;
  currentPercent: number | null;
  targetPercent: number;
  driftPercent: number | null;
  targetValueHkd: number;
  deficitHkd: number;
  targetedInjectionHkd: number;
  allocatedHkd: number;
  unallocatedHkd: number;
}

export interface Holding {
  ticker: string;
  name: string;
  bucket: BucketId;
  bucketLabel: string;
  market: "HKEX" | "GLOBAL";
  currency: "HKD" | "USD";
  shares: number;
  targetWeightInBucket: number;
  priceHkd: number | null;
  valueHkd: number;
  allocationHkd: number;
  orderType: OrderType;
  momentumPercent: number | null;
  priceVsSma20: "Above" | "Below" | null;
  sma20Hkd: number | null;
  longTermStatus: "Above 200-day SMA" | "Below 200-day SMA" | null;
  longTrend: "Rising" | "Falling" | "Flat" | null;
  sma200Hkd: number | null;
  annualizedGrowthPercent: number | null;
  projectedValueHkd: number | null;
  annualizedVolatilityPercent: number | null;
  downsideVolatilityPercent: number | null;
  monthlyVarPercent: number | null;
  dataIssue: string | null;
}

export interface HistoryPoint {
  date: string;
  assets: Record<string, number | null>;
}

export interface InvestmentReport {
  generatedAt: string;
  currency: string;
  historyPeriod: string;
  summary: ReportSummary;
  buckets: BucketSummary[];
  holdings: Holding[];
  history: HistoryPoint[];
  warnings: string[];
}
