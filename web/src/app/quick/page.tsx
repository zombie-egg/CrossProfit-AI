"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { percent } from "@/lib/utils";
import type { AnalysisRun, ProfitAnalysisRequest } from "@/types";

type Field = "price" | "discount" | "sales" | "purchase" | "packaging" | "shipping" | "platformRate" | "activityRate" | "creatorRate" | "paymentRate" | "fxRate" | "tariffRate" | "returnRate" | "returnShipping" | "productLossRate" | "nonrefundableRate" | "otherCost" | "coupon" | "platformSubsidy" | "shippingSubsidy" | "fixedCost";
const initial: Record<Field, string> = {
  price: "", discount: "0", sales: "1", purchase: "", packaging: "0", shipping: "", platformRate: "", activityRate: "0", creatorRate: "0", paymentRate: "0", fxRate: "0", tariffRate: "0", returnRate: "", returnShipping: "0", productLossRate: "0", nonrefundableRate: "0", otherCost: "0", coupon: "0", platformSubsidy: "0", shippingSubsidy: "0", fixedCost: "0",
};
const groups: Array<{ title: string; fields: Array<[Field, string, boolean?]> }> = [
  { title: "成交与商品成本", fields: [["price", "原售价", true], ["discount", "活动折扣 %"], ["sales", "预计销量", true], ["purchase", "采购成本 / 单", true], ["packaging", "包装成本 / 单"], ["shipping", "卖家物流 / 单", true]] },
  { title: "实际费率", fields: [["platformRate", "平台佣金 %", true], ["activityRate", "活动附加费 %"], ["creatorRate", "达人佣金 %"], ["paymentRate", "支付费率 %"], ["fxRate", "汇损率 %"], ["tariffRate", "关税率 %"]] },
  { title: "退货与其他", fields: [["returnRate", "历史退货率 %", true], ["returnShipping", "退货不可回收运费 / 单"], ["productLossRate", "退货商品损耗 %"], ["nonrefundableRate", "退货不退平台费 %"], ["otherCost", "其他变动成本 / 单"], ["coupon", "卖家优惠券 / 单"], ["platformSubsidy", "平台补贴 / 单"], ["shippingSubsidy", "物流补贴 / 单"], ["fixedCost", "活动固定投入"]] },
];
const percentageFields = new Set<Field>(["discount", "platformRate", "activityRate", "creatorRate", "paymentRate", "fxRate", "tariffRate", "returnRate", "productLossRate", "nonrefundableRate"]);

export default function QuickPage() {
  const [values, setValues] = useState(initial);
  const [platform, setPlatform] = useState("tiktok_shop");
  const [currency, setCurrency] = useState("USD");
  const [source, setSource] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const rate = (key: Field) => String(Number(values[key]) / 100);
  const amount = (value: string | number) => `${currency} ${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const required = groups.flatMap(g => g.fields.filter(f => f[2]).map(f => f[0]));
  const valid = required.every(key => values[key].trim() !== "") && source.trim() !== "" && confirmed && Object.entries(values).every(([key, value]) => value === "" || (Number.isFinite(Number(value)) && Number(value) >= 0 && (!percentageFields.has(key as Field) || Number(value) <= 100))) && Number(values.price) > 0 && Number.isInteger(Number(values.sales)) && Number(values.sales) >= 1;
  const calculate = async () => {
    if (!valid) return;
    setBusy(true); setError(""); setRun(null);
    const request: ProfitAnalysisRequest = {
      product: { name: "手动测算商品", sku: "manual", purchase_cost: values.purchase, packaging_cost: values.packaging, weight_kg: "0", volume_cm3: "0", currency },
      platform_config: { platform, original_price: values.price, shipping_cost: values.shipping, platform_commission_rate: rate("platformRate"), creator_commission_rate: rate("creatorRate"), payment_fee_rate: rate("paymentRate"), fx_loss_rate: rate("fxRate"), tariff_rate: rate("tariffRate"), tariff_basis: "product_cost", return_rate: rate("returnRate"), return_shipping_nonrecoverable: values.returnShipping, return_product_loss_rate: rate("productLossRate"), platform_nonrefundable_fee_rate: rate("nonrefundableRate"), other_variable_cost: values.otherCost, demo_default: false },
      activity: { platform, activity_name: "手动单品测算", activity_type: "promotion", source_url: null, start_date: null, end_date: null, discount_type: "percentage", discount_value: rate("discount"), minimum_discount: null, platform_commission_rate: null, extra_commission_rate: rate("activityRate"), creator_commission_rate: null, shipping_subsidy: values.shippingSubsidy, seller_shipping_cost: null, platform_subsidy: values.platformSubsidy, coupon_cost_bearer: "seller", coupon_amount: values.coupon, minimum_price_requirement: null, minimum_stock_requirement: null, estimated_traffic_lift: null, estimated_sales: Number(values.sales), return_rate_override: null, currency, notes: `费率来源：${source.trim()}`, raw_text: "", parse_confidence: "0", missing_fields: [], registration_fee: values.fixedCost, ad_budget: "0", creative_cost: "0", creator_fixed_fee: "0" },
    };
    try { setRun(await api.runAnalysis(request)); } catch (e) { setError(e instanceof Error ? e.message : "计算失败"); } finally { setBusy(false); }
  };
  return <div className="space-y-6">
    <Card><CardHeader><CardTitle>先算一个商品</CardTitle></CardHeader><CardContent className="space-y-3 text-sm text-slate-600"><p>无需 TikTok 接口权限或 Easyboss 授权。请从店铺费率页、活动报名页、采购台账、物流账单和近期退款记录填写实际数据。所有输入只用于本次预览，不自动归档。</p><p>空白必填项必须填写；其余 0 表示你确认该项不适用。金额统一使用同一币种，费率按百分数填写。</p></CardContent></Card>
    <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm">平台<select className="mt-2 h-10 w-full rounded-md border bg-white px-3" value={platform} onChange={e=>setPlatform(e.target.value)}><option value="tiktok_shop">TikTok Shop</option><option value="amazon">Amazon</option><option value="temu">Temu</option><option value="shein">SHEIN</option><option value="other">其他</option></select></label><label className="text-sm">币种<input className="mt-2 h-10 w-full rounded-md border bg-white px-3" value={currency} maxLength={3} onChange={e=>setCurrency(e.target.value.toUpperCase())}/></label></div>
    {groups.map(group=><Card key={group.title}><CardHeader><CardTitle>{group.title}</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{group.fields.map(([key,label,mandatory])=><label className="text-sm" key={key}><span>{label}{mandatory&&<span className="ml-1 text-red-600">*</span>}</span><Input className="mt-2" type="number" min="0" max={percentageFields.has(key)?"100":undefined} step={key==="sales"?"1":"any"} value={values[key]} onChange={e=>{setValues({...values,[key]:e.target.value});setRun(null);}}/></label>)}</CardContent></Card>)}
    <Card><CardContent className="space-y-4 pt-6"><label className="block text-sm">费率来源与日期 *<Input className="mt-2" value={source} onChange={e=>{setSource(e.target.value);setRun(null);}} placeholder="例：店铺后台费率页，2026-09-23；活动报名页"/></label><label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} className="mt-1"/><span>我已核对输入数据。测算是活动前预测，退货率和销量等假设需在活动后与实际账单复核。</span></label><Button disabled={!valid||busy||currency.length!==3} onClick={()=>void calculate()}>{busy?"计算中":"计算单品利润"}</Button>{error&&<p role="alert" className="text-sm text-red-600">{error}</p>}</CardContent></Card>
    {run&&<Card><CardHeader><CardTitle>测算结果 · {currency}</CardTitle></CardHeader><CardContent className="space-y-5"><div className="grid gap-4 sm:grid-cols-3"><div><p className="text-sm text-slate-500">单件利润</p><p className="text-2xl font-semibold">{amount(run.result.unit_profit)}</p></div><div><p className="text-sm text-slate-500">预计总利润</p><p className="text-2xl font-semibold">{amount(run.result.estimated_total_profit)}</p></div><div><p className="text-sm text-slate-500">利润率</p><p className="text-2xl font-semibold">{percent(run.result.profit_margin)}</p></div></div><p className="flex items-center gap-2 text-sm text-amber-700"><AlertTriangle className="size-4"/>预测结果依赖你填写的费率、销量和退货假设；请以结算单复核。</p><div className="divide-y border-t">{run.result.breakdown.map(item=><div key={item.item} className="flex justify-between gap-3 py-2 text-sm"><span>{item.item}</span><span className="font-medium">{amount(item.amount)}</span></div>)}</div><p className="text-xs text-slate-500">费率来源：{source}</p></CardContent></Card>}
  </div>;
}
