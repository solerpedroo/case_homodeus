"use client";

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { LoadingScreen } from "@/components/LoadingScreen";

/**
 * Client-side shell rendered once per page load.
 * Shows the loading animation on first mount (entry / refresh),
 * then reveals the application underneath.
 */
export function ClientRoot({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);

  return (
    <>
      <AnimatePresence>
        {loading && <LoadingScreen onComplete={() => setLoading(false)} />}
      </AnimatePresence>
      {children}
    </>
  );
}
