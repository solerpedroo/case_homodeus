import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "HomoDeus Challenge - Pedro Soler",
  description:
    "HomoDeus Challenge submission by Pedro Soler: labor law & payroll Q&A with citations and deterministic calculators.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt" className={`${inter.variable} ${jetbrains.variable} dark`}>
      <body className="min-h-screen bg-bg text-ink antialiased font-sans">
        {children}
      </body>
    </html>
  );
}
