"use client";

import { ArrowRight, CircleDollarSign, CircleGauge, PackageCheck, ShieldAlert, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import { useData } from "@/components/data-provider";
import { ErrorState, PageSkeleton, RiskBadge } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AppleHelloChineseTitleEffect } from "@/components/ui/apple-hello-effect";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn, money, percent, platformName } from "@/lib/utils";
import type { HistoryItem } from "@/types";

export default function Dashboard() {
  const { data, history, loading, error, refresh } = useData();
  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState message={error ?? "数据为空"} retry={refresh} />;
  const demoResults: HistoryItem[] = data.cases.map((item) => ({ id: item.id, activity_id: item.id, product_id: item.product_id, activity_name: item.request.activity.activity_name, product_name: item.request.product.name, platform: item.request.activity.platform, unit_profit: item.result.unit_profit, profit_margin: item.result.profit_margin, estimated_total_profit: item.result.estimated_total_profit, risk_level: item.result.risk_level, created_at: "" }));
  const latestHistoryByActivity = new Map<number, HistoryItem>();
  history.forEach((item) => { if (!latestHistoryByActivity.has(item.activity_id)) latestHistoryByActivity.set(item.activity_id, item); });
  const resultByActivity = new Map<number, HistoryItem>(demoResults.map((item) => [item.activity_id, item]));
  latestHistoryByActivity.forEach((item, activityId) => resultByActivity.set(activityId, item));
  const results = Array.from(resultByActivity.values());
  const profitable = results.filter((x) => Number(x.unit_profit) > 0).length;
  const caution = results.filter((x) => ["CAUTION", "NOT_RECOMMENDED"].includes(x.risk_level)).length;
  const losses = results.filter((x) => x.risk_level === "LOSS").length;
  const total = results.reduce((sum, x) => sum + Number(x.estimated_total_profit), 0);
  const latestArchive = history[0] ?? null;
  const previewMargin = latestArchive ? Number(latestArchive.profit_margin) : 0;
  const previewBarWidth = latestArchive ? (previewMargin < 0 ? 100 : Math.min(100, Math.max(4, previewMargin / .2 * 100))) : 0;
  const previewBarColor = latestArchive?.risk_level === "LOSS" ? "bg-red-500" : ["CAUTION", "NOT_RECOMMENDED"].includes(latestArchive?.risk_level ?? "") ? "bg-amber-500" : "bg-emerald-500";
  const previewPressure = latestArchive?.cost_drivers?.map((item) => item.item).join("与") || "暂无显著成本项";
  const pie = [{ name: "健康", value: profitable - caution, color: "#16a34a" }, { name: "谨慎", value: caution, color: "#d97706" }, { name: "亏损", value: losses, color: "#dc2626" }].filter((x) => x.value > 0);
  const trend = [...results].reverse().map((x, i) => ({ name: `#${i + 1}`, profit: Number(x.estimated_total_profit) }));
  const costDrivers = data.cases.flatMap((x) => x.result.breakdown).filter((x) => Number(x.amount) > 0).reduce<Record<string, number>>((acc, item) => ({ ...acc, [item.item]: (acc[item.item] ?? 0) + Number(item.amount) }), {});
  return <div className="space-y-6">
    <section data-dashboard-hero className="relative overflow-hidden rounded-2xl bg-transparent px-6 py-9 text-black sm:px-10 sm:py-11 lg:grid lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-center lg:gap-12">
      <div className="hidden w-80 rounded-2xl bg-transparent p-5 outline outline-1 outline-slate-600/45 lg:col-start-2 lg:row-start-1 lg:block">
        <div className="flex items-center justify-between gap-3 text-xs text-slate-500"><div className="min-w-0"><span>最新归档活动</span><p className="mt-1 truncate font-medium text-slate-800">{latestArchive?.activity_name ?? "暂无归档记录"}</p></div>{latestArchive ? <RiskBadge level={latestArchive.risk_level}/> : <Badge variant="outline">等待归档</Badge>}</div>
        <div className="mt-6 grid grid-cols-2 gap-5"><div><p className="text-xs text-slate-500">单件利润</p><p className={cn("mt-1 text-2xl font-semibold tabular", latestArchive && Number(latestArchive.unit_profit) < 0 && "text-red-600")}>{latestArchive ? money(latestArchive.unit_profit) : "--"}</p></div><div><p className="text-xs text-slate-500">利润率</p><p className={cn("mt-1 text-2xl font-semibold tabular", previewMargin < 0 && "text-red-600")}>{latestArchive ? percent(latestArchive.profit_margin) : "--"}</p></div></div>
        <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-slate-200"><div className={cn("h-full transition-[width] duration-500",previewBarColor)} style={{width:`${previewBarWidth}%`}} /></div><p className="mt-3 text-xs text-slate-500">{latestArchive ? `主要压力：${previewPressure}` : "完成分析并归档后，这里会显示真实结果"}</p>
      </div>
      <div className="min-w-0 max-w-[920px] lg:col-start-1 lg:row-start-1">
        <AppleHelloChineseTitleEffect speed={0.82} />
        <p className="mt-0 max-w-xl text-xs leading-5 tracking-[0.035em] text-slate-500 sm:text-sm">自动拆解平台佣金、达人佣金、物流、退货与活动折扣，快速判断活动到底赚不赚钱。</p>
        <div className="mt-8 flex flex-wrap gap-3"><Button asChild size="lg"><Link href="/analysis">分析新活动<ArrowRight className="size-4" /></Link></Button><Button asChild size="lg" variant="outline"><Link href="/analysis?demo=1">加载演示案例</Link></Button></div>
      </div>
    </section>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{([
      ["活动总数", results.length, "按活动去重，取最新结果", CircleGauge], ["盈利活动", profitable, `${Math.round(profitable / Math.max(results.length, 1) * 100)}% 的活动单件利润为正`, PackageCheck], ["风险活动", caution + losses, "包含谨慎、不建议与亏损", ShieldAlert], ["预计总利润", money(total), "按各活动最新结果汇总", CircleDollarSign],
    ] as Array<[string, string | number, string, LucideIcon]>).map(([label, value, note, Icon]) => <Card key={label}><CardContent className="p-5"><div className="flex items-start justify-between"><div><p className="text-sm text-slate-500">{label}</p><p className="mt-3 text-2xl font-semibold tracking-tight tabular">{String(value)}</p><p className="mt-2 text-xs text-slate-500">{note}</p></div><div className="grid size-9 place-items-center rounded-lg bg-slate-100 text-slate-600"><Icon className="size-4" /></div></div></CardContent></Card>)}</section>
    <section className="grid gap-6 xl:grid-cols-3"><Card className="xl:col-span-2"><CardHeader><CardTitle>近期活动分析</CardTitle><CardDescription>统一口径下的活动真实利润</CardDescription></CardHeader><CardContent className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>平台</TableHead><TableHead>活动</TableHead><TableHead>商品</TableHead><TableHead>利润率</TableHead><TableHead>预计总利润</TableHead><TableHead>风险</TableHead></TableRow></TableHeader><TableBody>{results.slice(0, 6).map((row) => <TableRow key={`${row.id}-${row.activity_name}`}><TableCell><Badge variant="outline">{platformName(row.platform)}</Badge></TableCell><TableCell className="font-medium">{row.activity_name}</TableCell><TableCell className="text-slate-500">{row.product_name}</TableCell><TableCell className={cn("tabular", Number(row.profit_margin) < 0 ? "text-red-600" : "text-emerald-700")}>{percent(row.profit_margin)}</TableCell><TableCell className="tabular font-medium">{money(row.estimated_total_profit)}</TableCell><TableCell><RiskBadge level={row.risk_level} /></TableCell></TableRow>)}</TableBody></Table></CardContent></Card><Card><CardHeader><CardTitle>利润风险概览</CardTitle><CardDescription>当前活动风险分布</CardDescription></CardHeader><CardContent><div className="h-52"><ResponsiveContainer><PieChart><Pie data={pie} dataKey="value" nameKey="name" innerRadius={58} outerRadius={78} paddingAngle={3}>{pie.map((x) => <Cell key={x.name} fill={x.color} />)}</Pie><ChartTooltip /></PieChart></ResponsiveContainer></div><div className="flex justify-center gap-5">{pie.map((x) => <div key={x.name} className="flex items-center gap-2 text-xs text-slate-600"><span className="size-2 rounded-full" style={{ background: x.color }} />{x.name} {x.value}</div>)}</div></CardContent></Card></section>
    <section className="grid gap-6 xl:grid-cols-3"><Card className="xl:col-span-2"><CardHeader><CardTitle>预计利润趋势</CardTitle><CardDescription>按最近分析顺序观察活动回报</CardDescription></CardHeader><CardContent className="h-64"><ResponsiveContainer><AreaChart data={trend}><defs><linearGradient id="profit" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2563eb" stopOpacity={.2}/><stop offset="100%" stopColor="#2563eb" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0"/><XAxis dataKey="name" axisLine={false} tickLine={false}/><YAxis axisLine={false} tickLine={false}/><ChartTooltip formatter={(v) => money(Number(v))}/><Area type="monotone" dataKey="profit" stroke="#2563eb" strokeWidth={2} fill="url(#profit)"/></AreaChart></ResponsiveContainer></CardContent></Card><Card><CardHeader><CardTitle>最大成本来源</CardTitle><CardDescription>跨演示活动累计</CardDescription></CardHeader><CardContent className="space-y-4">{Object.entries(costDrivers).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([name,value],i)=><div key={name}><div className="flex justify-between text-sm"><span className="text-slate-600">{name}</span><span className="font-medium tabular">{money(value)}</span></div><div className="mt-2 h-1.5 rounded-full bg-slate-100"><div className="h-full rounded-full bg-slate-700" style={{width:`${Math.max(12,100-i*17)}%`}}/></div></div>)}</CardContent></Card></section>
  </div>;
}
