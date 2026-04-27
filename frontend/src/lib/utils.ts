/**
 * EN: Small UI utilities — Tailwind class merge, number formatting, URL helpers.
 * PT: Utilitários de UI — fusão de classes Tailwind, formatação, URLs.
 */
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  // EN: clsx for conditional classes + tailwind-merge to dedupe conflicting utilities.
  // PT: clsx para condicionais + tailwind-merge para resolver conflitos de utilities.
  return twMerge(clsx(inputs));
}

export function fmtPct(n: number, digits = 1): string {
  return `${(n * 100).toFixed(digits)}%`;
}

export function fmtMs(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function domainFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function faviconFor(domain: string): string {
  return `https://www.google.com/s2/favicons?sz=32&domain=${domain}`;
}
