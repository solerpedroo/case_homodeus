"use client";

import { LocaleContext, useLocaleProvider } from "@/lib/i18n";

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const value = useLocaleProvider();
  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}
