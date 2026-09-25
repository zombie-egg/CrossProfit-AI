"use client";

import { useEffect, useState } from "react";
import { Component as InfiniteGrid } from "@/components/ui/the-infinite-grid";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";

type Mode = "login" | "register" | "code" | "reset";

export function AuthPage() {
  const { locale, setAccount, setLocale } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!cooldown) return;
    const timer = window.setTimeout(() => setCooldown(cooldown - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);
  const zh = locale === "zh";
  const copy = {
    brand: zh ? "CrossProfit AI" : "CrossProfit AI",
    headline: zh ? "你的多平台盈利工作台" : "Your profit workspace",
    subtitle: zh ? "聚合店铺数据、平台规则与市场信号。" : "Shop data · Platform rules · Market signals",
    title: zh ? ({ login: "登录", register: "注册新账户", code: "验证码登录", reset: "找回密码" }[mode]) : ({ login: "Sign in", register: "Create account", code: "One-time code", reset: "Reset password" }[mode]),
  };
  const changeMode = (value: Mode) => { setMode(value); setMessage(""); setCode(""); };
  const sendCode = async () => {
    if (!email.trim()) { setMessage(zh ? "请先填写邮箱" : "Enter your email first"); return; }
    setSending(true); setMessage("");
    try { await api.sendCode(email.trim(), mode === "register" ? "register" : mode === "reset" ? "reset" : "login"); setCooldown(60); setMessage(zh ? "如邮箱可用，验证码已发送；10 分钟内有效。" : "If eligible, a code was sent. It expires in 10 minutes."); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Unable to send code"); }
    finally { setSending(false); }
  };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      const account = mode === "login" ? await api.login(email.trim(), password)
        : mode === "register" ? await api.register(email.trim(), code.trim(), password)
        : mode === "code" ? await api.codeLogin(email.trim(), code.trim())
        : await api.resetPassword(email.trim(), code.trim(), password);
      setAccount(account);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Authentication failed"); }
    finally { setBusy(false); }
  };
  return <div className="relative min-h-screen overflow-hidden bg-white text-[#292823]">
    <InfiniteGrid className="z-0 opacity-50" />
    <button type="button" onClick={() => void setLocale(zh ? "en" : "zh")} className="absolute right-7 top-6 z-20 whitespace-nowrap rounded-full border border-stone-200 bg-white/80 px-4 py-2 text-sm font-medium shadow-sm">{zh ? "English" : "中文"}</button>
    <div className="relative z-10 mx-auto grid min-h-screen max-w-[1600px] grid-cols-1 items-center gap-10 px-6 py-24 sm:px-10 xl:grid-cols-[minmax(0,1fr)_540px] xl:gap-16 xl:px-16">
      <section className="min-w-0 whitespace-nowrap xl:pt-16"><p className="mb-5 text-lg font-semibold text-stone-500 xl:text-xl">{copy.brand}</p><h1 className="text-[clamp(21px,3.2vw,58px)] font-bold leading-tight tracking-tight">{copy.headline}</h1><p className="mt-6 text-[clamp(13px,1.35vw,21px)] text-stone-500">{copy.subtitle}</p></section>
      <section className="mx-auto flex h-[680px] w-full max-w-[540px] flex-col rounded-[15px] border border-[#dedbd4] bg-white/95 px-6 py-8 shadow-[0_2px_5px_rgba(50,45,35,0.11)] sm:px-9">
        <h2 className="whitespace-nowrap text-[34px] font-bold leading-tight">{copy.title}</h2>
        <div className="mt-2 flex items-center gap-x-3 whitespace-nowrap text-base text-stone-500">
          <span>{zh ? "第一次使用？" : "New here?"}</span><button type="button" onClick={() => changeMode(mode === "register" ? "login" : "register")} className="font-semibold text-stone-800 underline underline-offset-8">{mode === "register" ? (zh ? "返回登录" : "Sign in") : (zh ? "注册新账户" : "Create account")}</button>
        </div>
        <form onSubmit={(event) => void submit(event)} className="mt-8 flex min-h-0 flex-1 flex-col gap-4">
          <label className="block whitespace-nowrap text-base font-semibold"><span>{zh ? "邮箱" : "Email"}</span><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 h-14 w-full rounded-[10px] border border-[#d8d8d6] bg-[#eff4ff] px-4 text-base font-normal outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder={zh ? "请输入你的邮箱" : "Enter your email"} /></label>
          {(mode === "register" || mode === "code" || mode === "reset") && <label className="block whitespace-nowrap text-base font-semibold"><span>{zh ? "邮箱验证码" : "Email code"}</span><div className="mt-2 flex gap-2"><input inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} className="h-14 min-w-0 flex-1 rounded-[10px] border border-[#d8d8d6] bg-[#eff4ff] px-4 text-base font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder={zh ? "6 位验证码" : "6-digit code"} /><button type="button" onClick={() => void sendCode()} disabled={sending || cooldown > 0} className="shrink-0 whitespace-nowrap rounded-[10px] border border-stone-300 px-3 text-sm font-semibold disabled:text-stone-400">{cooldown ? `${cooldown}s` : sending ? (zh ? "发送中" : "Sending") : (zh ? "发送验证码" : "Send code")}</button></div></label>}
          {mode !== "code" && <label className="block whitespace-nowrap text-base font-semibold"><span>{mode === "reset" ? (zh ? "新密码" : "New password") : (zh ? "密码" : "Password")}</span><input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "login" ? undefined : 8} required value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 h-14 w-full rounded-[10px] border border-[#d8d8d6] bg-[#eff4ff] px-4 text-base font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder={mode === "login" ? "••••••••" : (zh ? "至少 8 位" : "At least 8 characters")} /></label>}
          {message && <p role="status" title={message} className="overflow-hidden text-ellipsis whitespace-nowrap rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{message}</p>}
          <button type="submit" disabled={busy} className="mt-auto h-14 w-full shrink-0 whitespace-nowrap rounded-[10px] bg-[#292823] text-lg font-semibold text-white transition hover:bg-stone-700 disabled:opacity-60">{busy ? (zh ? "请稍候…" : "Please wait…") : copy.title}</button>
        </form>
        <div className="mt-5 flex items-center justify-between gap-2 whitespace-nowrap text-[clamp(11px,2.7vw,14px)] text-stone-600"><button type="button" onClick={() => changeMode(mode === "code" ? "login" : "code")} className="underline underline-offset-4">{mode === "code" ? (zh ? "密码登录" : "Password sign in") : (zh ? "一次性验证码登录" : "Sign in with a code")}</button><button type="button" onClick={() => changeMode(mode === "reset" ? "login" : "reset")} className="underline underline-offset-4">{mode === "reset" ? (zh ? "返回登录" : "Back to sign in") : (zh ? "忘记密码？" : "Forgot password?")}</button></div>
      </section>
    </div>
  </div>;
}
