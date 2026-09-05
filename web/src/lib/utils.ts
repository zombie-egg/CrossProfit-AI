import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
export const money = (value: string | number | null | undefined) => { const number = Number(value ?? 0); const absolute = Math.abs(number).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); return number < 0 ? `-$${absolute}` : `$${absolute}`; };
export const percent = (value: string | number | null | undefined) => `${(Number(value ?? 0) * 100).toLocaleString("zh-CN", { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%`;
export const quantity = (value: number) => value.toLocaleString("zh-CN");
export const platformName = (value: string) => ({ tiktok_shop: "TikTok Shop", amazon: "Amazon", temu: "Temu", shein: "SHEIN" }[value] ?? value);
export const riskStyles: Record<string, string> = { HIGHLY_RECOMMENDED: "border-emerald-200 bg-emerald-50 text-emerald-700", RECOMMENDED: "border-green-200 bg-green-50 text-green-700", CAUTION: "border-amber-200 bg-amber-50 text-amber-700", NOT_RECOMMENDED: "border-orange-200 bg-orange-50 text-orange-700", LOSS: "border-red-200 bg-red-50 text-red-700" };

