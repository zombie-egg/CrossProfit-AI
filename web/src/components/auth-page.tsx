"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import Image from "next/image";
import { Component as InfiniteGrid } from "@/components/ui/the-infinite-grid";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";

type Mode = "login" | "register" | "code" | "reset";
type Captcha = { token: string; image: string };

const inputClass = "mt-2 block h-[clamp(42px,6svh,56px)] w-full rounded-[10px] border border-[#d8d8d6] bg-[#eff4ff] px-4 text-base font-normal outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";
const labelClass = "block min-w-0 whitespace-nowrap text-[clamp(13px,1.3vw,16px)] font-semibold";

export function AuthPage() {
  const { locale, setAccount, setLocale } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [captcha, setCaptcha] = useState<Captcha | null>(null);
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [message, setMessage] = useState("");
  const zh = locale === "zh";

  const refreshCaptcha = useCallback(async () => {
    setCaptcha(null);
    setCaptchaAnswer("");
    try {
      setCaptcha(await api.captcha());
    } catch {
      setMessage(locale === "zh" ? "图片验证码加载失败，请重试" : "Captcha could not load. Please retry.");
    }
  }, [locale]);

  useEffect(() => {
    if (mode === "login" || mode === "code") void refreshCaptcha();
  }, [mode, refreshCaptcha]);

  useEffect(() => {
    if (!cooldown) return;
    const timer = window.setTimeout(() => setCooldown(cooldown - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  const title = zh
    ? ({ login: "登录", register: "注册新账户", code: "验证码登录", reset: "找回密码" }[mode])
    : ({ login: "Sign in", register: "Create account", code: "One-time code", reset: "Reset password" }[mode]);

  const changeMode = (next: Mode) => {
    setMode(next);
    setMessage("");
    setCode("");
    setCaptchaAnswer("");
  };

  const sendCode = async () => {
    if (!email.trim()) {
      setMessage(zh ? "请先填写邮箱" : "Enter your email first");
      return;
    }
    setSending(true);
    setMessage("");
    try {
      await api.sendCode(email.trim(), mode === "register" ? "register" : mode === "reset" ? "reset" : "login");
      setCooldown(60);
      setMessage(zh ? "验证码已发送，有效期 10 分钟" : "Code sent. Valid for 10 minutes.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to send code");
    } finally {
      setSending(false);
    }
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      let account;
      if (mode === "login" || mode === "code") {
        if (!captcha) throw new Error(zh ? "请先刷新图片验证码" : "Refresh the image code first");
        account = mode === "login"
          ? await api.login(email.trim(), password, captcha.token, captchaAnswer.trim())
          : await api.codeLogin(email.trim(), code.trim(), captcha.token, captchaAnswer.trim());
      } else {
        account = mode === "register"
          ? await api.register(email.trim(), code.trim(), password)
          : await api.resetPassword(email.trim(), code.trim(), password);
      }
      setAccount(account);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Authentication failed");
      if (mode === "login" || mode === "code") void refreshCaptcha();
    } finally {
      setBusy(false);
    }
  };

  return <div className="relative h-svh min-h-[360px] overflow-hidden bg-white text-[#292823]">
    <InfiniteGrid className="z-0 opacity-50" />
    <button type="button" onClick={() => void setLocale(zh ? "en" : "zh")} className="absolute right-5 top-4 z-20 whitespace-nowrap rounded-full border border-stone-200 bg-white/80 px-4 py-2 text-sm font-medium shadow-sm sm:right-8 sm:top-6">{zh ? "English" : "中文"}</button>
    <div className="relative z-10 mx-auto grid h-full max-w-[2250px] grid-cols-1 items-center gap-6 px-5 pt-16 pb-4 sm:px-8 md:grid-cols-[minmax(0,1fr)_minmax(340px,44%)] md:gap-8 md:px-[4.5vw] md:py-12 xl:grid-cols-[minmax(0,1fr)_minmax(440px,32%)]">
      <section className="hidden min-w-0 whitespace-nowrap md:block md:pt-16">
        <p className="mb-7 text-[clamp(17px,1.3vw,28px)] font-semibold text-stone-500">CrossProfit AI</p>
        <h1 className="text-[clamp(27px,3.3vw,70px)] font-bold leading-tight tracking-tight">{zh ? "你的多平台盈利工作台" : "Your profit workspace"}</h1>
        <p className="mt-8 text-[clamp(15px,1.35vw,27px)] text-stone-500">{zh ? "店铺数据 · 平台规则 · 市场信号" : "Shop data · Platform rules · Market signals"}</p>
      </section>
      <section className="mx-auto flex h-[min(640px,calc(100svh-88px))] w-full max-w-[540px] min-w-0 flex-col overflow-y-auto rounded-[15px] border border-[#dedbd4] bg-white/95 px-[clamp(18px,2.3vw,38px)] py-[clamp(20px,3svh,34px)] shadow-[0_2px_5px_rgba(50,45,35,0.11)] md:h-[min(640px,calc(100svh-96px))]">
        <h2 className="shrink-0 whitespace-nowrap text-[clamp(25px,2.2vw,38px)] font-bold leading-tight">{title}</h2>
        <div className="mt-2 flex shrink-0 items-center gap-3 whitespace-nowrap text-[clamp(13px,1.2vw,18px)] text-stone-500">
          <span>{zh ? "第一次使用？" : "New here?"}</span>
          <button type="button" onClick={() => changeMode(mode === "register" ? "login" : "register")} className="font-semibold text-stone-800 underline underline-offset-8">{mode === "register" ? (zh ? "返回登录" : "Sign in") : (zh ? "注册新账户" : "Create account")}</button>
        </div>
        <form onSubmit={(event) => void submit(event)} className="mt-[clamp(16px,3svh,32px)] flex min-h-0 flex-1 flex-col gap-[clamp(8px,1.7svh,18px)]">
          <label className={labelClass}><span>{zh ? "邮箱" : "Email"}</span><input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className={inputClass} placeholder={zh ? "请输入你的邮箱" : "Enter your email"} /></label>
          {(mode === "register" || mode === "code" || mode === "reset") && <label className={labelClass}><span>{zh ? "邮箱验证码" : "Email code"}</span><div className="mt-2 flex min-w-0 gap-2"><input inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} className="h-[clamp(42px,6svh,56px)] min-w-0 flex-1 rounded-[10px] border border-[#d8d8d6] bg-[#eff4ff] px-3 text-base font-normal outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder={zh ? "6 位数字" : "6 digits"} /><button type="button" onClick={() => void sendCode()} disabled={sending || cooldown > 0} className="shrink-0 whitespace-nowrap rounded-[10px] border border-stone-300 px-2 text-[clamp(11px,1vw,14px)] font-semibold disabled:text-stone-400">{cooldown ? `${cooldown}s` : sending ? (zh ? "发送中" : "Sending") : (zh ? "发送验证码" : "Send code")}</button></div></label>}
          {mode !== "code" && <label className={labelClass}><span>{mode === "reset" ? (zh ? "新密码" : "New password") : (zh ? "密码" : "Password")}</span><input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "login" ? undefined : 8} required value={password} onChange={(event) => setPassword(event.target.value)} className={inputClass} placeholder={mode === "login" ? "••••••••" : (zh ? "至少 8 位" : "At least 8 characters")} /></label>}
          {(mode === "login" || mode === "code") && <label className={labelClass}><span>{zh ? "图片验证码" : "Image code"}</span><div className="mt-2 flex min-w-0 gap-2"><input required autoComplete="off" maxLength={5} value={captchaAnswer} onChange={(event) => setCaptchaAnswer(event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))} className="h-[clamp(42px,6svh,56px)] min-w-0 flex-1 rounded-[10px] border border-[#d8d8d6] bg-[#eff4ff] px-3 text-base font-normal uppercase outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder={zh ? "输入图中字符" : "Enter characters"} /><button type="button" onClick={() => void refreshCaptcha()} className="flex w-[clamp(115px,12vw,176px)] shrink-0 items-center justify-center overflow-hidden rounded-[10px] border border-stone-300 bg-[#eef4ff]" aria-label={zh ? "刷新图片验证码" : "Refresh image code"} title={zh ? "点击刷新图片验证码" : "Click to refresh image code"}>{captcha ? <Image unoptimized src={captcha.image} alt={zh ? "图片验证码" : "Image code"} width={176} height={56} className="h-full w-full object-fill" /> : <RefreshCw className="size-5 text-stone-500" />}</button></div></label>}
          {message && <p role="status" title={message} className="shrink-0 overflow-hidden text-ellipsis whitespace-nowrap rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">{message}</p>}
          <button type="submit" disabled={busy || ((mode === "login" || mode === "code") && !captcha)} className="mt-auto h-[clamp(42px,6svh,56px)] w-full shrink-0 whitespace-nowrap rounded-[10px] bg-[#292823] text-[clamp(15px,1.2vw,21px)] font-semibold text-white transition hover:bg-stone-700 disabled:opacity-60">{busy ? (zh ? "请稍候…" : "Please wait…") : title}</button>
        </form>
        <div className="mt-[clamp(10px,2svh,22px)] flex shrink-0 items-center justify-between gap-2 whitespace-nowrap text-[clamp(10px,1vw,14px)] text-stone-600"><button type="button" onClick={() => changeMode(mode === "code" ? "login" : "code")} className="underline underline-offset-4">{mode === "code" ? (zh ? "密码登录" : "Password sign in") : (zh ? "一次性验证码登录" : "Sign in with a code")}</button><button type="button" onClick={() => changeMode(mode === "reset" ? "login" : "reset")} className="underline underline-offset-4">{mode === "reset" ? (zh ? "返回登录" : "Back to sign in") : (zh ? "忘记密码？" : "Forgot password?")}</button></div>
      </section>
    </div>
  </div>;
}
