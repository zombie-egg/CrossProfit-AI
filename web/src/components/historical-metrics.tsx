"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { HistoricalRow } from "@/types";

const initial = { platform: "tiktok_shop", period: "", visitors: "", orders: "", returns: "", source: "" };

export function HistoricalMetrics() {
  const { locale } = useAuth();
  const zh = locale === "zh";
  const [rows, setRows] = useState<HistoricalRow[]>([]);
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const refresh = async () => setRows(await api.historicalMetrics());
  useEffect(() => { void refresh().catch((reason) => setError(reason instanceof Error ? reason.message : "Failed to load")); }, []);
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await api.addHistoricalMetric({ platform: form.platform, period: form.period,
        visitors: form.visitors === "" ? null : Number(form.visitors),
        orders: form.orders === "" ? null : Number(form.orders),
        returns: form.returns === "" ? null : Number(form.returns), source: form.source });
      setForm(initial); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Failed to save"); }
    finally { setBusy(false); }
  };
  return <Card><CardHeader><CardTitle>{zh ? "店铺历史指标" : "Shop history"}</CardTitle><CardDescription>{zh ? "按同一时段和口径录入店铺后台的访客、订单、退货数据，并注明来源。" : "Enter visitors, orders, and returns from the same reporting period and basis, with a source."}</CardDescription></CardHeader><CardContent>
    {error && <p role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <form onSubmit={(event) => void save(event)} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
      {[[zh ? "平台" : "Platform", "platform"], [zh ? "时段" : "Period", "period"], [zh ? "访客" : "Visitors", "visitors"], [zh ? "订单" : "Orders", "orders"], [zh ? "退货" : "Returns", "returns"], [zh ? "数据来源" : "Source", "source"]].map(([label, key]) => <label key={key} className="space-y-2 text-sm"><span>{label}</span><Input list={key === "platform" ? "historical-platforms" : undefined} type={["visitors", "orders", "returns"].includes(key) ? "number" : "text"} min={0} required={["platform", "period", "source"].includes(key)} value={form[key as keyof typeof form]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>)}
      <datalist id="historical-platforms"><option value="tiktok_shop" /><option value="amazon" /></datalist>
      <Button disabled={busy} className="lg:col-span-6">{busy ? (zh ? "保存中" : "Saving") : (zh ? "保存历史指标" : "Save historical metrics")}</Button>
    </form>
    <div className="mt-5 space-y-2">{rows.slice(0, 5).map((row) => <div key={row.id} className="rounded-lg border px-4 py-3 text-sm"><strong>{row.platform}</strong> · {row.period} · {zh ? "访客" : "visitors"} {row.visitors ?? "—"} · {zh ? "订单" : "orders"} {row.orders ?? "—"} · {zh ? "退货" : "returns"} {row.returns ?? "—"}<span className="ml-2 text-slate-500">{row.source}</span></div>)}</div>
  </CardContent></Card>;
}
