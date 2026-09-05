"use client";

import { useEffect } from "react";
import { motion, type MotionValue, useAnimationFrame, useMotionTemplate, useMotionValue } from "framer-motion";
import { cn } from "@/lib/utils";

/** A quiet light-mode ambient background adapted from The Infinite Grid. */
export function Component({ className }: { className?: string }) {
  const mouseX = useMotionValue(-500);
  const mouseY = useMotionValue(-500);
  const gridOffsetX = useMotionValue(0);
  const gridOffsetY = useMotionValue(0);

  useEffect(() => {
    const updatePointer = (event: PointerEvent) => {
      mouseX.set(event.clientX);
      mouseY.set(event.clientY);
    };
    window.addEventListener("pointermove", updatePointer, { passive: true });
    return () => window.removeEventListener("pointermove", updatePointer);
  }, [mouseX, mouseY]);

  useAnimationFrame((_, delta) => {
    const step = Math.min(delta, 40) * 0.0125;
    gridOffsetX.set((gridOffsetX.get() + step) % 40);
    gridOffsetY.set((gridOffsetY.get() + step) % 40);
  });

  const maskImage = useMotionTemplate`radial-gradient(320px circle at ${mouseX}px ${mouseY}px, black, transparent)`;
  return (
    <div aria-hidden className={cn("pointer-events-none fixed inset-0 overflow-hidden bg-[#f8fafc]", className)}>
      <div className="absolute inset-0 text-slate-500 opacity-[0.045]"><GridPattern offsetX={gridOffsetX} offsetY={gridOffsetY} /></div>
      <motion.div className="absolute inset-0 text-blue-600 opacity-25" style={{ maskImage, WebkitMaskImage: maskImage }}><GridPattern offsetX={gridOffsetX} offsetY={gridOffsetY} /></motion.div>
      <div className="absolute -right-[14%] -top-[24%] size-[54vw] min-h-[440px] min-w-[440px] rounded-full bg-orange-300/25 blur-[130px]" />
      <div className="absolute right-[14%] -top-[14%] size-[28vw] min-h-[260px] min-w-[260px] rounded-full bg-indigo-300/25 blur-[110px]" />
      <div className="absolute -bottom-[28%] -left-[14%] size-[58vw] min-h-[480px] min-w-[480px] rounded-full bg-blue-300/30 blur-[140px]" />
      <div className="absolute inset-0 bg-gradient-to-b from-white/15 via-transparent to-white/20" />
    </div>
  );
}

function GridPattern({ offsetX, offsetY }: { offsetX: MotionValue<number>; offsetY: MotionValue<number> }) {
  return <svg className="size-full"><defs><motion.pattern id="crossprofit-grid-pattern" width="40" height="40" patternUnits="userSpaceOnUse" x={offsetX} y={offsetY}><path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1" /></motion.pattern></defs><rect width="100%" height="100%" fill="url(#crossprofit-grid-pattern)" /></svg>;
}
