"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Download } from "lucide-react";
import { api } from "@/lib/api";
import type { AnalysisRun } from "@/types";
import { PageSkeleton, RiskBadge } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table,TableBody,TableCell,TableHead,TableHeader,TableRow } from "@/components/ui/table";
import { money,percent } from "@/lib/utils";
export default function HistoryDetail({params}:{params:{id:string}}){const {id}=params;const [data,setData]=useState<{result:AnalysisRun["result"];scenarios:AnalysisRun["scenarios"]}|null>(null);useEffect(()=>{void api.analysis(Number(id)).then(setData)},[id]);if(!data)return <PageSkeleton/>;return <div className="space-y-6"><div className="flex justify-between"><Button asChild variant="ghost"><Link href="/history"><ArrowLeft className="size-4"/>返回历史</Link></Button><Button asChild variant="outline"><a href={api.exportUrl(Number(id),"xlsx")}><Download className="size-4"/>导出 Excel</a></Button></div><Card><CardContent className="grid gap-6 p-6 sm:grid-cols-4"><div><RiskBadge level={data.result.risk_level} label={data.result.risk_label}/></div><div><p className="text-xs text-slate-500">单件利润</p><p className="mt-2 text-2xl font-semibold">{money(data.result.unit_profit)}</p></div><div><p className="text-xs text-slate-500">利润率</p><p className="mt-2 text-2xl font-semibold">{percent(data.result.profit_margin)}</p></div><div><p className="text-xs text-slate-500">预计总利润</p><p className="mt-2 text-2xl font-semibold">{money(data.result.estimated_total_profit)}</p></div></CardContent></Card><Card><CardHeader><CardTitle>详细计算过程</CardTitle></CardHeader><CardContent><Table><TableHeader><TableRow><TableHead>项目</TableHead><TableHead>公式</TableHead><TableHead>金额</TableHead></TableRow></TableHeader><TableBody>{data.result.breakdown.map(x=><TableRow key={x.item}><TableCell>{x.item}</TableCell><TableCell className="text-slate-500">{x.formula}</TableCell><TableCell>{money(x.amount)}</TableCell></TableRow>)}</TableBody></Table></CardContent></Card></div>}
