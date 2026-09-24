export type Platform = "tiktok_shop" | "amazon" | "temu" | "shein" | string;

export interface ProductInput {
  name: string;
  sku: string;
  purchase_cost: string;
  packaging_cost: string;
  weight_kg: string;
  volume_cm3: string;
  currency: string;
}

export interface PlatformConfig {
  id?: number;
  platform: Platform;
  original_price: string;
  shipping_cost: string;
  platform_commission_rate: string;
  creator_commission_rate: string;
  payment_fee_rate: string;
  fx_loss_rate: string;
  tariff_rate: string;
  tariff_basis: "product_cost" | "selling_price";
  return_rate: string;
  return_shipping_nonrecoverable: string;
  return_product_loss_rate: string;
  platform_nonrefundable_fee_rate: string;
  other_variable_cost: string;
  demo_default: boolean;
}

export interface Product extends ProductInput {
  id: number;
  created_at: string;
  platform_configs: PlatformConfig[];
}

export interface PromotionActivity {
  platform: Platform;
  activity_name: string;
  activity_type: string;
  source_url: string | null;
  start_date: string | null;
  end_date: string | null;
  discount_type: "percentage" | "fixed_amount" | "fixed_price" | "none";
  discount_value: string;
  minimum_discount: string | null;
  platform_commission_rate: string | null;
  extra_commission_rate: string;
  creator_commission_rate: string | null;
  shipping_subsidy: string;
  seller_shipping_cost: string | null;
  platform_subsidy: string;
  coupon_cost_bearer: string;
  coupon_amount: string;
  minimum_price_requirement: string | null;
  minimum_stock_requirement: number | null;
  estimated_traffic_lift: string | null;
  estimated_sales: number;
  return_rate_override: string | null;
  currency: string;
  notes: string;
  raw_text: string;
  parse_confidence: string;
  missing_fields: string[];
  registration_fee: string;
  ad_budget: string;
  creative_cost: string;
  creator_fixed_fee: string;
}

export interface ProfitAnalysisRequest {
  product: ProductInput;
  platform_config: PlatformConfig;
  activity: PromotionActivity;
}

export interface CalculationBreakdown {
  item: string;
  formula: string;
  input_values: Record<string, string | number>;
  amount: string;
  description: string;
}

export interface ProfitResult {
  original_price: string;
  discount_amount: string;
  selling_price: string;
  revenue: string;
  total_cost: string;
  unit_profit: string;
  profit_margin: string;
  estimated_sales: number;
  estimated_revenue: string;
  estimated_total_profit: string;
  break_even_price: string | null;
  break_even_quantity: number | null;
  fixed_cost: string;
  risk_level: "HIGHLY_RECOMMENDED" | "RECOMMENDED" | "CAUTION" | "NOT_RECOMMENDED" | "LOSS";
  risk_label: string;
  assumptions: string[];
  breakdown: CalculationBreakdown[];
}

export interface ScenarioResult {
  name: string;
  sales_multiplier: string;
  return_rate: string;
  shipping_multiplier: string;
  unit_profit: string;
  profit_margin: string;
  total_profit: string;
  profitable: boolean;
}

export interface ParsedPromotion {
  activity: PromotionActivity;
  recognized_fields: Record<string, string | number | null>;
  missing_suggestions: Array<{ field: string; label: string; reason: string; default_action: string }>;
  fetch_warning: string | null;
}

export interface AnalysisRun {
  analysis_id: number | null;
  result: ProfitResult;
  scenarios: ScenarioResult[];
  recommendations: string[];
}

export interface HistoricalMetrics {
  period: string;
  visitors: number | null;
  orders: number | null;
  returns: number | null;
  source: string;
}

export interface ResearchReport {
  provider: "deepseek" | "rules";
  historical: HistoricalMetrics & { conversion_rate?: number; return_rate?: number };
  sources: Array<{ url: string; title: string }>;
  discovered_sources: Array<{ url: string; title: string }>;
  warnings: string[];
  missing_data: string[];
  dimensions: Array<{ name: string; finding: string; evidence: string; status: "verified" | "assumption" | "missing"; action: string }>;
}

export interface DemoCase {
  id: number;
  product_id: number;
  request: ProfitAnalysisRequest;
  result: ProfitResult;
}

export interface BootstrapData { products: Product[]; cases: DemoCase[]; }

export interface HistoryItem {
  id: number;
  activity_id: number;
  product_id: number;
  activity_name: string;
  product_name: string;
  platform: Platform;
  unit_profit: string;
  profit_margin: string;
  estimated_total_profit: string;
  risk_level: ProfitResult["risk_level"];
  cost_drivers?: Array<{ item: string; amount: string }>;
  created_at: string;
}

export type Recommendation = string;
export interface ComparisonResult { case: DemoCase; rank: number; }
