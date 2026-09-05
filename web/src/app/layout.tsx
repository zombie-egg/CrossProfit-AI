import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/layout/app-shell";
import { DataProvider } from "@/components/data-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Anton, Inter, ZCOOL_QingKe_HuangYou } from "next/font/google";
import { cn } from "@/lib/utils";

const inter = Inter({subsets:['latin'],variable:'--font-sans'});
const geometricChinese = ZCOOL_QingKe_HuangYou({ weight: "400", subsets: ["latin"], variable: "--font-display-zh", display: "swap" });
const posterEnglish = Anton({ weight: "400", subsets: ["latin"], variable: "--font-poster", display: "swap" });

export const metadata: Metadata = {
  title: "CrossProfit AI · 跨境活动盈利助手",
  description: "让每一次流量，都有利润答案。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" className={cn("font-sans", inter.variable, geometricChinese.variable, posterEnglish.variable)}>
      <body>
        <TooltipProvider delay={100}>
          <DataProvider><AppShell>{children}</AppShell></DataProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}
