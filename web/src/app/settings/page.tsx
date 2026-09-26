"use client";

import { useEffect, useState } from "react";
import { KeyRound, Languages, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  const { account, locale, setLocale } = useAuth(); const zh = locale === "zh";
  const [configured, setConfigured] = useState(false); const [key, setKey] = useState(""); const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  useEffect(() => { void api.aiKeyStatus().then((value) => setConfigured(value.configured)).catch(() => undefined); }, []);
  const save = async (clear = false) => { setBusy(true); setMessage(""); try { const result = await api.saveAiKey(clear ? null : key); setConfigured(result.configured); setKey(""); setMessage(zh ? "设置已保存" : "Settings saved"); } catch (error) { setMessage(error instanceof Error ? error.message : "Failed to save"); } finally { setBusy(false); } };
  return <div className="grid gap-6 xl:grid-cols-2">
    <Card><CardHeader><CardTitle className="flex items-center gap-2"><KeyRound className="size-5" />{zh ? "我的 DeepSeek API Key" : "My DeepSeek API key"}</CardTitle><CardDescription>{zh ? "每个商家可以使用自己的模型账户。密钥加密存储，只在服务端调用，不会回显。" : "Each merchant can use their own model account. Keys are encrypted at rest and never displayed again."}</CardDescription></CardHeader><CardContent className="space-y-4"><p className="flex items-center gap-2 text-sm"><ShieldCheck className="size-4 text-emerald-600" />{configured ? (zh ? "已配置个人密钥" : "Personal key configured") : (zh ? "尚未配置个人密钥" : "No personal key configured")}</p><Input type="password" autoComplete="off" placeholder="sk-…" value={key} onChange={(event) => setKey(event.target.value)} /><div className="flex flex-wrap gap-2"><Button disabled={busy || !key.trim()} onClick={() => void save()}>{zh ? "保存密钥" : "Save key"}</Button>{configured && <Button variant="outline" disabled={busy} onClick={() => void save(true)}>{zh ? "删除个人密钥" : "Remove key"}</Button>}</div>{message && <p role="status" className="text-sm text-slate-600">{message}</p>}<p className="text-xs leading-5 text-slate-500">{zh ? "DeepSeek 只补充定性建议；利润数字始终由确定性引擎计算。" : "DeepSeek only supplements qualitative advice. Deterministic calculations produce all profit figures."}</p></CardContent></Card>
    <Card><CardHeader><CardTitle className="flex items-center gap-2"><Languages className="size-5" />{zh ? "语言与账户" : "Language and account"}</CardTitle><CardDescription>{account?.email}</CardDescription></CardHeader><CardContent><div className="flex gap-2"><Button variant={zh ? "default" : "outline"} onClick={() => void setLocale("zh")}>中文</Button><Button variant={!zh ? "default" : "outline"} onClick={() => void setLocale("en")}>English</Button></div><p className="mt-4 text-xs text-slate-500">{zh ? "平台政策、费率和历史指标必须注明来源、时间段与数据权限；公开市场资料不能代表你的店铺实际结果。" : "Platform rules, fees and historical metrics need source, period and access context. Public market information does not represent your shop's actual results."}</p></CardContent></Card>
  </div>;
}
