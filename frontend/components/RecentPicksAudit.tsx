"use client";

import React, { useState } from "react";
import {
  Calendar,
  Check,
  Clock,
  Copy,
  Flame,
  Info,
  Search,
  Sparkles,
  Target,
  TrendingUp,
  Trophy,
} from "lucide-react";

export interface AuditFixture {
  fixture: string;
  home_team: string;
  away_team: string;
  league: string;
  matchday?: string;
  played_date?: string;
  kickoff_time?: string;
  time_ago?: string;
  ft_score: string;
  pick_tracking?: string;
  main_pick: {
    name: string;
    market: string;
    probability: number;
    odds: number | null;
    status: "won" | "lost" | "push" | "pending" | "ungraded";
    status_symbol: string;
    profit: number | null;
  };
  best_prop?: {
    name: string;
    market: string;
    probability: number;
    status: "won" | "lost" | "push" | "pending" | "ungraded";
    status_symbol: string;
    stat_detail: string;
  };
}

export interface AuditReportData {
  audit_date: string;
  title: string;
  subtitle: string;
  summary: {
    main_picks: {
      graded: number;
      wins: number;
      losses: number;
      win_rate: number;
      net_profit: number;
      roi: number;
    };
    best_props: {
      graded: number;
      wins: number;
      losses: number;
      pushes: number;
      win_rate: number;
    };
    brier_calibration: number | null;
  };
  formatted_text: string;
  fixtures: AuditFixture[];
}

export default function RecentPicksAudit({ data }: { data: AuditReportData }) {
  const [filter, setFilter] = useState<"all" | "won" | "lost">("all");
  const [selectedLeague, setSelectedLeague] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [copied, setCopied] = useState(false);

  if (!data) return null;

  const handleCopy = () => {
    if (data.formatted_text) {
      navigator.clipboard.writeText(data.formatted_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    }
  };

  const leagues = ["all", ...Array.from(new Set(data.fixtures.map((f) => f.league)))];

  const filteredFixtures = data.fixtures.filter((f) => {
    // 1. Status Filter
    if (filter === "won" && f.main_pick.status !== "won") return false;
    if (filter === "lost" && f.main_pick.status !== "lost") return false;

    // 2. League Filter
    if (selectedLeague !== "all" && f.league !== selectedLeague) return false;

    // 3. Search Query
    if (searchQuery.trim() !== "") {
      const q = searchQuery.toLowerCase();
      const matchName = f.fixture.toLowerCase();
      const leagueName = f.league.toLowerCase();
      return matchName.includes(q) || leagueName.includes(q);
    }

    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-gray-900 via-[#111827] to-emerald-950/40 border border-emerald-500/30 p-6 sm:p-7 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-bold uppercase tracking-wider mb-2">
              <Trophy className="h-3.5 w-3.5" />
              <span>Transparent Model Performance Audit</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-2">
              <span>{data.title}</span>
            </h2>
            <p className="text-xs sm:text-sm text-gray-400 mt-1 max-w-2xl">
              {data.subtitle}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-black text-xs shadow-lg shadow-emerald-500/20 transition flex items-center gap-2"
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              <span>{copied ? "Copied Audit Text!" : "Copy Audit Report"}</span>
            </button>
          </div>
        </div>

        {/* 4 Performance Metric Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 mt-6 pt-6 border-t border-gray-800/80">
          {/* Main Picks Record */}
          <div className="p-4 rounded-xl bg-gray-950/70 border border-gray-800">
            <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
              <span className="font-mono uppercase text-[11px]">🎯 Main Picks Graded</span>
              <Target className="h-3.5 w-3.5 text-emerald-400" />
            </div>
            <p className="text-xl sm:text-2xl font-black text-white font-mono">
              {data.summary.main_picks.wins}W - {data.summary.main_picks.losses}L
            </p>
            <p className="text-xs text-emerald-400 font-mono font-bold mt-0.5">
              {data.summary.main_picks.win_rate}% Win Rate ({data.summary.main_picks.graded} Graded)
            </p>
          </div>

          {/* Best Props Record */}
          <div className="p-4 rounded-xl bg-gray-950/70 border border-gray-800">
            <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
              <span className="font-mono uppercase text-[11px]">🔥 Best Props Graded</span>
              <Flame className="h-3.5 w-3.5 text-amber-400" />
            </div>
            <p className="text-xl sm:text-2xl font-black text-white font-mono">
              {data.summary.best_props.wins}W - {data.summary.best_props.losses}L
            </p>
            <p className="text-xs text-amber-400 font-mono font-bold mt-0.5">
              {data.summary.best_props.win_rate}% Win Rate ({data.summary.best_props.graded} Graded)
            </p>
          </div>

          {/* Net Profit & ROI */}
          <div className="p-4 rounded-xl bg-gray-950/70 border border-gray-800">
            <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
              <span className="font-mono uppercase text-[11px]">💰 Main Net Profit</span>
              <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
            </div>
            <p className="text-xl sm:text-2xl font-black text-emerald-400 font-mono">
              {data.summary.main_picks.net_profit >= 0 ? "+" : ""}
              {data.summary.main_picks.net_profit.toFixed(2)} units
            </p>
            <p className="text-xs text-gray-300 font-mono font-bold mt-0.5">
              ROI: <span className="text-emerald-400">+{data.summary.main_picks.roi}%</span>
            </p>
          </div>

          {/* 1X2 Brier Calibration */}
          <div className="p-4 rounded-xl bg-gray-950/70 border border-gray-800">
            <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
              <span className="font-mono uppercase text-[11px]">📊 1X2 Brier Calibration</span>
              <Sparkles className="h-3.5 w-3.5 text-blue-400" />
            </div>
            <p className="text-xl sm:text-2xl font-black text-white font-mono">
              {data.summary.brier_calibration == null ? "Not measured" : data.summary.brier_calibration.toFixed(4)}
            </p>
            <p className="text-xs text-emerald-400 font-mono font-bold mt-0.5">
              Measured only after saved predictions are graded
            </p>
          </div>
        </div>
      </div>

      {/* Explanatory Info Card: When These Matches Were Played */}
      <div className="p-4 rounded-xl bg-blue-950/30 border border-blue-800/40 flex items-start gap-3">
        <Info className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-gray-300 space-y-1">
          <p className="font-semibold text-white">
            📅 When were these matches played?
          </p>
          <p className="text-gray-400 leading-relaxed">
            Only saved forecasts with completed scores are shown. Kickoff times and competition names come from the stored fixture records.
          </p>
        </div>
      </div>

      {/* Filter Tabs, League Selector & Search */}
      <div className="space-y-3 border-b border-gray-800 pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Status Tabs */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setFilter("all")}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition ${
                filter === "all"
                  ? "bg-emerald-500 text-gray-950 shadow-md shadow-emerald-500/20"
                  : "bg-gray-900 text-gray-400 hover:text-white border border-gray-800"
              }`}
            >
              All Matches ({data.fixtures.length})
            </button>
            <button
              onClick={() => setFilter("won")}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1 ${
                filter === "won"
                  ? "bg-emerald-500 text-gray-950 shadow-md shadow-emerald-500/20"
                  : "bg-gray-900 text-emerald-400 hover:text-white border border-gray-800"
              }`}
            >
              <span>Main Picks Won ({data.summary.main_picks.wins})</span>
              <span>✅</span>
            </button>
            <button
              onClick={() => setFilter("lost")}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1 ${
                filter === "lost"
                  ? "bg-red-500 text-white shadow-md shadow-red-500/20"
                  : "bg-gray-900 text-red-400 hover:text-white border border-gray-800"
              }`}
            >
              <span>Main Picks Lost ({data.summary.main_picks.losses})</span>
              <span>❌</span>
            </button>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-gray-500" />
            <input
              type="text"
              placeholder="Search team (Arsenal, Inter)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-gray-900/90 border border-gray-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition"
            />
          </div>
        </div>

        {/* League Selector Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
          <span className="text-[11px] font-mono text-gray-500 uppercase whitespace-nowrap mr-1">
            League:
          </span>
          {leagues.map((l) => (
            <button
              key={l}
              onClick={() => setSelectedLeague(l)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                selectedLeague === l
                  ? "bg-emerald-500 text-gray-950 font-black"
                  : "bg-gray-900/80 text-gray-400 hover:text-white border border-gray-800"
              }`}
            >
              {l === "all" ? "All Competitions" : l}
            </button>
          ))}
        </div>
      </div>

      {/* Fixtures List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredFixtures.length === 0 ? (
          <div className="col-span-full py-12 text-center text-gray-500 bg-gray-950/60 rounded-2xl border border-gray-800">
            <Calendar className="h-8 w-8 mx-auto mb-2 text-gray-600" />
            <p className="font-semibold text-white">No fixtures found matching your filter</p>
            <p className="text-xs text-gray-400 mt-1">Try switching league or clearing the search query.</p>
          </div>
        ) : (
          filteredFixtures.map((f, i) => {
            const mainWon = f.main_pick.status === "won";
            const mainPending = f.main_pick.status === "pending";
            return (
              <div
                key={i}
                className={`p-4 rounded-xl border transition flex flex-col justify-between gap-3 ${
                  mainPending
                    ? "bg-gray-950/80 border-gray-800"
                    : mainWon
                    ? "bg-[#111827]/90 border-gray-800 hover:border-emerald-500/40"
                    : "bg-gray-950/80 border-gray-900 hover:border-red-500/40"
                }`}
              >
                {/* Match Header */}
                <div>
                  <div className="flex items-center justify-between text-xs pb-1.5">
                    <span className="font-black text-white text-base">⚽ {f.fixture}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] font-mono text-gray-300 bg-gray-900 px-2 py-0.5 rounded border border-gray-800">
                        {f.league}
                      </span>
                      <span className="text-xs font-mono font-black px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                        {f.ft_score === "Pending result" || f.ft_score === "Result unavailable" ? f.ft_score : `FT: ${f.ft_score}`}
                      </span>
                    </div>
                  </div>

                  {/* Kickoff Date & Matchday Information */}
                  <div className="flex items-center justify-between text-[11px] text-gray-400 font-mono pt-1 pb-2 border-b border-gray-800/60">
                    <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                      <Clock className="h-3 w-3 text-emerald-400" />
                      <span>{f.played_date || "Date unavailable"}</span>
                      {f.kickoff_time && <span className="text-gray-300">• {f.kickoff_time}</span>}
                    </span>
                    <span className="text-gray-500 text-[10px]">
                      {f.matchday || ""}
                    </span>
                  </div>
                </div>

                {/* Picks Breakdown */}
                <div className="space-y-2 text-xs">
                  {/* 🎯 Main Pick */}
                  <div className="p-2.5 rounded-lg bg-gray-950/70 border border-gray-800/80 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-base">{f.main_pick.status_symbol}</span>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-black text-white">{f.main_pick.name}</span>
                          <span className="text-[11px] font-mono text-gray-400">
                            ({(f.main_pick.probability * 100).toFixed(0)}%)
                          </span>
                          <span className="text-[11px] font-mono text-gray-300 font-bold">
                            {f.main_pick.odds ? `@${f.main_pick.odds.toFixed(2)}` : "odds unavailable"}
                          </span>
                        </div>
                        <span className="text-[10px] uppercase font-mono text-gray-500">
                          Main Pick • {f.main_pick.market}{f.pick_tracking === "reconstructed from saved forecasts" ? " • Reconstructed" : " • Carried"}
                        </span>
                      </div>
                    </div>

                    <span
                      className={`font-mono font-bold text-xs px-2 py-0.5 rounded ${
                        f.main_pick.status === "pending"
                          ? "bg-amber-950/50 text-amber-300 border border-amber-900"
                          : f.main_pick.status === "ungraded"
                          ? "bg-gray-900 text-gray-400 border border-gray-800"
                          : f.main_pick.profit == null
                          ? "bg-gray-900 text-gray-400 border border-gray-800"
                          : f.main_pick.profit >= 0
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : "bg-red-950 text-red-400 border border-red-800"
                      }`}
                    >
                      {f.main_pick.status === "pending" ? (f.ft_score === "Result unavailable" ? "Final score unavailable" : "Awaiting result") : f.main_pick.status === "ungraded" ? "Result received · market not gradeable" : f.main_pick.profit == null ? "No odds tracked" : `${f.main_pick.profit >= 0 ? "+" : ""}${f.main_pick.profit.toFixed(2)}u`}
                    </span>
                  </div>

                  {/* 🔥 Best Prop */}
                  {f.best_prop && <div className="p-2.5 rounded-lg bg-gray-950/70 border border-gray-800/80 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-base">{f.best_prop.status_symbol}</span>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-gray-200">{f.best_prop.name}</span>
                          <span className="text-[11px] font-mono text-gray-400">
                            ({(f.best_prop.probability * 100).toFixed(1)}%)
                          </span>
                        </div>
                        <span className="text-[10px] uppercase font-mono text-gray-500">
                          Best Prop • {f.best_prop.market}
                        </span>
                      </div>
                    </div>

                    <span className="font-mono text-xs text-gray-400 bg-gray-900 px-2 py-0.5 rounded border border-gray-800">
                      {f.best_prop.stat_detail || f.best_prop.status}
                    </span>
                  </div>}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
