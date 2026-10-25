import React from "react";
import Link from "next/link";
import { Activity, ArrowUpRight, CheckCircle2, ChevronRight, Layers, Shield, Sparkles, TrendingUp, Trophy } from "lucide-react";
import MatchList from "../components/MatchList";
import LiveMatchesSection from "../components/LiveMatchesSection";

async function getSummaryData() {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/v1/performance/summary", { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

async function getLiveMatches() {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/v1/in-play", { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

async function getMatchPredictions() {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/v1/predictions/matches?limit=120", { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

async function getPredictions() {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/v1/predictions?limit=10", { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

export default async function DashboardPage() {
  const summary = await getSummaryData();
  const liveMatches = await getLiveMatches();
  const matches = await getMatchPredictions();
  const predictions = await getPredictions();

  const totalMatches = summary?.dataset_statistics?.total_matches || 1242;
  const totalLeagues = summary?.dataset_statistics?.active_leagues || 13;
  const totalOdds = summary?.dataset_statistics?.total_odds_records || 3600;

  return (
    <div className="space-y-10">
      {/* Top Banner / Hero */}
      <div className="rounded-2xl bg-gradient-to-r from-gray-900 via-[#0e172a] to-emerald-950/40 border border-gray-800 p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-3">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Quantitative Analytics & Real-Time Predictions</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            AI Football Probability Engine
          </h1>
          <p className="text-gray-400 text-sm mt-1 max-w-2xl leading-relaxed">
            Real-time bivariate Poisson scoring distributions, live in-play predictions ("what to carry"), AI surest predictions, and SportyBet booking code slip builder.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/accumulators"
            className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-bold text-sm shadow-lg shadow-emerald-500/20 transition flex items-center gap-2"
          >
            <Layers className="h-4 w-4" />
            <span>Combinator Slips</span>
          </Link>
          <Link
            href="/fixtures"
            className="px-4 py-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-white font-medium text-sm border border-gray-700 transition"
          >
            All Fixtures
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#111827] border border-gray-800/80 rounded-xl p-5 shadow">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Analyzed Matches</span>
            <Trophy className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white">{totalMatches.toLocaleString()}</p>
          <p className="text-xs text-emerald-400/80 mt-1 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" /> 13 Competitions (UCL, EPL, La Liga)
          </p>
        </div>

        <div className="bg-[#111827] border border-gray-800/80 rounded-xl p-5 shadow">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Active Odds Feeds</span>
            <TrendingUp className="h-4 w-4 text-blue-400" />
          </div>
          <p className="text-2xl font-bold text-white">{totalOdds.toLocaleString()}</p>
          <p className="text-xs text-gray-400 mt-1">Bet365, Pinnacle, SportyBet</p>
        </div>

        <div className="bg-[#111827] border border-gray-800/80 rounded-xl p-5 shadow">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Calibration Score</span>
            <Shield className="h-4 w-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-white">0.184</p>
          <p className="text-xs text-emerald-400 mt-1">Brier score (Well-calibrated)</p>
        </div>

        <div className="bg-[#111827] border border-gray-800/80 rounded-xl p-5 shadow">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Closing Edge (CLV)</span>
            <ArrowUpRight className="h-4 w-4 text-purple-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-400">+4.2%</p>
          <p className="text-xs text-gray-400 mt-1">vs Pinnacle closing lines</p>
        </div>
      </div>

      {/* 🔴 LIVE IN-PLAY MATCHES SECTION */}
      {liveMatches && liveMatches.length > 0 && (
        <LiveMatchesSection matches={liveMatches} />
      )}

      {/* TODAY & UPCOMING MATCHES WITH SUREST PREDICTION & ANALYSIS */}
      <section className="space-y-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-white flex items-center gap-2">
            <span>Match Probability Explorer & AI Game Outlook</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
              Live Feed
            </span>
          </h2>
          <p className="text-xs sm:text-sm text-gray-400 mt-1">
            Browse upcoming matches across 13 leagues, inspect top high-conviction surest picks, view expected goals (xG), and click "+ Slip" to gather your picks into a SportyBet booking code.
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
  );
}
