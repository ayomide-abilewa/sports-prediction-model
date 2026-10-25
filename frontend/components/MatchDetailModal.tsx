"use client";

import React, { useState } from "react";
import { useSlip } from "./SlipContext";
import { Activity, Check, Flame, Layers, Plus, Shield, Sparkles, TrendingUp, X, Zap } from "lucide-react";

export interface SurestPickItem {
  market: string;
  selection: string;
  prob: number;
  odds: number;
  fair_odds: number;
  ev: number;
  confidence_tier: string;
  rationale?: string;
}

export interface MatchAnalysisData {
  id: number;
  fixture: string;
  home_team: string;
  away_team: string;
  league: string;
  kickoff: string;
  surest_prediction?: SurestPickItem;
  top_surest_picks?: SurestPickItem[];
  ai_analysis?: string;
  expected_goals?: {
    home: number;
    away: number;
    total: number;
  };
  markets?: Array<{
    market: string;
    selection: string;
    odds: number;
    probability: number;
    ev?: number;
    confidence_tier?: string;
  }>;
}

export default function MatchDetailModal({
  match,
  onClose,
}: {
  match: MatchAnalysisData | null;
  onClose: () => void;
}) {
  const { addLeg, legs, setIsOpen } = useSlip();
  const [marketFilter, setMarketFilter] = useState<string>("all");

  if (!match) return null;

  const surestPicks = match.top_surest_picks || (match.surest_prediction ? [match.surest_prediction] : []);
  const allMarkets = match.markets || [];

  const filteredMarkets = allMarkets.filter((m) => {
    if (marketFilter === "all") return true;
    if (marketFilter === "1x2") return m.market === "1X2" || m.market === "Double Chance" || m.market === "Draw No Bet";
    if (marketFilter === "goals") return m.market === "Match Goals" || m.market === "Team Goals";
    if (marketFilter === "btts") return m.market === "GG / NG" || m.market === "Clean Sheet";
    if (marketFilter === "handicap") return m.market === "Handicap";
    if (marketFilter === "specials") return m.market === "Corners" || m.market === "Cards & Bookings";
    return true;
  });

  const handleMixAllSurest = () => {
    surestPicks.forEach((p) => {
      addLeg({
        match_id: match.id,
        fixture: match.fixture,
        market: p.market,
        selection: p.selection,
        odds: p.odds,
        probability: p.prob,
      });
    });
    setIsOpen(true);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in">
      <div className="w-full max-w-3xl bg-[#0f172a] border border-gray-700/80 rounded-2xl shadow-2xl overflow-hidden max-h-[92vh] flex flex-col">
        {/* Top Header */}
        <div className="p-5 border-b border-gray-800 bg-gray-900/90 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-semibold">
                {match.league || "European Competition"}
              </span>
              <span className="text-xs text-gray-400 font-mono">
                {new Date(match.kickoff).toLocaleDateString("en-GB", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-white">{match.fixture}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 space-y-6 overflow-y-auto">
          {/* AI SUREST PREDICTIONS SECTION */}
          {surestPicks.length > 0 && (
            <div className="rounded-2xl p-5 bg-gradient-to-r from-emerald-950/70 via-[#0e1e2d] to-gray-900 border border-emerald-500/50 shadow-lg shadow-emerald-500/10 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-bold uppercase tracking-wider">
                    <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Top High-Conviction Surest Predictions</span>
                  </span>
                  <span className="text-xs text-gray-400">({surestPicks.length} Model Picks)</span>
                </div>
                <button
                  onClick={handleMixAllSurest}
                  className="px-3.5 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-bold text-xs transition flex items-center gap-1.5 shadow"
                >
                  <Zap className="h-3.5 w-3.5" />
                  <span>Mix All Surest Picks</span>
                </button>
              </div>

              {/* Grid of Surest Picks */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {surestPicks.map((pick, idx) => {
                  const inSlip = legs.some(
                    (l) => l.match_id === match.id && l.selection === pick.selection
                  );
                  return (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-gray-950/80 border border-emerald-500/30 flex flex-col justify-between gap-2.5"
                    >
                      <div>
                        <div className="flex items-center justify-between text-[11px] text-gray-400">
                          <span className="font-mono uppercase text-emerald-400 font-bold">{pick.market}</span>
                          <span className="font-mono text-gray-400">{pick.confidence_tier}</span>
                        </div>
                        <p className="font-black text-white text-base mt-0.5">{pick.selection}</p>
                        <p className="text-[11px] text-gray-400 font-mono mt-0.5">
                          Win Prob: <span className="text-emerald-400 font-bold">{(pick.prob * 100).toFixed(0)}%</span> • Odds:{" "}
                          <span className="text-white font-extrabold">{pick.odds.toFixed(2)}</span>
                        </p>
                      </div>

                      <button
                        onClick={() =>
                          addLeg({
                            match_id: match.id,
                            fixture: match.fixture,
                            market: pick.market,
                            selection: pick.selection,
                            odds: pick.odds,
                            probability: pick.prob,
                          })
                        }
                        className={`w-full py-2 rounded-lg font-bold text-xs transition flex items-center justify-center gap-1.5 ${
                          inSlip
                            ? "bg-gray-800 text-emerald-400 border border-emerald-500/40"
                            : "bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-extrabold shadow-sm"
                        }`}
                      >
                        {inSlip ? (
                          <>
                            <Check className="h-3.5 w-3.5" />
                            <span>In Slip</span>
                          </>
                        ) : (
                          <>
                            <Plus className="h-3.5 w-3.5" />
                            <span>Add to Slip</span>
                          </>
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* AI Tactical Analysis / What It Thinks Will Happen */}
          {match.ai_analysis && (
            <div className="bg-gray-900/60 rounded-xl p-5 border border-gray-800 space-y-2">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Activity className="h-4 w-4 text-emerald-400" />
                <span>AI Game Outlook & Match Narrative</span>
              </h3>
              <p className="text-xs sm:text-sm text-gray-300 leading-relaxed">{match.ai_analysis}</p>
            </div>
          )}

          {/* Projected Scoreline & Expected Goals */}
          {match.expected_goals && (
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-3">
                <p className="text-[11px] text-gray-400 uppercase font-mono">{match.home_team}</p>
                <p className="text-xl font-black text-white font-mono mt-0.5">{match.expected_goals.home} xG</p>
              </div>
              <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-3">
                <p className="text-[11px] text-gray-400 uppercase font-mono">Match Total</p>
                <p className="text-xl font-black text-emerald-400 font-mono mt-0.5">{match.expected_goals.total} xG</p>
              </div>
              <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-3">
                <p className="text-[11px] text-gray-400 uppercase font-mono">{match.away_team}</p>
                <p className="text-xl font-black text-white font-mono mt-0.5">{match.expected_goals.away} xG</p>
              </div>
            </div>
          )}

          {/* CATEGORIZED BETTING MARKETS SECTION */}
          {allMarkets.length > 0 && (
            <div className="space-y-4 pt-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <h3 className="text-sm uppercase font-bold text-gray-300 tracking-wider">
                  Available Betting Markets ({filteredMarkets.length})
                </h3>

                {/* Market Category Filter Tabs */}
                <div className="flex items-center gap-1 overflow-x-auto pb-1 text-xs font-semibold">
                  {[
                    { id: "all", label: "All" },
                    { id: "1x2", label: "1X2 & DC" },
                    { id: "goals", label: "Goals & O/U" },
                    { id: "btts", label: "GG / NG" },
                    { id: "handicap", label: "Handicaps" },
                    { id: "specials", label: "Corners & Cards" },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setMarketFilter(tab.id)}
                      className={`px-2.5 py-1 rounded-md transition whitespace-nowrap ${
                        marketFilter === tab.id
                          ? "bg-emerald-500 text-gray-950 font-bold"
                          : "text-gray-400 hover:text-white bg-gray-900 border border-gray-800"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Markets Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {filteredMarkets.map((m, idx) => {
                  const inSlip = legs.some(
                    (l) => l.match_id === match.id && l.selection === m.selection
                  );
                  return (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-gray-900/70 border border-gray-800 hover:border-gray-700 flex items-center justify-between transition"
                    >
                      <div className="flex-1 pr-3">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono text-emerald-400 uppercase">{m.market}</span>
                          {m.confidence_tier && (
                            <span className="text-[10px] text-gray-500 font-mono">({m.confidence_tier})</span>
                          )}
                        </div>
                        <p className="text-sm font-bold text-white mt-0.5">{m.selection}</p>
                        <p className="text-[11px] text-gray-400 font-mono mt-0.5">
                          P: <span className="text-emerald-400 font-semibold">{(m.probability * 100).toFixed(0)}%</span> • Odds:{" "}
                          <span className="text-white font-extrabold">{m.odds.toFixed(2)}</span>
                          {m.ev !== undefined && (
                            <span className={m.ev >= 0 ? " text-emerald-400 ml-2" : " text-gray-500 ml-2"}>
                              EV: {(m.ev * 100).toFixed(1)}%
                            </span>
                          )}
                        </p>
                      </div>

                      <button
                        onClick={() =>
                          addLeg({
                            match_id: match.id,
                            fixture: match.fixture,
                            market: m.market,
                            selection: m.selection,
                            odds: m.odds,
                            probability: m.probability,
                          })
                        }
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1 ${
                          inSlip
                            ? "bg-gray-800 text-emerald-400 border border-emerald-500/40"
                            : "bg-gray-800 hover:bg-emerald-500 hover:text-gray-950 text-white border border-gray-700"
                        }`}
                      >
                        {inSlip ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                        <span>{inSlip ? "Added" : "Add"}</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
