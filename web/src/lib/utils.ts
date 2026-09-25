import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
export const money = (value: string | number | null | undefined, currency = "USD") => { const number = Number(value ?? 0); try { return new Intl.NumberFormat(currency === "CNY" ? "zh-CN" : "en-US", { style: "currency", currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(number); } catch { return `${currency} ${number.toFixed(2)}`; } };
export const percent = (value: string | number | null | undefined) => `${(Number(value ?? 0) * 100).toLocaleString("zh-CN", { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%`;
export const quantity = (value: number) => value.toLocaleString("zh-CN");
export const platformName = (value: string) => ({ tiktok_shop: "TikTok Shop", amazon: "Amazon", temu: "Temu", shein: "SHEIN", taobao: "淘宝", pinduoduo: "拼多多", douyin: "抖音电商", xianyu: "闲鱼", miaoshou: "妙手 ERP" }[value] ?? value);
export const riskStyles: Record<string, string> = { HIGHLY_RECOMMENDED: "border-emerald-200 bg-emerald-50 text-emerald-700", RECOMMENDED: "border-green-200 bg-green-50 text-green-700", CAUTION: "border-amber-200 bg-amber-50 text-amber-700", NOT_RECOMMENDED: "border-orange-200 bg-orange-50 text-orange-700", LOSS: "border-red-200 bg-red-50 text-red-700" };
