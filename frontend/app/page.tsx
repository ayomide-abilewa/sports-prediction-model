import React from "react";
import Link from "next/link";
import { Activity, ArrowUpRight, CheckCircle2, ChevronRight, Layers, Shield, Sparkles, TrendingUp, Trophy } from "lucide-react";
import DashboardTabs from "../components/DashboardTabs";

export const dynamic = "force-dynamic";

async function getSummaryData() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/performance/summary`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

async function getLiveMatches() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/in-play`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

async function getMatchPredictions() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/predictions/matches?limit=120`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

async function getPredictions() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/predictions?limit=10`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

async function getAuditData() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/performance/audit`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

export default async function DashboardPage() {
  const [summary, liveMatches, matches, predictions, auditData] = await Promise.all([
    getSummaryData(),
    getLiveMatches(),
    getMatchPredictions(),
    getPredictions(),
    getAuditData(),
  ]);

  const totalMatches = summary?.dataset_statistics?.total_matches ?? 0;
  const totalLeagues = summary?.dataset_statistics?.active_leagues ?? 0;
  const totalOdds = summary?.dataset_statistics?.total_odds_records ?? 0;
  const settledPredictions = summary?.dataset_statistics?.settled_predictions ?? 0;

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
            Live scores, match forecasts with their data source shown, fixture markets, accumulator building, and tracked results.
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
            <span className="text-xs font-medium uppercase tracking-wider">Stored Matches</span>
            <Trophy className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white">{totalMatches.toLocaleString()}</p>
          <p className="text-xs text-emerald-400/80 mt-1 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" /> {totalLeagues} configured competitions
          </p>
        </div>

        <div className="bg-[#111827] border border-gray-800/80 rounded-xl p-5 shadow">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Stored Odds Records</span>
            <TrendingUp className="h-4 w-4 text-blue-400" />
          </div>
          <p className="text-2xl font-bold text-white">{totalOdds.toLocaleString()}</p>
          <p className="text-xs text-gray-400 mt-1">Bookmaker sources vary by competition</p>
        </div>

        <div className="bg-[#111827] border border-gray-800/80 rounded-xl p-5 shadow">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Graded Predictions</span>
            <Shield className="h-4 w-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-white">{settledPredictions ? settledPredictions.toLocaleString() : "—"}</p>
          <p className="text-xs text-gray-400 mt-1">Settled predictions · calibration not yet measured</p>
        </div>

        <div className="bg-[#111827] border border-gray-800/80 rounded-xl p-5 shadow">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Closing Edge (CLV)</span>
            <ArrowUpRight className="h-4 w-4 text-purple-400" />
          </div>
          <p className="text-2xl font-bold text-gray-400">—</p>
          <p className="text-xs text-gray-400 mt-1">Closing odds tracking not available</p>
        </div>
      </div>

      {/* DASHBOARD TABBED VIEW: PREDICTIONS / AUDIT */}
      <DashboardTabs
        matches={matches}
        liveMatches={liveMatches}
        predictions={predictions}
        auditData={auditData}
      />
    </div>
  );
}
