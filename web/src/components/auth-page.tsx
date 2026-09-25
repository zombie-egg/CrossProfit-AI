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
    subtitle: zh ? "将店铺数据、平台政策与市场信号放在一起，做有依据的活动决策。" : "Bring shop data, platform rules and market signals together for informed decisions.",
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
    <button type="button" onClick={() => void setLocale(zh ? "en" : "zh")} className="absolute right-7 top-6 z-20 rounded-full border border-stone-200 bg-white/80 px-4 py-2 text-sm font-medium shadow-sm">{zh ? "English" : "中文"}</button>
    <div className="relative z-10 mx-auto grid min-h-screen max-w-[2250px] grid-cols-1 items-center gap-16 px-[clamp(28px,4.5vw,104px)] py-20 lg:grid-cols-[1.08fr_0.92fr]">
      <section className="max-w-[900px] lg:pt-28"><p className="mb-8 text-[clamp(18px,1.3vw,28px)] font-semibold text-stone-500">{copy.brand}</p><h1 className="text-[clamp(44px,3.8vw,78px)] font-bold leading-[1.17] tracking-tight">{copy.headline}</h1><p className="mt-9 max-w-[860px] text-[clamp(19px,1.65vw,34px)] leading-relaxed text-stone-500">{copy.subtitle}</p></section>
      <section className="mx-auto w-full max-w-[755px] rounded-[15px] border border-[#dedbd4] bg-white/95 px-[clamp(26px,2.3vw,48px)] py-[clamp(32px,2.2vw,46px)] shadow-[0_2px_5px_rgba(50,45,35,0.11)]">
        <h2 className="text-[clamp(30px,2.1vw,44px)] font-bold leading-tight">{copy.title}</h2>
        <div className="mt-2 flex flex-wrap gap-x-3 text-[clamp(15px,1.2vw,24px)] text-stone-500">
          <span>{zh ? "第一次使用？" : "New here?"}</span><button type="button" onClick={() => changeMode(mode === "register" ? "login" : "register")} className="font-semibold text-stone-800 underline underline-offset-8">{mode === "register" ? (zh ? "返回登录" : "Sign in") : (zh ? "注册新账户" : "Create account")}</button>
        </div>
        <form onSubmit={(event) => void submit(event)} className="mt-12 space-y-8">
          <label className="block text-[clamp(17px,1.2vw,25px)] font-semibold"><span>{zh ? "邮箱" : "Email"}</span><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="mt-4 h-[74px] w-full rounded-[12px] border border-[#d8d8d6] bg-[#eff4ff] px-6 text-[clamp(17px,1.3vw,27px)] font-normal outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder={zh ? "请输入你的邮箱" : "Enter your email"} /></label>
          {(mode === "register" || mode === "code" || mode === "reset") && <label className="block text-[clamp(17px,1.2vw,25px)] font-semibold"><span>{zh ? "邮箱验证码" : "Email code"}</span><div className="mt-4 flex gap-3"><input inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} className="h-[74px] min-w-0 flex-1 rounded-[12px] border border-[#d8d8d6] bg-[#eff4ff] px-6 text-[clamp(17px,1.3vw,27px)] font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder="6-digit code" /><button type="button" onClick={() => void sendCode()} disabled={sending || cooldown > 0} className="rounded-[12px] border border-stone-300 px-4 text-sm font-semibold disabled:text-stone-400">{cooldown ? `${cooldown}s` : sending ? (zh ? "发送中" : "Sending") : (zh ? "发送验证码" : "Send code")}</button></div></label>}
          {mode !== "code" && <label className="block text-[clamp(17px,1.2vw,25px)] font-semibold"><span>{mode === "reset" ? (zh ? "新密码" : "New password") : (zh ? "密码" : "Password")}</span><input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "login" ? undefined : 8} required value={password} onChange={(event) => setPassword(event.target.value)} className="mt-4 h-[74px] w-full rounded-[12px] border border-[#d8d8d6] bg-[#eff4ff] px-6 text-[clamp(17px,1.3vw,27px)] font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder={mode === "login" ? "••••••••" : (zh ? "至少 8 位" : "At least 8 characters")} /></label>}
          {message && <p role="status" className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">{message}</p>}
          <button type="submit" disabled={busy} className="h-[74px] w-full rounded-[11px] bg-[#292823] text-[clamp(18px,1.2vw,25px)] font-semibold text-white transition hover:bg-stone-700 disabled:opacity-60">{busy ? (zh ? "请稍候…" : "Please wait…") : copy.title}</button>
        </form>
        <div className="mt-6 flex flex-wrap justify-between gap-3 text-sm text-stone-600"><button type="button" onClick={() => changeMode(mode === "code" ? "login" : "code")} className="underline underline-offset-4">{mode === "code" ? (zh ? "密码登录" : "Password sign in") : (zh ? "一次性验证码登录" : "Sign in with a code")}</button><button type="button" onClick={() => changeMode(mode === "reset" ? "login" : "reset")} className="underline underline-offset-4">{mode === "reset" ? (zh ? "返回登录" : "Back to sign in") : (zh ? "忘记密码？" : "Forgot password?")}</button></div>
      </section>
    </div>
  </div>;
}
