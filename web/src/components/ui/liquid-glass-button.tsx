"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const glassBase = "relative isolate inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 overflow-hidden whitespace-nowrap rounded-xl border text-sm font-semibold outline-none backdrop-blur-xl transition-[transform,background-color,box-shadow,border-color,filter] duration-200 before:pointer-events-none before:absolute before:inset-x-1 before:top-px before:h-px before:bg-gradient-to-r before:from-transparent before:via-white/90 before:to-transparent after:pointer-events-none after:absolute after:inset-0 after:-z-10 after:bg-gradient-to-br after:from-white/30 after:via-transparent after:to-white/10 hover:-translate-y-0.5 hover:brightness-[1.03] active:translate-y-0 active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4";

const buttonVariants = cva(glassBase, {
  variants: {
    variant: {
      default: "border-blue-400/50 bg-blue-600/90 text-white shadow-[0_8px_22px_-10px_rgba(37,99,235,0.9),inset_0_1px_0_rgba(255,255,255,0.32)] hover:bg-blue-600/95",
      cool: "border-indigo-400/40 bg-gradient-to-b from-blue-500/90 to-indigo-600/90 text-white shadow-[0_9px_24px_-10px_rgba(79,70,229,0.85),inset_0_1px_0_rgba(255,255,255,0.35)]",
      outline: "border-white/80 bg-white/50 text-slate-800 shadow-[0_7px_20px_-13px_rgba(15,23,42,0.48),inset_0_1px_0_rgba(255,255,255,0.95),inset_0_-1px_0_rgba(148,163,184,0.16)] hover:bg-white/70 hover:text-slate-950",
      secondary: "border-slate-200/50 bg-slate-100/50 text-slate-800 shadow-[0_7px_18px_-14px_rgba(15,23,42,0.45),inset_0_1px_0_rgba(255,255,255,0.9)] hover:bg-slate-100/80",
      ghost: "border-white/25 bg-white/20 text-slate-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.38)] hover:border-white/60 hover:bg-white/50 hover:text-slate-950",
      destructive: "border-red-300/50 bg-red-500/90 text-white shadow-[0_8px_22px_-11px_rgba(220,38,38,0.85),inset_0_1px_0_rgba(255,255,255,0.3)] hover:bg-red-600/95",
      link: "border-transparent bg-transparent text-blue-700 shadow-none backdrop-blur-none before:hidden after:hidden hover:translate-y-0 hover:underline",
    },
    size: {
      default: "h-9 px-4 py-2",
      xs: "h-6 rounded-lg px-2 text-xs",
      sm: "h-8 rounded-xl px-3 text-xs",
      lg: "h-10 px-6",
      xl: "h-12 px-8",
      xxl: "h-14 px-10",
      icon: "size-9 p-0",
      "icon-xs": "size-6 rounded-lg p-0 [&_svg]:size-3",
      "icon-sm": "size-8 rounded-xl p-0 [&_svg]:size-3.5",
      "icon-lg": "size-10 p-0",
    },
  },
  defaultVariants: { variant: "default", size: "default" },
});

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";
  return <Comp data-slot="button" className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
});
Button.displayName = "Button";

const liquidbuttonVariants = buttonVariants;
const LiquidButton = Button;

type ColorVariant = "default" | "primary" | "success" | "error" | "gold" | "bronze";
const metalColors: Record<ColorVariant, string> = {
  default: "from-slate-500/90 to-slate-700/90",
  primary: "from-blue-500/90 to-indigo-700/90",
  success: "from-emerald-400/90 to-emerald-700/90",
  error: "from-red-400/90 to-red-700/90",
  gold: "from-amber-300/95 to-amber-600/95",
  bronze: "from-orange-400/90 to-amber-800/90",
};

interface MetalButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> { variant?: ColorVariant }
const MetalButton = React.forwardRef<HTMLButtonElement, MetalButtonProps>(({ children, className, variant = "default", ...props }, ref) => (
  <button ref={ref} className={cn(glassBase, "h-11 bg-gradient-to-b px-6 text-white shadow-[0_8px_20px_-10px_rgba(15,23,42,0.75),inset_0_1px_0_rgba(255,255,255,0.45)]", metalColors[variant], className)} {...props}>{children}</button>
));
MetalButton.displayName = "MetalButton";

/** Shared filter definition for optional advanced SVG backdrop distortion. */
function GlassFilter() {
  return <svg aria-hidden className="absolute size-0"><defs><filter id="container-glass" x="0%" y="0%" width="100%" height="100%" colorInterpolationFilters="sRGB"><feTurbulence type="fractalNoise" baseFrequency="0.05 0.05" numOctaves={1} seed={1} result="turbulence"/><feGaussianBlur in="turbulence" stdDeviation={2} result="blurredNoise"/><feDisplacementMap in="SourceGraphic" in2="blurredNoise" scale={70} xChannelSelector="R" yChannelSelector="B" result="displaced"/><feGaussianBlur in="displaced" stdDeviation={4} result="finalBlur"/><feComposite in="finalBlur" in2="finalBlur" operator="over"/></filter></defs></svg>;
}

export { Button, buttonVariants, liquidbuttonVariants, LiquidButton, MetalButton, GlassFilter };
