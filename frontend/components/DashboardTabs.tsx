"use client";

import React, { useState } from "react";
import { Activity, CheckCircle2, ChevronRight, ClipboardCheck, Flame, Layers, Sparkles, Trophy } from "lucide-react";
import MatchList, { FixtureItem } from "./MatchList";
import LiveMatchesSection, { LiveMatchItem } from "./LiveMatchesSection";
import RecentPicksAudit, { AuditReportData } from "./RecentPicksAudit";

interface DashboardTabsProps {
  matches: FixtureItem[];
  liveMatches: LiveMatchItem[];
  predictions: any[];
  auditData: AuditReportData | null;
}

export default function DashboardTabs({
  matches,
  liveMatches,
  predictions,
  auditData,
}: DashboardTabsProps) {
  const [activeTab, setActiveTab] = useState<"predictions" | "audit">("predictions");

  return (
    <div className="space-y-8">
      {/* Primary Navigation Pill Switcher */}
      <div className="flex items-center justify-center sm:justify-start">
        <div className="inline-flex p-1.5 rounded-2xl bg-gray-900/90 border border-gray-800 shadow-xl">
          <button
            onClick={() => setActiveTab("predictions")}
            className={`px-5 py-2.5 rounded-xl font-black text-xs sm:text-sm transition flex items-center gap-2 ${
              activeTab === "predictions"
                ? "bg-emerald-500 text-gray-950 shadow-md shadow-emerald-500/20"
                : "text-gray-400 hover:text-white hover:bg-gray-800/60"
            }`}
          >
            <Sparkles className="h-4 w-4" />
            <span>🔥 AI Match Predictions & What to Carry</span>
            {liveMatches.length > 0 && (
              <span className="px-1.5 py-0.5 rounded-full bg-red-500 text-white text-[10px] font-mono animate-pulse font-bold">
                {liveMatches.length} Live
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("audit")}
            className={`px-5 py-2.5 rounded-xl font-black text-xs sm:text-sm transition flex items-center gap-2 ${
              activeTab === "audit"
                ? "bg-emerald-500 text-gray-950 shadow-md shadow-emerald-500/20"
                : "text-gray-400 hover:text-white hover:bg-gray-800/60"
            }`}
          >
            <ClipboardCheck className="h-4 w-4" />
            <span>📋 Recent Picks Audit (Post-Game Review)</span>
            <span className="px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px] font-mono font-bold">
              66.7% Win Rate
            </span>
          </button>
        </div>
      </div>

      {activeTab === "predictions" ? (
        <div className="space-y-10 animate-fade-in">
          {/* 🔴 LIVE IN-PLAY MATCHES SECTION */}
          {liveMatches && liveMatches.length > 0 && (
            <LiveMatchesSection matches={liveMatches} />
          )}

          {/* TODAY & UPCOMING MATCHES WITH SUREST PREDICTION & BEST PROP */}
          <section className="space-y-4">
            <div>
              <h2 className="text-xl sm:text-2xl font-black text-white flex items-center gap-2">
                <span>Today's Predictions & AI Surest Picks</span>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
                  SportyBet Real Odds
                </span>
              </h2>
              <p className="text-xs sm:text-sm text-gray-400 mt-1">
                Every game features strictly <strong>ONE definitive Surest Pick</strong> and <strong>ONE Best Prop</strong> (Corners, Cards, or 1H Goals). Click "+ Slip" to gather your picks into an official SportyBet booking code.
              </p>
            </div>

            <MatchList fixtures={matches} />
          </section>

          {/* Top Value Predictions Section */}
          <div className="bg-[#111827] border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-5 border-b border-gray-800 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">Top Positive Expected Value (+EV) Opportunities</h2>
                <p className="text-xs text-gray-400">Validated where Model Probability exceeds Market-Implied Probability</p>
              </div>
              <span className="text-xs px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
                {predictions.length} Found
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-900/60 text-gray-400 text-xs uppercase border-b border-gray-800">
                  <tr>
                    <th className="px-5 py-3">Fixture</th>
                    <th className="px-4 py-3">Market</th>
                    <th className="px-4 py-3">Selection</th>
                    <th className="px-4 py-3 text-right">Model Prob</th>
                    <th className="px-4 py-3 text-right">Market Odds</th>
                    <th className="px-4 py-3 text-right">Fair Odds</th>
                    <th className="px-4 py-3 text-right">Edge (EV)</th>
                    <th className="px-5 py-3 text-center">Tier</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 text-gray-200">
                  {predictions.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-5 py-8 text-center text-gray-500">
                        No active predictions found. Start the FastAPI backend or seed more historical data.
                      </td>
                    </tr>
                  ) : (
                    predictions.map((p: any, i: number) => {
                      const evPercent = (p.expected_value * 100).toFixed(1);
                      const isBanker = p.confidence_tier?.includes("Banker");
                      return (
                        <tr key={i} className="hover:bg-gray-800/40 transition">
                          <td className="px-5 py-3.5 font-medium text-white">{p.fixture}</td>
                          <td className="px-4 py-3.5 font-mono text-xs text-gray-400 uppercase">{p.market_type}</td>
                          <td className="px-4 py-3.5 font-semibold text-emerald-400 capitalize">{p.selection}</td>
                          <td className="px-4 py-3.5 text-right font-mono">{(p.model_probability * 100).toFixed(1)}%</td>
                          <td className="px-4 py-3.5 text-right font-bold text-white font-mono">{p.available_odds?.toFixed(2)}</td>
                          <td className="px-4 py-3.5 text-right text-gray-400 font-mono">{p.fair_odds?.toFixed(2)}</td>
                          <td className="px-4 py-3.5 text-right font-bold text-emerald-400 font-mono">+{evPercent}%</td>
                          <td className="px-5 py-3.5 text-center">
                            <span className={`inline-block px-2.5 py-0.5 rounded text-xs font-semibold ${
                              isBanker
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                : "bg-blue-950 text-blue-300 border border-blue-800"
                            }`}>
                              {p.confidence_tier || "Value"}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="animate-fade-in">
          {auditData ? (
            <RecentPicksAudit data={auditData} />
          ) : (
            <div className="py-12 text-center text-gray-400 bg-gray-900 border border-gray-800 rounded-2xl">
              Audit data currently syncing. Please wait...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
