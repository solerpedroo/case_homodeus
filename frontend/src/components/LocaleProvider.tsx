"use client";

/**
 * EN: Injects i18n React context from `useLocaleProvider` (see i18n.ts).
 * PT: Injeta o contexto i18n a partir de `useLocaleProvider` (ver i18n.ts).
 */

import { LocaleContext, useLocaleProvider } from "@/lib/i18n";

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const value = useLocaleProvider();
  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}
