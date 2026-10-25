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
  event_id?: string;
  market_id?: string;
  outcome_id?: string;
  specifier?: string;
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
    event_id?: string;
    market_id?: string;
    outcome_id?: string;
    specifier?: string;
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

  const surest = match.surest_prediction || (match.top_surest_picks && match.top_surest_picks[0]);
  const allMarkets = match.markets || [];

  const filteredMarkets = allMarkets.filter((m) => {
    const mkt = m.market.toLowerCase();
    if (marketFilter === "all") return true;
    if (marketFilter === "corners") return mkt.includes("corner");
    if (marketFilter === "cards") return mkt.includes("card") || mkt.includes("booking");
    if (marketFilter === "goals") return mkt.includes("goal") || mkt.includes("over/under");
    if (marketFilter === "btts") return mkt.includes("gg") || mkt.includes("clean");
    if (marketFilter === "handicap") return mkt.includes("handicap");
    if (marketFilter === "1x2") return mkt.includes("1x2") || mkt.includes("double") || mkt.includes("draw");
    return true;
  });

  const isSurestInSlip = surest
    ? legs.some((l) => l.match_id === match.id && l.selection === surest.selection)
    : false;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in">
      <div className="w-full max-w-3xl bg-[#0f172a] border border-gray-700/80 rounded-2xl shadow-2xl overflow-hidden max-h-[92vh] flex flex-col">
        {/* Top Header */}
        <div className="p-5 border-b border-gray-800 bg-gray-900/90 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-semibold">
                {match.league || "Competition"}
              </span>
              <span className="text-xs text-gray-400 font-mono">
                {new Date(match.kickoff).toLocaleDateString("en-GB", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-950/80 text-red-300 border border-red-800 font-mono font-bold">
                SportyBet Verified Odds
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
          {/* THE ONE SUREST PREDICTION HIGHLIGHT */}
          {surest && (
            <div className="rounded-2xl p-5 bg-gradient-to-r from-emerald-950/70 via-[#0e1e2d] to-gray-900 border border-emerald-500/50 shadow-lg shadow-emerald-500/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 text-xs font-bold uppercase tracking-wider">
                  <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Single Surest Prediction to Carry</span>
                </span>
                <span className="text-xs font-mono text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800">
                  {surest.confidence_tier || "Bankers Tier"}
                </span>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-1">
                <div>
                  <span className="text-xs font-mono uppercase text-gray-400 px-2 py-0.5 rounded bg-gray-900 border border-gray-800">
                    {surest.market}
                  </span>
                  <p className="font-black text-white text-xl sm:text-2xl mt-1">{surest.selection}</p>
                  <p className="text-xs text-gray-400 font-mono mt-1">
                    Model Conviction: <span className="text-emerald-400 font-bold">{(surest.prob * 100).toFixed(0)}%</span> • SportyBet Odds:{" "}
                    <span className="text-white font-extrabold">{surest.odds.toFixed(2)}</span>
                  </p>
                </div>

                <button
                  onClick={() => {
                    addLeg({
                      match_id: match.id,
                      fixture: match.fixture,
                      market: surest.market,
                      selection: surest.selection,
                      odds: surest.odds,
                      probability: surest.prob,
                      event_id: surest.event_id,
                      market_id: surest.market_id,
                      outcome_id: surest.outcome_id,
                      specifier: surest.specifier,
                    });
                  }}
                  className={`px-5 py-3 rounded-xl font-black text-xs transition flex items-center justify-center gap-2 whitespace-nowrap shadow-md ${
                    isSurestInSlip
                      ? "bg-gray-800 text-emerald-400 border border-emerald-500/40"
                      : "bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-extrabold"
                  }`}
                >
                  {isSurestInSlip ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                  <span>{isSurestInSlip ? "In Bet Slip" : "+ Add Surest Pick"}</span>
                </button>
              </div>

              {surest.rationale && (
                <p className="text-xs text-gray-300 leading-relaxed border-t border-gray-800/80 pt-2.5">
                  <span className="font-bold text-white">Mathematical Rationale:</span> {surest.rationale}
                </p>
              )}
            </div>
          )}

          {/* AI Tactical Analysis / What It Thinks Will Happen */}
          {match.ai_analysis && (
            <div className="bg-gray-900/60 rounded-xl p-5 border border-gray-800 space-y-2">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Activity className="h-4 w-4 text-emerald-400" />
                <span>AI Game Outlook & Deep Tactical Prediction</span>
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

          {/* CATEGORIZED SPORTYBET BETTING MARKETS SECTION */}
          {allMarkets.length > 0 && (
            <div className="space-y-4 pt-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <h3 className="text-sm uppercase font-bold text-gray-300 tracking-wider">
                  SportyBet Options & Markets ({filteredMarkets.length})
                </h3>

                {/* Market Category Filter Tabs */}
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs font-semibold">
                  {[
                    { id: "all", label: "All" },
                    { id: "corners", label: "🚩 Corners" },
                    { id: "cards", label: "🟨 Cards" },
                    { id: "goals", label: "⚽ Goals" },
                    { id: "btts", label: "GG/NG" },
                    { id: "handicap", label: "⚖️ Handicap" },
                    { id: "1x2", label: "🏆 1X2 & DC" },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setMarketFilter(tab.id)}
                      className={`px-3 py-1.5 rounded-lg transition whitespace-nowrap text-xs ${
                        marketFilter === tab.id
                          ? "bg-emerald-500 text-gray-950 font-extrabold shadow-sm"
                          : "text-gray-300 hover:text-white bg-gray-900 border border-gray-800"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Markets Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {filteredMarkets.length === 0 ? (
                  <div className="col-span-2 py-8 text-center text-xs text-gray-500 bg-gray-900/30 rounded-xl border border-gray-800">
                    No options found for this category on SportyBet.
                  </div>
                ) : (
                  filteredMarkets.map((m, idx) => {
                    const inSlip = legs.some(
                      (l) => l.match_id === match.id && l.selection === m.selection
                    );
                    return (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl bg-gray-900/60 border border-gray-800/80 hover:border-gray-700 flex items-center justify-between transition"
                      >
                        <div className="flex-1 pr-3">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-mono text-emerald-400 uppercase px-1.5 py-0.5 rounded bg-emerald-950/60 border border-emerald-900/60">
                              {m.market}
                            </span>
                          </div>
                          <p className="font-bold text-white text-xs mt-1">{m.selection}</p>
                          <p className="text-[11px] text-gray-400 font-mono mt-0.5">
                            Prob: <span className="text-white font-semibold">{(m.probability * 100).toFixed(0)}%</span> • Odds:{" "}
                            <span className="text-emerald-400 font-extrabold font-mono">{m.odds.toFixed(2)}</span>
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
                              event_id: m.event_id,
                              market_id: m.market_id,
                              outcome_id: m.outcome_id,
                              specifier: m.specifier,
                            })
                          }
                          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1 ${
                            inSlip
                              ? "bg-gray-800 text-emerald-400 border border-emerald-500/40"
                              : "bg-gray-800 hover:bg-emerald-500 hover:text-gray-950 text-white border border-gray-700"
                          }`}
                        >
                          {inSlip ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                          <span>{inSlip ? "Added" : "+ Slip"}</span>
                        </button>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
