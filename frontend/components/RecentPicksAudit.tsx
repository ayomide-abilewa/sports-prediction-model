"use client";

import React, { useState } from "react";
import { Check, Copy, Flame, ShieldAlert, Sparkles, Target, TrendingUp, Trophy } from "lucide-react";

export interface AuditFixture {
  fixture: string;
  home_team: string;
  away_team: string;
  league: string;
  ft_score: string;
  main_pick: {
    name: string;
    market: string;
    probability: number;
    odds: number;
    status: "won" | "lost" | "push";
    status_symbol: string;
    profit: number;
  };
  best_prop: {
    name: string;
    market: string;
    probability: number;
    status: "won" | "lost" | "push";
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
    brier_calibration: number;
  };
  formatted_text: string;
  fixtures: AuditFixture[];
}

export default function RecentPicksAudit({ data }: { data: AuditReportData }) {
  const [filter, setFilter] = useState<"all" | "won" | "lost">("all");
  const [copied, setCopied] = useState(false);

  if (!data) return null;

  const handleCopy = () => {
    if (data.formatted_text) {
      navigator.clipboard.writeText(data.formatted_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    }
  };

  const filteredFixtures = data.fixtures.filter((f) => {
    if (filter === "won") return f.main_pick.status === "won";
    if (filter === "lost") return f.main_pick.status === "lost";
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
              {data.subtitle}. Every prediction rigorously graded upon final whistle with unit returns, win calibration, and prop tracking.
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
              {data.summary.brier_calibration.toFixed(4)}
            </p>
            <p className="text-xs text-emerald-400 font-mono font-bold mt-0.5">
              Target &lt; 0.20 (Well-Calibrated)
            </p>
          </div>
        </div>
      </div>

      {/* Filter Tabs & Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-800 pb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-black text-white uppercase tracking-wider font-mono">
            Fixture-by-Fixture Breakdown
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-gray-900 text-gray-400 border border-gray-800 font-mono">
            {filteredFixtures.length} matches
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setFilter("all")}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
              filter === "all"
                ? "bg-emerald-500 text-gray-950"
                : "bg-gray-900 text-gray-400 hover:text-white border border-gray-800"
            }`}
          >
            All ({data.fixtures.length})
          </button>
          <button
            onClick={() => setFilter("won")}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition flex items-center gap-1 ${
              filter === "won"
                ? "bg-emerald-500 text-gray-950"
                : "bg-gray-900 text-emerald-400 hover:text-white border border-gray-800"
            }`}
          >
            <span>Won ({data.summary.main_picks.wins})</span>
            <span>✅</span>
          </button>
          <button
            onClick={() => setFilter("lost")}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition flex items-center gap-1 ${
              filter === "lost"
                ? "bg-red-500 text-white"
                : "bg-gray-900 text-red-400 hover:text-white border border-gray-800"
            }`}
          >
            <span>Lost ({data.summary.main_picks.losses})</span>
            <span>❌</span>
          </button>
        </div>
      </div>

      {/* Fixtures List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredFixtures.map((f, i) => {
          const mainWon = f.main_pick.status === "won";
          return (
            <div
              key={i}
              className={`p-4 rounded-xl border transition flex flex-col justify-between gap-3 ${
                mainWon
                  ? "bg-[#111827]/90 border-gray-800 hover:border-emerald-500/40"
                  : "bg-gray-950/80 border-gray-900 hover:border-red-500/40"
              }`}
            >
              {/* Match Header */}
              <div className="flex items-center justify-between text-xs pb-2 border-b border-gray-800/60">
                <div className="flex items-center gap-2">
                  <span className="font-extrabold text-white text-sm">⚽ {f.fixture}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-gray-400 bg-gray-900 px-2 py-0.5 rounded border border-gray-800">
                    {f.league}
                  </span>
                  <span className="text-xs font-mono font-black px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                    FT: {f.ft_score}
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
                          @{f.main_pick.odds.toFixed(2)}
                        </span>
                      </div>
                      <span className="text-[10px] uppercase font-mono text-gray-500">
                        Main Pick • {f.main_pick.market}
                      </span>
                    </div>
                  </div>

                  <span
                    className={`font-mono font-bold text-xs px-2 py-0.5 rounded ${
                      f.main_pick.profit >= 0
                        ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                        : "bg-red-950 text-red-400 border border-red-800"
                    }`}
                  >
                    {f.main_pick.profit >= 0 ? "+" : ""}
                    {f.main_pick.profit.toFixed(2)}u
                  </span>
                </div>

                {/* 🔥 Best Prop */}
                <div className="p-2.5 rounded-lg bg-gray-950/70 border border-gray-800/80 flex items-center justify-between gap-2">
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
                    {f.best_prop.stat_detail}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
