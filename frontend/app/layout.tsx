import "./globals.css";
import React from "react";
import Link from "next/link";
import { Activity, BarChart3, Database, Layers, ShieldCheck, Trophy } from "lucide-react";
import { SlipProvider } from "../components/SlipContext";
import BetSlipDrawer from "../components/BetSlipDrawer";

export const metadata = {
  title: "AI Football Probability Engine & Betting Terminal",
  description: "Quantitative football modeling, probability calibration, and automated accumulator builder.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0f1d] text-gray-100 flex flex-col">
        <SlipProvider>
          {/* Top Navigation Terminal Bar */}
          <header className="border-b border-gray-800 bg-[#0e1626]/80 backdrop-blur sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <Link href="/" className="font-bold text-lg tracking-wide text-white flex items-center gap-2">
                  <span>FOOTBALL<span className="text-emerald-400">PROB</span></span>
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">v1.0</span>
                </Link>
                <p className="text-xs text-gray-400">Quantitative Probability & Analytics Terminal</p>
              </div>
            </div>

            <nav className="flex items-center gap-1 sm:gap-2 text-sm font-medium">
              <Link
                href="/"
                className="px-3 py-1.5 rounded-md hover:bg-gray-800 text-gray-300 hover:text-white transition flex items-center gap-1.5"
              >
                <BarChart3 className="h-4 w-4 text-emerald-400" />
                <span>Dashboard</span>
              </Link>
              <Link
                href="/fixtures"
                className="px-3 py-1.5 rounded-md hover:bg-gray-800 text-gray-300 hover:text-white transition flex items-center gap-1.5"
              >
                <Trophy className="h-4 w-4 text-blue-400" />
                <span>Fixtures</span>
              </Link>
              <Link
                href="/accumulators"
                className="px-3 py-1.5 rounded-md hover:bg-gray-800 text-gray-300 hover:text-white transition flex items-center gap-1.5"
              >
                <Layers className="h-4 w-4 text-purple-400" />
                <span>Accumulators</span>
              </Link>
              <Link
                href="/performance"
                className="px-3 py-1.5 rounded-md hover:bg-gray-800 text-gray-300 hover:text-white transition flex items-center gap-1.5"
              >
                <ShieldCheck className="h-4 w-4 text-amber-400" />
                <span>Model Center</span>
              </Link>
            </nav>

            <div className="hidden lg:flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-gray-900 border border-gray-800">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-gray-300 font-mono">Dixon-Coles Active</span>
              </div>
            </div>
          </header>

          {/* Main Content Area */}
          <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
            {children}
          </main>

          {/* Persistent Bet Slip Floating Drawer */}
          <BetSlipDrawer />

          {/* Footer */}
          <footer className="border-t border-gray-800 py-6 px-6 text-center text-xs text-gray-500">
            <p>© 2026 Advanced AI Football Probability Engine. Research-grade statistical modelling for educational analytics.</p>
          </footer>
        </SlipProvider>
      </body>
    </html>
  );
}
