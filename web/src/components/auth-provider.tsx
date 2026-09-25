"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MerchantAccount } from "@/types";
import { AuthPage } from "@/components/auth-page";

type Locale = "zh" | "en";
interface AuthContextValue {
  account: MerchantAccount | null;
  locale: Locale;
  setAccount: (account: MerchantAccount | null) => void;
  setLocale: (locale: Locale) => Promise<void>;
  logout: () => Promise<void>;
}
const Context = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [account, setAccount] = useState<MerchantAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [locale, setLocaleState] = useState<Locale>("zh");
  useEffect(() => {
    const saved = localStorage.getItem("crossprofit-locale");
    if (saved === "en" || saved === "zh") setLocaleState(saved);
    void api.me().then((value) => { setAccount(value); setLocaleState(value.locale); }).catch(() => setAccount(null)).finally(() => setLoading(false));
    const unauthorized = () => setAccount(null);
    window.addEventListener("crossprofit:unauthorized", unauthorized);
    return () => window.removeEventListener("crossprofit:unauthorized", unauthorized);
  }, []);
  const setLocale = async (value: Locale) => {
    setLocaleState(value);
    localStorage.setItem("crossprofit-locale", value);
    document.documentElement.lang = value === "zh" ? "zh-CN" : "en";
    if (account) {
      try { await api.setLocale(value); setAccount({ ...account, locale: value }); } catch { /* local display still works */ }
    }
  };
  const logout = async () => { await api.logout(); setAccount(null); };
  return <Context.Provider value={{ account, locale, setAccount, setLocale, logout }}>
    {loading ? <div className="grid min-h-screen place-items-center text-sm text-slate-500">Loading…</div> : account ? children : <AuthPage />}
  </Context.Provider>;
}

export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
