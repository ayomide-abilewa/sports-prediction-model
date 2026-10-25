"use client";

import React, { useState } from "react";
import { useSlip } from "./SlipContext";
import MatchDetailModal, { MatchAnalysisData } from "./MatchDetailModal";
import { Activity, Check, Clock, Flame, Layers, Plus, Sparkles, Trophy, Zap } from "lucide-react";

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

export interface FixtureItem {
  id: number;
  fixture: string;
  home_team: string;
  away_team: string;
  league: string;
  league_code?: string;
  kickoff: string;
  status: string;
  ft_home_goals?: number;
  ft_away_goals?: number;
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

export default function MatchList({ fixtures }: { fixtures: FixtureItem[] }) {
  const { addLeg, legs, setIsOpen } = useSlip();
  const [selectedMatch, setSelectedMatch] = useState<MatchAnalysisData | null>(null);
  const [activeTab, setActiveTab] = useState<"upcoming" | "finished">("upcoming");
  const [selectedLeague, setSelectedLeague] = useState<string>("all");

  const filtered = fixtures.filter((f) => {
    const isSched = f.status === "scheduled";
    const matchTab = activeTab === "upcoming" ? isSched : !isSched;
    const matchLeague = selectedLeague === "all" || f.league === selectedLeague;
    return matchTab && matchLeague;
  });

  const leagues = Array.from(new Set(fixtures.map((f) => f.league).filter(Boolean)));

  const handleMixSurestPicks = (match: FixtureItem) => {
    const picks = match.top_surest_picks || (match.surest_prediction ? [match.surest_prediction] : []);
    picks.forEach((p) => {
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
    <div className="space-y-6">
      {/* Tab Filter Navigation */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-gray-800 pb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab("upcoming")}
            className={`px-4 py-2 rounded-xl font-bold text-sm transition flex items-center gap-2 ${
              activeTab === "upcoming"
                ? "bg-emerald-500 text-gray-950 shadow-md shadow-emerald-500/20"
                : "bg-gray-900 text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
          >
            <Clock className="h-4 w-4" />
            <span>Today & Upcoming Games</span>
          </button>
          <button
            onClick={() => setActiveTab("finished")}
            className={`px-4 py-2 rounded-xl font-bold text-sm transition flex items-center gap-2 ${
              activeTab === "finished"
                ? "bg-emerald-500 text-gray-950 shadow-md shadow-emerald-500/20"
                : "bg-gray-900 text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
          >
            <Trophy className="h-4 w-4" />
            <span>Completed Matches</span>
          </button>
        </div>

        {/* League Selector */}
        {leagues.length > 0 && (
          <div className="flex items-center gap-1.5 overflow-x-auto max-w-full pb-1 scrollbar-thin">
            <button
              onClick={() => setSelectedLeague("all")}
              className={`px-3 py-1 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                selectedLeague === "all"
                  ? "bg-emerald-500 text-gray-950 font-bold"
                  : "text-gray-400 hover:text-white bg-gray-900/60 border border-gray-800"
              }`}
            >
              All Competitions ({fixtures.length})
            </button>
            {leagues.map((l) => (
              <button
                key={l}
                onClick={() => setSelectedLeague(l)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                  selectedLeague === l
                    ? "bg-emerald-500 text-gray-950 font-bold"
                    : "text-gray-400 hover:text-white bg-gray-900/60 border border-gray-800"
                }`}
              >
                {l}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Matches Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {filtered.length === 0 ? (
          <div className="col-span-full py-12 text-center text-gray-500 bg-[#111827] border border-gray-800 rounded-2xl">
            <Clock className="h-8 w-8 mx-auto mb-2 text-gray-600" />
            <p className="font-semibold text-white">No matches found in this view</p>
            <p className="text-xs text-gray-400 mt-1">Switch to "Today & Upcoming Games" or select "All Competitions".</p>
          </div>
        ) : (
          filtered.map((match) => {
            const surestPicks = match.top_surest_picks || (match.surest_prediction ? [match.surest_prediction] : []);
            const dateStr = new Date(match.kickoff).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "short",
              hour: "2-digit",
              minute: "2-digit",
            });

            return (
              <div
                key={match.id}
                className="bg-[#111827] border border-gray-800/90 hover:border-gray-700 rounded-2xl p-5 transition flex flex-col justify-between gap-4 shadow-xl"
              >
                {/* Match Header */}
                <div>
                  <div className="flex items-center justify-between text-xs mb-2">
                    <span className="font-semibold text-emerald-400 bg-emerald-950/40 border border-emerald-900/60 px-2.5 py-0.5 rounded-full">
                      {match.league}
                    </span>
                    <span className="text-gray-400 font-mono text-[11px]">{dateStr}</span>
                  </div>

                  <h3 className="font-extrabold text-white text-base sm:text-lg">
                    {match.home_team} <span className="text-gray-500 font-normal">vs</span> {match.away_team}
                  </h3>

                  {match.status === "finished" ? (
                    <span className="inline-block mt-1 font-mono text-xs px-2.5 py-0.5 rounded bg-gray-900 text-emerald-400 border border-gray-800">
                      Final Score: {match.ft_home_goals} - {match.ft_away_goals}
                    </span>
                  ) : (
                    match.expected_goals && (
                      <p className="text-[11px] text-gray-400 mt-1 font-mono">
                        Proj. xG: <span className="text-white font-bold">{match.expected_goals.home}</span> vs{" "}
                        <span className="text-white font-bold">{match.expected_goals.away}</span> (Total: {match.expected_goals.total})
                      </p>
                    )
                  )}
                </div>

                {/* AI TOP SUREST PREDICTIONS (MULTIPLE PICKS) */}
                {surestPicks.length > 0 && (
                  <div className="space-y-2 bg-gray-900/80 rounded-xl p-3.5 border border-emerald-500/30">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-bold uppercase tracking-wider">
                        <Sparkles className="h-3.5 w-3.5" />
                        <span>Surest Predictions ({surestPicks.length} High Conviction)</span>
                      </div>
                      <button
                        onClick={() => handleMixSurestPicks(match)}
                        className="text-[11px] font-bold text-emerald-300 hover:text-emerald-200 bg-emerald-950/80 hover:bg-emerald-900/80 border border-emerald-800 px-2.5 py-1 rounded-lg transition flex items-center gap-1"
                        title="Add all high conviction picks to your slip"
                      >
                        <Zap className="h-3 w-3 text-emerald-400" />
                        <span>Mix All Picks</span>
                      </button>
                    </div>

                    <div className="space-y-1.5 pt-1">
                      {surestPicks.map((pick, pIdx) => {
                        const inSlip = legs.some(
                          (l) => l.match_id === match.id && l.selection === pick.selection
                        );
                        return (
                          <div
                            key={pIdx}
                            className="flex items-center justify-between text-xs p-2 rounded-lg bg-gray-950/60 border border-gray-800/80 hover:border-gray-700 transition"
                          >
                            <div className="flex-1 pr-2">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-mono uppercase text-gray-400 px-1.5 py-0.5 rounded bg-gray-900 border border-gray-800">
                                  {pick.market}
                                </span>
                                <span className="font-bold text-white text-xs">{pick.selection}</span>
                              </div>
                              <p className="text-[11px] text-gray-400 font-mono mt-0.5">
                                Prob: <span className="text-emerald-400 font-semibold">{(pick.prob * 100).toFixed(0)}%</span> • Odds:{" "}
                                <span className="text-white font-bold">{pick.odds.toFixed(2)}</span>
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
                              className={`px-2.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1 ${
                                inSlip
                                  ? "bg-gray-800 text-emerald-400 border border-emerald-500/40"
                                  : "bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-extrabold shadow-sm"
                              }`}
                            >
                              {inSlip ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                              <span>{inSlip ? "Added" : "+ Slip"}</span>
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Card Action Footer */}
                <div className="flex items-center justify-between pt-2 border-t border-gray-800/60">
                  <button
                    onClick={() => setSelectedMatch(match as any)}
                    className="text-xs font-bold text-gray-300 hover:text-white flex items-center gap-1.5 transition"
                  >
                    <Activity className="h-3.5 w-3.5 text-emerald-400" />
                    <span>View All Markets & AI Outlook</span>
                  </button>
                  <span className="text-[11px] font-mono text-gray-500">
                    {match.markets?.length || 15}+ Markets Modeled
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Match Analysis Detail Modal */}
      <MatchDetailModal match={selectedMatch} onClose={() => setSelectedMatch(null)} />
    </div>
  );
}
