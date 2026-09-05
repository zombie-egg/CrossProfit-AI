"use client";

import { AlertCircle, Inbox } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, riskStyles } from "@/lib/utils";

export function RiskBadge({ level, label }: { level: string; label?: string }) {
  const names: Record<string, string> = { HIGHLY_RECOMMENDED: "强烈推荐", RECOMMENDED: "可以参加", CAUTION: "谨慎参加", NOT_RECOMMENDED: "不建议参加", LOSS: "明确亏损" };
  return <Badge variant="outline" className={cn("font-medium", riskStyles[level])}>{label ?? names[level] ?? level}</Badge>;
}

export function PageSkeleton() {
  return <div className="space-y-6"><Skeleton className="h-44 w-full rounded-xl" /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}</div><Skeleton className="h-80 rounded-xl" /></div>;
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return <Alert variant="destructive" className="bg-white"><AlertCircle className="size-4" /><AlertTitle>无法读取数据</AlertTitle><AlertDescription className="mt-1 flex items-center justify-between gap-4"><span>{message}。请确认 FastAPI 已在 8000 端口启动。</span>{retry && <Button size="sm" variant="outline" onClick={retry}>重新连接</Button>}</AlertDescription></Alert>;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return <Card><CardContent className="flex min-h-64 flex-col items-center justify-center text-center"><div className="mb-4 grid size-11 place-items-center rounded-xl bg-slate-100 text-slate-500"><Inbox className="size-5" /></div><h3 className="font-semibold">{title}</h3><p className="mt-1 max-w-md text-sm text-slate-500">{description}</p>{action && <div className="mt-5">{action}</div>}</CardContent></Card>;
}

