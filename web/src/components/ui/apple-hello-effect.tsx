"use client";

import type { TargetAndTransition } from "motion/react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

const initialProps: TargetAndTransition = { pathLength: 0, opacity: 0 };
const animateProps: TargetAndTransition = { pathLength: 1, opacity: 1 };
const title = "PROFIT BEFORE TRAFFIC";

type Props = React.ComponentProps<typeof motion.svg> & {
  speed?: number;
  onAnimationComplete?: () => void;
};

/** The prompt component is retained as a reusable Apple-style path animation. */
function AppleHelloEnglishEffect({ className, speed = 1, onAnimationComplete, ...props }: Props) {
  const calc = (x: number) => x * speed;
  return (
    <motion.svg className={cn("h-20", className)} viewBox="0 0 638 200" fill="none" stroke="currentColor" strokeWidth="14.8883" initial={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: .5 }} {...props}>
      <title>hello</title>
      <motion.path d="M8.69214 166.553C36.2393 151.239 61.3409 131.548 89.8191 98.0295C109.203 75.1488 119.625 49.0228 120.122 31.0026C120.37 17.6036 113.836 7.43883 101.759 7.43883C88.3598 7.43883 79.9231 17.6036 74.7122 40.9363C69.005 66.5793 64.7866 96.0036 54.1166 190.356" strokeLinecap="round" initial={initialProps} animate={animateProps} transition={{ duration: calc(.8), ease: "easeInOut", opacity: { duration: calc(.4) } }} />
      <motion.path d="M55.1624 181.135C60.6251 133.114 81.4118 98.0479 107.963 98.0479C123.844 98.0479 133.937 110.703 131.071 128.817C122.869 178.941 130.128 191.348 152.122 191.348C239.208 192.341 335.86 137.292 359.199 75.8585C401.015 166.301 444.416 191.348 499.471 138.402C508.955 111.447 520.618 94.8221 544.935 94.8221C580.916 94.8221 603.549 125.866 630.047 96.7186" strokeLinecap="round" initial={initialProps} animate={animateProps} transition={{ duration: calc(2.8), ease: "easeInOut", delay: calc(.7), opacity: { duration: calc(.7), delay: calc(.7) } }} onAnimationComplete={onAnimationComplete} />
    </motion.svg>
  );
}

const writingTransition = (speed: number, delay = 0) => ({
  strokeDashoffset: { duration: 2.15 * speed, delay, ease: "easeInOut" as const },
  strokeOpacity: { duration: .18 * speed, delay },
  fillOpacity: { duration: .72 * speed, delay: delay + 1.48 * speed, ease: "easeOut" as const },
});

function WritingText({ children, x, y, speed, delay = 0, onAnimationComplete }: { children: string; x: number; y: number; speed: number; delay?: number; onAnimationComplete?: () => void }) {
  return (
    <motion.text
      x={x}
      y={y}
      className="apple-written-title"
      fill="currentColor"
      stroke="currentColor"
      strokeWidth="0.85"
      strokeLinecap="round"
      strokeLinejoin="round"
      paintOrder="stroke fill"
      initial={{ strokeDasharray: 1900, strokeDashoffset: 1900, strokeOpacity: 0, fillOpacity: 0 }}
      animate={{ strokeDashoffset: 0, strokeOpacity: 1, fillOpacity: 1 }}
      transition={writingTransition(speed, delay)}
      onAnimationComplete={onAnimationComplete}
    >
      {children}
    </motion.text>
  );
}

/** Geometric Chinese headline whose glyph contours carry the restrained stroke animation. */
function AppleHelloChineseTitleEffect({ className, speed = 1, onAnimationComplete }: Pick<Props, "className" | "speed" | "onAnimationComplete">) {
  return (
    <motion.h1
      className={cn("poster-title text-black", className)}
      aria-label={title}
      initial={{ opacity: 0, clipPath: "inset(0 100% 0 0)", y: 8 }}
      animate={{ opacity: 1, clipPath: "inset(0 0% 0 0)", y: 0 }}
      transition={{ duration: 1.15 * speed, ease: [0.16, 1, 0.3, 1] }}
      onAnimationComplete={onAnimationComplete}
    >
      <span className="block lg:inline">PROFIT BEFORE</span>{" "}
      <span className="block lg:inline">TRAFFIC</span>
    </motion.h1>
  );
}

export { AppleHelloChineseTitleEffect, AppleHelloEnglishEffect };
