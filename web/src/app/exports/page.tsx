"use client";
import { Download, FileSpreadsheet, FileText } from "lucide-react";
import { useData } from "@/components/data-provider";
import { EmptyState, ErrorState, PageSkeleton, RiskBadge } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card,CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { money,platformName } from "@/lib/utils";
export default function ExportsPage(){const {history,loading,error,refresh}=useData();if(loading)return <PageSkeleton/>;if(error)return <ErrorState message={error} retry={refresh}/>;if(!history.length)return <EmptyState title="暂无可导出报告" description="完成一次活动分析后，可以在这里下载 CSV 或 Excel 报告。"/>;return <div className="grid gap-4 lg:grid-cols-2">{history.map(x=><Card key={x.id}><CardContent className="p-5"><div className="flex items-start justify-between gap-4"><div><p className="font-medium">{x.activity_name}</p><p className="mt-1 text-xs text-slate-500">{x.product_name} · {platformName(x.platform)}</p></div><RiskBadge level={x.risk_level}/></div><div className="mt-5 flex items-center justify-between border-t pt-4"><div><p className="text-xs text-slate-500">预计总利润</p><p className="mt-1 font-semibold">{money(x.estimated_total_profit)}</p></div><div className="flex gap-2"><Button asChild size="sm" variant="outline"><a href={api.exportUrl(x.id,"csv")}><FileText className="size-4"/>CSV</a></Button><Button asChild size="sm"><a href={api.exportUrl(x.id,"xlsx")}><FileSpreadsheet className="size-4"/>Excel</a></Button></div></div></CardContent></Card>)}</div>}

