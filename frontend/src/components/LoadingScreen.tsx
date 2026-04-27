"use client";

import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

const TARGET = "Direito laboral português";

// Character pool weighted towards Latin/Portuguese glyphs — thematic feel
const POOL =
  "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" +
  "àáâãäåæçèéêëìíîïñòóôõöùúûü" +
  "0123456789§°ªº";

const SETTLE_DURATION = 2100; // ms for all chars to resolve
const HOLD_DURATION = 650;    // ms to hold after fully settled
const FADE_DURATION = 480;    // ms for exit fade

interface Props {
  onComplete: () => void;
}

export function LoadingScreen({ onComplete }: Props) {
  const targetChars = TARGET.split("");
  const nonSpaceCount = targetChars.filter((c) => c !== " ").length;

  const [displayChars, setDisplayChars] = useState<string[]>(() =>
    targetChars.map((c) =>
      c === " " ? " " : POOL[Math.floor(Math.random() * POOL.length)]
    )
  );
  const [settledCount, setSettledCount] = useState(0);
  const [visible, setVisible] = useState(true);

  const animRef = useRef<number>(0);
  const startRef = useRef<number | null>(null);
  const doneRef = useRef(false);

  useEffect(() => {
    const poolArr = POOL.split("");

    const tick = (timestamp: number) => {
      if (!startRef.current) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const progress = Math.min(elapsed / SETTLE_DURATION, 1);

      // Ease-out: chars settle faster at first, slow at the end
      const eased = 1 - Math.pow(1 - progress, 1.6);
      const targetSettled = Math.floor(eased * nonSpaceCount);

      setSettledCount(targetSettled);

      let settledSoFar = 0;
      const next = targetChars.map((char) => {
        if (char === " ") return " ";
        if (settledSoFar < targetSettled) {
          settledSoFar++;
          return char;
        }
        return poolArr[Math.floor(Math.random() * poolArr.length)];
      });
      setDisplayChars(next);

      if (progress < 1) {
        animRef.current = requestAnimationFrame(tick);
      } else if (!doneRef.current) {
        doneRef.current = true;
        setDisplayChars(targetChars);
        setSettledCount(nonSpaceCount);
        setTimeout(() => {
          setVisible(false);
          setTimeout(onComplete, FADE_DURATION);
        }, HOLD_DURATION);
      }
    };

    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const progress = nonSpaceCount > 0 ? settledCount / nonSpaceCount : 0;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="loading-screen"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4, ease: "easeInOut" }}
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center select-none"
          style={{ backgroundColor: "#070709" }}
        >
          {/* Center content */}
          <div className="flex flex-col items-center gap-12">

            {/* Brand mark */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              className="flex flex-col items-center gap-3"
            >
              <div
                className="w-14 h-14 rounded-xl border border-white/[0.10] flex items-center justify-center"
                style={{
                  boxShadow:
                    "0 0 0 1px rgba(77,127,255,0.10), 0 0 28px rgba(77,127,255,0.14)",
                }}
              >
                <motion.span
                  className="font-mono text-xl font-semibold"
                  style={{ color: "#f0f0f3" }}
                  animate={{ opacity: [1, 0.62, 1] }}
                  transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                >
                  HD
                </motion.span>
              </div>
              <span className="marker">/labor</span>
            </motion.div>

            {/* Scramble block */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.45, duration: 0.5 }}
              className="flex flex-col items-center gap-6"
            >
              {/* Article prefix + scrambling title */}
              <div className="flex items-baseline gap-3 flex-wrap justify-center px-6">
                <span
                  className="font-mono text-[11px] uppercase tracking-[0.14em] shrink-0"
                  style={{ color: "#5d5f68" }}
                >
                  Art. 1.º —
                </span>
                <span
                  className="font-mono text-base sm:text-lg"
                  style={{ letterSpacing: "0.03em" }}
                  aria-label={TARGET}
                  aria-live="polite"
                >
                  {displayChars.map((char, i) => {
                    const isSettled = char === targetChars[i];
                    return (
                      <span
                        key={i}
                        style={{
                          display: "inline-block",
                          minWidth: char === " " ? "0.42ch" : undefined,
                          color: isSettled ? "#f0f0f3" : "#4d7fff",
                          opacity: isSettled ? 1 : 0.55,
                          transition: isSettled
                            ? "color 0.06s ease, opacity 0.06s ease"
                            : undefined,
                        }}
                      >
                        {char === " " ? "\u00a0" : char}
                      </span>
                    );
                  })}
                </span>
              </div>

              {/* Progress bar */}
              <div
                className="w-52"
                style={{
                  height: "1px",
                  background: "rgba(255,255,255,0.065)",
                  borderRadius: "999px",
                  overflow: "hidden",
                }}
              >
                <motion.div
                  style={{
                    height: "100%",
                    width: `${progress * 100}%`,
                    background: "#4d7fff",
                    boxShadow: "0 0 6px rgba(77,127,255,0.7)",
                    borderRadius: "999px",
                  }}
                />
              </div>
            </motion.div>
          </div>

          {/* Bottom-right version marker */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9, duration: 0.7 }}
            className="absolute bottom-8 right-10 marker"
          >
            v1 · 2026
          </motion.div>

          {/* Bottom-left subtle hint */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.0, duration: 0.7 }}
            className="absolute bottom-8 left-10 marker"
            style={{ color: "rgba(93,95,104,0.5)" }}
          >
            a carregar
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
