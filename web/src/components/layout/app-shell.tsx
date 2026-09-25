"use client";

import { motion } from "framer-motion";
import { BarChart3, Calculator, Download, History, LayoutDashboard, Menu, Package, Settings, TrendingUp, PlugZap, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useData } from "@/components/data-provider";
import { useAuth } from "@/components/auth-provider";
import { LocaleDom } from "@/components/locale-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Component as InfiniteGrid } from "@/components/ui/the-infinite-grid";
import { cn, money, platformName } from "@/lib/utils";

const primary = [
  ["/", "Dashboard", LayoutDashboard], ["/quick", "单品测算", Calculator], ["/analysis", "活动分析", Calculator], ["/comparison", "活动对比", BarChart3],
  ["/products", "商品管理", Package], ["/connections", "平台连接", PlugZap], ["/history", "历史记录", History],
] as const;
const secondary = [["/exports", "导出中心", Download], ["/settings", "设置", Settings]] as const;
const pageCopy: Record<string, [string, string]> = {
  "/": ["Dashboard", "跨平台活动盈利概览"],
  "/quick": ["单品测算", "手动填入实际成本和费率，先算清单件利润"],
  "/analysis": ["活动分析", "计算活动真实利润，并识别隐藏成本风险"],
  "/comparison": ["活动对比", "用统一口径判断哪个活动更值得参加"],
  "/products": ["商品管理", "集中管理商品成本和不同平台费用结构"],
  "/connections": ["平台连接", "一个账号管理多个平台与店铺"],
  "/history": ["历史记录", "回看每一次活动决策与计算结果"],
  "/exports": ["导出中心", "下载可交付的盈利分析报告"],
  "/settings": ["设置", "管理分析模式、利润阈值与显示偏好"],
};

function Brand({ expanded = true }: { expanded?: boolean }) {
  return <div className="flex h-16 items-center gap-3 px-4"><div className="grid size-9 shrink-0 place-items-center rounded-lg bg-slate-950 text-white"><TrendingUp className="size-4" /></div>{expanded && <div className="min-w-0"><div className="truncate text-sm font-semibold tracking-tight">CrossProfit AI</div><div className="truncate text-[11px] text-slate-500">跨境活动盈利助手</div></div>}</div>;
}

function NavList({ expanded, close }: { expanded: boolean; close?: () => void }) {
  const pathname = usePathname();
  const { locale } = useAuth();
  const english: Record<string, string> = { "Dashboard": "Dashboard", "单品测算": "Single product", "活动分析": "Promotion analysis", "活动对比": "Compare", "商品管理": "Products", "平台连接": "Connections", "历史记录": "History", "导出中心": "Exports", "设置": "Settings" };
  const render = (item: (typeof primary)[number] | (typeof secondary)[number]) => {
    const [href, originalLabel, Icon] = item; const label = locale === "en" ? english[originalLabel] ?? originalLabel : originalLabel; const active = pathname === href;
    const link = <Link href={href} onClick={close} className={cn("flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-950", active && "bg-slate-100 text-slate-950")}><Icon className="size-[18px] shrink-0" />{expanded && <span>{label}</span>}</Link>;
    return expanded ? <div key={href}>{link}</div> : <Tooltip key={href}><TooltipTrigger asChild>{link}</TooltipTrigger><TooltipContent side="right">{label}</TooltipContent></Tooltip>;
  };
  return <nav className="flex flex-1 flex-col px-3"><div className="space-y-1">{primary.map(render)}</div><div className="my-4 border-t" /><div className="space-y-1">{secondary.map(render)}</div></nav>;
}

function DesktopSidebar() {
  const [hovered, setHovered] = useState(false);
  return <motion.aside animate={{ width: hovered ? 252 : 72 }} transition={{ duration: .2, ease: "easeOut" }} onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} className="fixed inset-y-0 left-0 z-40 hidden overflow-hidden bg-white/75 shadow-[12px_0_40px_-32px_rgba(15,23,42,0.45)] backdrop-blur-xl lg:flex lg:flex-col"><Brand expanded={hovered} /><NavList expanded={hovered} /><div className="p-3"><div className="flex items-center gap-3 rounded-lg bg-white/55 p-3"><span className="size-2 shrink-0 rounded-full bg-emerald-500" />{hovered && <div><div className="text-xs font-medium">System Ready</div><div className="text-[11px] text-slate-500">Demo · 利润引擎</div></div>}</div></div></motion.aside>;
}

function DemoDialog() {
  const { data } = useData();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const labels = ["TikTok 高流量低利润", "Amazon 稳健盈利", "TikTok 高销量亏损"];
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm" variant="outline">加载演示案例</Button></DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader><DialogTitle>选择一个比赛演示案例</DialogTitle><DialogDescription>载入真实 Demo 商品与活动参数，计算结果仍由后端盈利引擎生成。</DialogDescription></DialogHeader>
        <div className="space-y-3">{data?.cases.map((item, index) => <button key={item.id} onClick={() => { setOpen(false); router.push(`/analysis?demo=${item.id}`); }} className="flex w-full items-center justify-between rounded-xl border bg-white p-4 text-left hover:border-slate-300 hover:bg-slate-50"><div><div className="font-medium">{labels[index] ?? item.request.activity.activity_name}</div><div className="mt-1 text-xs text-slate-500">{platformName(item.request.activity.platform)} · {item.request.activity.activity_name}</div></div><div className={cn("tabular text-sm font-semibold", Number(item.result.unit_profit) < 0 ? "text-red-600" : "text-emerald-600")}>{money(item.result.unit_profit)} / 单</div></button>)}</div>
      </DialogContent>
    </Dialog>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const [title, subtitle] = pageCopy[pathname] ?? pageCopy["/"];
  const { account, locale, setLocale, logout } = useAuth();
  const titleEn: Record<string, string> = { "/": "Dashboard", "/quick": "Single product", "/analysis": "Promotion analysis", "/comparison": "Compare activities", "/products": "Products", "/connections": "Connections", "/history": "History", "/exports": "Exports", "/settings": "Settings" };
  return <div className="relative min-h-screen"><LocaleDom/><InfiniteGrid className="z-0"/><DesktopSidebar /><header className="sticky top-0 z-30 flex h-16 items-center bg-white/65 px-4 shadow-[0_12px_36px_-32px_rgba(15,23,42,0.5)] backdrop-blur-xl lg:ml-[72px] lg:px-8"><Sheet><SheetTrigger asChild><Button variant="ghost" size="icon" className="mr-2 lg:hidden"><Menu className="size-5" /></Button></SheetTrigger><SheetContent side="left" className="w-[280px] border-0 bg-white/90 p-0 backdrop-blur-xl"><SheetTitle className="sr-only">Navigation</SheetTitle><Brand /><NavList expanded /></SheetContent></Sheet><div className="min-w-0 flex-1"><h1 className="truncate text-sm font-semibold text-slate-950">{locale === "en" ? titleEn[pathname] ?? title : title}</h1><p className="hidden truncate text-xs text-slate-500 sm:block">{locale === "en" ? "Merchant workspace" : subtitle}</p></div><div className="flex items-center gap-2"><span className="hidden max-w-40 truncate text-xs text-slate-500 md:inline">{account?.email}</span><Button size="sm" variant="outline" onClick={() => void setLocale(locale === "zh" ? "en" : "zh")}>{locale === "zh" ? "EN" : "中文"}</Button><Button size="sm" variant="ghost" onClick={() => void logout()} title={locale === "zh" ? "退出登录" : "Sign out"}><LogOut className="size-4"/></Button></div></header><main className="relative z-10 lg:ml-[72px]"><motion.div key={pathname} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .2 }} className="mx-auto max-w-[1560px] p-4 sm:p-6 lg:p-8">{children}</motion.div></main></div>;
}
