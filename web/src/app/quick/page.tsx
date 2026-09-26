"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { percent } from "@/lib/utils";
import type { PricingTarget, PricingTemplate, PricingTemplateInput, ProfitAnalysisRequest, ProfitResult } from "@/types";

type Field = "price" | "discount" | "sales" | "purchase" | "packaging" | "shipping" | "platformRate" | "activityRate" | "creatorRate" | "paymentRate" | "fxRate" | "tariffRate" | "returnRate" | "returnShipping" | "productLossRate" | "nonrefundableRate" | "otherCost" | "coupon" | "platformSubsidy" | "shippingSubsidy" | "fixedCost";
type PricingMode = "forward" | "target";
const initial: Record<Field, string> = {
  price: "", discount: "0", sales: "1", purchase: "", packaging: "0", shipping: "", platformRate: "", activityRate: "0", creatorRate: "0", paymentRate: "0", fxRate: "0", tariffRate: "0", returnRate: "", returnShipping: "0", productLossRate: "0", nonrefundableRate: "0", otherCost: "0", coupon: "0", platformSubsidy: "0", shippingSubsidy: "0", fixedCost: "0",
};
const groups: Array<{ title: string; fields: Array<[Field, string, boolean?]> }> = [
  { title: "成交与商品成本", fields: [["discount", "活动折扣 %"], ["sales", "预计销量", true], ["purchase", "采购成本 / 单", true], ["packaging", "包装成本 / 单"], ["shipping", "卖家物流 / 单", true]] },
  { title: "实际费率", fields: [["platformRate", "平台佣金 %", true], ["activityRate", "活动附加费 %"], ["creatorRate", "达人佣金 %"], ["paymentRate", "支付费率 %"], ["fxRate", "汇损率 %"], ["tariffRate", "关税率 %"]] },
  { title: "退货与其他", fields: [["returnRate", "历史退货率 %", true], ["returnShipping", "退货不可回收运费 / 单"], ["productLossRate", "退货商品损耗 %"], ["nonrefundableRate", "退货不退平台费 %"], ["otherCost", "其他变动成本 / 单"], ["coupon", "卖家优惠券 / 单"], ["platformSubsidy", "平台补贴 / 单"], ["shippingSubsidy", "物流补贴 / 单"], ["fixedCost", "活动固定投入"]] },
];
const percentageFields = new Set<Field>(["discount", "platformRate", "activityRate", "creatorRate", "paymentRate", "fxRate", "tariffRate", "returnRate", "productLossRate", "nonrefundableRate"]);
const required: Array<[Field, string]> = [["sales", "预计销量"], ["purchase", "采购成本"], ["shipping", "卖家物流"], ["platformRate", "平台佣金"], ["returnRate", "历史退货率"]];

function percentToRate(value: string): string {
  const [whole, fraction = ""] = value.split(".");
  const digits = `${whole}${fraction}`.replace(/^0+(?=\d)/, "").padStart(fraction.length + 3, "0");
  const scale = fraction.length + 2;
  return `${digits.slice(0, -scale)}.${digits.slice(-scale)}`;
}

function requestFrom(values: Record<Field, string>, platform: string, currency: string, category: string, mode: PricingMode, source: string, rateDate: string): ProfitAnalysisRequest {
  const rate = (field: Field) => percentToRate(values[field]);
  return {
    product: { name: "手动测算商品", sku: "manual", category, purchase_cost: values.purchase, packaging_cost: values.packaging, weight_kg: "0", volume_cm3: "0", currency },
    platform_config: { platform, original_price: mode === "forward" ? values.price : "0", shipping_cost: values.shipping, platform_commission_rate: rate("platformRate"), creator_commission_rate: rate("creatorRate"), payment_fee_rate: rate("paymentRate"), fx_loss_rate: rate("fxRate"), tariff_rate: rate("tariffRate"), tariff_basis: "product_cost", return_rate: rate("returnRate"), return_shipping_nonrecoverable: values.returnShipping, return_product_loss_rate: rate("productLossRate"), platform_nonrefundable_fee_rate: rate("nonrefundableRate"), other_variable_cost: values.otherCost, demo_default: false },
    activity: { platform, activity_name: "手动单品测算", activity_type: "promotion", source_url: null, start_date: null, end_date: null, discount_type: mode === "forward" ? "percentage" : "none", discount_value: mode === "forward" ? rate("discount") : "0", minimum_discount: null, platform_commission_rate: null, extra_commission_rate: rate("activityRate"), creator_commission_rate: null, shipping_subsidy: values.shippingSubsidy, seller_shipping_cost: null, platform_subsidy: values.platformSubsidy, coupon_cost_bearer: "seller", coupon_amount: values.coupon, minimum_price_requirement: null, minimum_stock_requirement: null, estimated_traffic_lift: null, estimated_sales: Number(values.sales), return_rate_override: null, currency, notes: source.trim() ? `费率来源：${source.trim()}` : "", raw_text: "", parse_confidence: "0", missing_fields: [], registration_fee: values.fixedCost, ad_budget: "0", creative_cost: "0", creator_fixed_fee: "0" },
    rate_source: source.trim() || null,
    rate_effective_date: rateDate || null,
  };
}

function validationMessage(values: Record<Field, string>, mode: PricingMode, targetMode: PricingTarget["mode"], targetValue: string, currency: string): string | null {
  const missing = required.filter(([field]) => values[field].trim() === "").map(([, label]) => label);
  if (mode === "forward" && !values.price.trim()) missing.push("原售价");
  if (mode === "target" && !targetValue.trim()) missing.push("目标利润");
  if (missing.length) return `请填写：${missing.join("、")}`;
  if (currency.length !== 3) return "请填写三位币种代码";
  for (const [field, value] of Object.entries(values) as Array<[Field, string]>) {
    if (value === "" || (mode === "target" && field === "discount")) continue;
    if (!/^\d+(?:\.\d+)?$/.test(value) || !Number.isFinite(Number(value)) || (percentageFields.has(field) && Number(value) > 100)) return `请核对 ${field}：金额和费率需为非负数字，百分比不超过 100`;
  }
  if (!Number.isInteger(Number(values.sales)) || Number(values.sales) < 1) return "预计销量必须是至少 1 的整数";
  if (mode === "forward" && Number(values.price) <= 0) return "原售价必须大于 0";
  if (mode === "target" && (!/^\d+(?:\.\d+)?$/.test(targetValue) || !Number.isFinite(Number(targetValue)) || (targetMode === "fixed_margin" && Number(targetValue) >= 100))) return "目标金额需为非负数字；目标利润率须小于 100%";
  return null;
}

export default function QuickPage() {
  const [values, setValues] = useState(initial);
  const [mode, setMode] = useState<PricingMode>("forward");
  const [targetMode, setTargetMode] = useState<PricingTarget["mode"]>("fixed_margin");
  const [targetValue, setTargetValue] = useState("");
  const [platform, setPlatform] = useState("tiktok_shop");
  const [currency, setCurrency] = useState("USD");
  const [category, setCategory] = useState("uncategorized");
  const [source, setSource] = useState("");
  const [rateDate, setRateDate] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [preview, setPreview] = useState<{ result: ProfitResult; price: string; mode: PricingMode; currency: string; source: string } | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState("");
  const [unreachable, setUnreachable] = useState("");
  const [templates, setTemplates] = useState<PricingTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [templateError, setTemplateError] = useState("");
  const [savingTemplate, setSavingTemplate] = useState(false);
  const requestVersion = useRef(0);
  const validation = useMemo(() => validationMessage(values, mode, targetMode, targetValue, currency), [values, mode, targetMode, targetValue, currency]);
  const selected = templates.find((template) => String(template.id) === selectedTemplate);

  useEffect(() => { void api.pricingTemplates().then(setTemplates).catch((reason) => setTemplateError(reason instanceof Error ? reason.message : "无法读取模板")); }, []);
  useEffect(() => {
    const version = ++requestVersion.current;
    let cancelled = false;
    if (validation) { setCalculating(false); setError(""); setUnreachable(""); return; }
    setCalculating(true); setError(""); setUnreachable("");
    const timer = window.setTimeout(() => {
      const request = requestFrom(values, platform, currency, category, mode, source, rateDate);
      const response = mode === "forward"
        ? api.profit(request).then((result) => ({ reachable: true, price: result.selling_price, result, reason: null }))
        : api.targetPrice({ request, target: { mode: targetMode, value: targetMode === "fixed_margin" ? percentToRate(targetValue) : targetValue } });
      void response.then((answer) => {
        if (cancelled || requestVersion.current !== version) return;
        if (answer.reachable && answer.result && answer.price) setPreview({ result: answer.result, price: answer.price, mode, currency, source });
        else setUnreachable(answer.reason ?? "目标价格不可达");
      }).catch((reason) => {
        if (!cancelled && requestVersion.current === version) setError(reason instanceof Error ? reason.message : "计算失败");
      }).finally(() => { if (!cancelled && requestVersion.current === version) setCalculating(false); });
    }, 300);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [values, platform, currency, category, mode, targetMode, targetValue, source, rateDate, validation]);

  const applyTemplate = (id: string) => {
    setSelectedTemplate(id);
    const template = templates.find((item) => String(item.id) === id);
    if (!template) return;
    const config = template.defaults.platform_config;
    const asPercent = (value: string) => String(Number(value) * 100);
    setValues((current) => ({ ...current, purchase: template.defaults.purchase_cost, packaging: template.defaults.packaging_cost,
      shipping: config.shipping_cost, platformRate: asPercent(config.platform_commission_rate), creatorRate: asPercent(config.creator_commission_rate),
      paymentRate: asPercent(config.payment_fee_rate), fxRate: asPercent(config.fx_loss_rate), tariffRate: asPercent(config.tariff_rate),
      returnRate: asPercent(config.return_rate), returnShipping: config.return_shipping_nonrecoverable,
      productLossRate: asPercent(config.return_product_loss_rate), nonrefundableRate: asPercent(config.platform_nonrefundable_fee_rate), otherCost: config.other_variable_cost }));
    setMode("target"); setTargetMode(template.target_mode);
    setTargetValue(template.target_mode === "fixed_margin" ? asPercent(template.target_value) : template.target_value);
    setPlatform(template.platform); setCurrency(template.currency); setCategory(template.category);
    setSource(template.rate_source); setRateDate(template.rate_effective_date); setConfirmed(false);
  };

  const saveTemplate = async () => {
    if (validation || mode !== "target" || !templateName.trim() || !category.trim() || !source.trim() || !rateDate || !confirmed) return;
    setSavingTemplate(true); setTemplateError("");
    try {
      const request = requestFrom(values, platform, currency, category, mode, source, rateDate);
      const payload: PricingTemplateInput = { name: templateName.trim(), platform, category, currency,
        target_mode: targetMode, target_value: targetMode === "fixed_margin" ? percentToRate(targetValue) : targetValue,
        defaults: { platform_config: request.platform_config, purchase_cost: values.purchase, packaging_cost: values.packaging },
        rate_source: source.trim(), rate_effective_date: rateDate };
      const saved = await api.createPricingTemplate(payload);
      setTemplates((current) => [saved, ...current]); setSelectedTemplate(String(saved.id)); setTemplateName("");
    } catch (reason) { setTemplateError(reason instanceof Error ? reason.message : "保存模板失败"); }
    finally { setSavingTemplate(false); }
  };

  const amount = (value: string | number, code: string) => `${code} ${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return <div className="space-y-6">
    <Card><CardHeader><CardTitle>先算一个商品</CardTitle></CardHeader><CardContent className="space-y-3 text-sm text-slate-600"><p>输入店铺实际成本与费率。实时预览由后端 Decimal 引擎计算，不自动归档。</p><p>目标售价是单件成交价；目标模式不再套用活动折扣。固定活动投入只影响盈亏平衡销量，不摊进单件售价。</p></CardContent></Card>
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(330px,0.85fr)] lg:items-start">
      <div className="space-y-6">
        <div className="flex flex-wrap gap-2" role="group" aria-label="定价模式"><Button type="button" variant={mode === "forward" ? "default" : "outline"} onClick={() => setMode("forward")}>按售价算利润</Button><Button type="button" variant={mode === "target" ? "default" : "outline"} onClick={() => setMode("target")}>按目标利润算售价</Button></div>
        <Card><CardHeader><CardTitle>套用定价模板</CardTitle></CardHeader><CardContent className="space-y-3"><select className="h-10 w-full rounded-md border bg-white px-3 text-sm" value={selectedTemplate} onChange={(event) => applyTemplate(event.target.value)}><option value="">选择已保存模板</option>{templates.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.platform}{item.stale ? "（费率可能已过期）" : ""}</option>)}</select>{selected?.stale && <p className="text-sm text-amber-700">这份模板的费率可能已过期，请核对来源和生效日期。</p>}</CardContent></Card>
        <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm">平台<select className="mt-2 h-10 w-full rounded-md border bg-white px-3" value={platform} onChange={(event) => setPlatform(event.target.value)}><option value="taobao">淘宝</option><option value="pinduoduo">拼多多</option><option value="douyin">抖音电商</option><option value="xianyu">闲鱼</option><option value="tiktok_shop">TikTok Shop</option><option value="amazon">Amazon</option><option value="temu">Temu</option><option value="shein">SHEIN</option><option value="other">其他</option></select></label><label className="text-sm">币种<Input className="mt-2" value={currency} maxLength={3} onChange={(event) => setCurrency(event.target.value.toUpperCase())}/></label></div>
        <Card><CardHeader><CardTitle>成交与商品成本</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {mode === "forward" ? <label className="text-sm"><span>原售价 <span className="text-red-600">*</span></span><Input className="mt-2" type="number" min="0" step="any" value={values.price} onChange={(event) => setValues({ ...values, price: event.target.value })}/></label> : <><label className="text-sm">目标模式<select className="mt-2 h-10 w-full rounded-md border bg-white px-3" value={targetMode} onChange={(event) => setTargetMode(event.target.value as PricingTarget["mode"])}><option value="fixed_amount">固定金额</option><option value="fixed_margin">固定比例</option></select></label><label className="text-sm"><span>{targetMode === "fixed_margin" ? "目标利润率 %" : "目标单件利润"} <span className="text-red-600">*</span></span><Input className="mt-2" type="number" min="0" max={targetMode === "fixed_margin" ? "99.999" : undefined} step="any" value={targetValue} onChange={(event) => setTargetValue(event.target.value)}/></label></>}
          {groups[0].fields.filter(([field]) => mode === "forward" || field !== "discount").map(([field, label, mandatory]) => <label className="text-sm" key={field}><span>{label}{mandatory && <span className="ml-1 text-red-600">*</span>}</span><Input className="mt-2" type="number" min="0" max={percentageFields.has(field) ? "100" : undefined} step={field === "sales" ? "1" : "any"} value={values[field]} onChange={(event) => setValues({ ...values, [field]: event.target.value })}/></label>)}
        </CardContent></Card>
        {groups.slice(1).map((group) => <Card key={group.title}><CardHeader><CardTitle>{group.title}</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{group.fields.map(([field, label, mandatory]) => <label className="text-sm" key={field}><span>{label}{mandatory && <span className="ml-1 text-red-600">*</span>}</span><Input className="mt-2" type="number" min="0" max={percentageFields.has(field) ? "100" : undefined} step="any" value={values[field]} onChange={(event) => setValues({ ...values, [field]: event.target.value })}/></label>)}</CardContent></Card>)}
        <Card><CardHeader><CardTitle>费率来源与模板</CardTitle></CardHeader><CardContent className="space-y-4"><div className="grid gap-4 sm:grid-cols-2"><label className="text-sm">费率来源<Input className="mt-2" value={source} onChange={(event) => setSource(event.target.value)} placeholder="店铺后台费率页、活动报名页"/></label><label className="text-sm">费率生效日期<Input className="mt-2" type="date" value={rateDate} onChange={(event) => setRateDate(event.target.value)}/></label></div><label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} className="mt-1"/><span>我已核对输入数据。测算是活动前预测，退货率和销量等假设需在活动后与实际账单复核。</span></label><div className="flex flex-wrap gap-3"><Input className="max-w-xs" value={templateName} onChange={(event) => setTemplateName(event.target.value)} placeholder="模板名称，例如：箱包目标毛利"/><Input className="max-w-xs" value={category} onChange={(event) => setCategory(event.target.value)} placeholder="类目"/><Button type="button" disabled={savingTemplate || mode !== "target" || !!validation || !templateName.trim() || !category.trim() || !source.trim() || !rateDate || !confirmed} onClick={() => void saveTemplate()}>{savingTemplate ? "保存中" : "另存为模板"}</Button></div><p className="text-xs text-slate-500">预览无需来源或勾选；保存模板需填写费率来源、日期并确认。模板保存目标、费率和成本默认值，不保存历史分析结果。</p>{templateError && <p role="alert" className="text-sm text-red-600">{templateError}</p>}</CardContent></Card>
      </div>
      <Card className="lg:sticky lg:top-20"><CardHeader><div className="flex items-center justify-between gap-3"><CardTitle>实时测算结果</CardTitle>{calculating && <span role="status" className="text-xs text-blue-600">计算中…</span>}</div></CardHeader><CardContent className="space-y-5">
        {validation && <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">{validation}</p>}
        {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {unreachable && <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">{unreachable}</p>}
        {preview ? <><p className="text-xs text-slate-500">{validation || error || unreachable || calculating ? "上一次有效结果" : "根据当前输入计算"}</p><div className="grid gap-4 sm:grid-cols-2"><div><p className="text-sm text-slate-500">{preview.mode === "target" ? "建议单件成交价" : "活动成交价"}</p><p className="text-2xl font-semibold">{amount(preview.price, preview.currency)}</p></div><div><p className="text-sm text-slate-500">单件利润</p><p className="text-2xl font-semibold">{amount(preview.result.unit_profit, preview.currency)}</p></div><div><p className="text-sm text-slate-500">预计总利润</p><p className="text-xl font-semibold">{amount(preview.result.estimated_total_profit, preview.currency)}</p></div><div><p className="text-sm text-slate-500">利润率</p><p className="text-xl font-semibold">{percent(preview.result.profit_margin)}</p></div></div><div className="grid gap-3 border-t pt-4 text-sm"><p>单件盈亏平衡价：{preview.result.break_even_price ? amount(preview.result.break_even_price, preview.currency) : "不可达"}</p><p>覆盖固定投入的销量：{preview.result.break_even_quantity ?? "无固定投入或单件贡献不足"}</p></div><p className="flex items-center gap-2 text-sm text-amber-700"><AlertTriangle className="size-4"/>预测结果依赖商家填写的成本、费率和销量假设。</p><div className="max-h-72 divide-y overflow-y-auto border-t">{preview.result.breakdown.map((item) => <div key={item.item} className="flex justify-between gap-3 py-2 text-sm"><span>{item.item}</span><span className="font-medium">{amount(item.amount, preview.currency)}</span></div>)}</div><p className="text-xs text-slate-500">费率来源：{preview.source || "未填写（仅预览）"}</p></> : !validation && <p className="text-sm text-slate-500">填写成本和费率后，结果会自动显示在这里。</p>}
      </CardContent></Card>
    </div>
  </div>;
}
