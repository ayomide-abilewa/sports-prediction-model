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
  event_id?: string;
  market_id?: string;
  outcome_id?: string;
  specifier?: string;
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
  best_prop?: SurestPickItem;
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
  const [activeTab, setActiveTab] = useState<"upcoming" | "finished" | "live">("upcoming");
  const [selectedLeague, setSelectedLeague] = useState<string>("all");

  const liveMatches = fixtures.filter((f) => f.status === "in_play");

  const filtered = fixtures.filter((f) => {
    let matchTab = false;
    if (activeTab === "live") {
      matchTab = f.status === "in_play";
    } else if (activeTab === "upcoming") {
      matchTab = f.status === "scheduled" && new Date(f.kickoff).getTime() > Date.now();
    } else {
      matchTab = f.status === "finished" || (f.status !== "in_play" && new Date(f.kickoff).getTime() <= Date.now());
    }
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
          {liveMatches.length > 0 && (
            <button
              onClick={() => setActiveTab("live")}
              className={`px-4 py-2 rounded-xl font-bold text-sm transition flex items-center gap-2 ${
                activeTab === "live"
                  ? "bg-red-500 text-white shadow-md shadow-red-500/30 font-black"
                  : "bg-red-950/40 text-red-300 hover:text-white hover:bg-red-900/40 border border-red-800/60"
              }`}
            >
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
              </span>
              <span>Live In-Play ({liveMatches.length})</span>
            </button>
          )}
          <button
            onClick={() => setActiveTab("upcoming")}
            className={`px-4 py-2 rounded-xl font-bold text-sm transition flex items-center gap-2 ${
              activeTab === "upcoming"
                ? "bg-emerald-500 text-gray-950 shadow-md shadow-emerald-500/20"
                : "bg-gray-900 text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
          >
            <Clock className="h-4 w-4" />
            <span>Upcoming Games</span>
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
                    {match.status === "in_play" ? (
                      <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-red-950 text-red-400 border border-red-800 font-mono font-bold text-[11px]">
                        <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
                        <span>LIVE IN-PLAY</span>
                      </span>
                    ) : (
                      <span className="text-gray-400 font-mono text-[11px]">{dateStr}</span>
                    )}
                  </div>

                  <h3 className="font-extrabold text-white text-base sm:text-lg">
                    {match.home_team} <span className="text-gray-500 font-normal">vs</span> {match.away_team}
                  </h3>

                  {match.status === "in_play" ? (
                    <div className="inline-flex items-center gap-2 mt-1 px-3 py-1 rounded-lg bg-red-950/40 border border-red-800/80">
                      <span className="text-xs font-black text-white font-mono">
                        Live Score: {match.ft_home_goals ?? 0} - {match.ft_away_goals ?? 0}
                      </span>
                    </div>
                  ) : match.status === "finished" ? (
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

                {/* THE ONE SUREST PREDICTION */}
                {match.surest_prediction ? (
                  <div className="bg-gradient-to-br from-emerald-950/40 via-gray-900 to-gray-950 rounded-xl p-4 border border-emerald-500/40 shadow-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-extrabold uppercase tracking-wider">
                        <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                        <span>Surest Pick to Carry</span>
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold">
                        {match.surest_prediction.confidence_tier || "Bankers Tier"}
                      </span>
                    </div>

                    <div>
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-[10px] font-mono uppercase text-gray-400 px-1.5 py-0.5 rounded bg-gray-900 border border-gray-800">
                            {match.surest_prediction.market}
                          </span>
                          <h4 className="font-black text-white text-base sm:text-lg mt-1">
                            {match.surest_prediction.selection}
                          </h4>
                        </div>
                        <div className="text-right">
                          <span className="text-xs text-gray-400 font-mono block">Sporty Odds</span>
                          <span className="text-lg font-black text-white font-mono">
                            {match.surest_prediction.odds.toFixed(2)}
                          </span>
                        </div>
                      </div>

                      {/* Conviction Bar */}
                      <div className="mt-2.5">
                        <div className="flex justify-between text-[11px] font-mono text-gray-400 mb-1">
                          <span>Model Win Probability</span>
                          <span className="text-emerald-400 font-bold">
                            {(match.surest_prediction.prob * 100).toFixed(0)}% Conviction
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                            style={{ width: `${Math.min(100, Math.max(10, match.surest_prediction.prob * 100))}%` }}
                          />
                        </div>
                      </div>

                      {/* Rationale */}
                      {match.surest_prediction.rationale && (
                        <p className="text-xs text-gray-300 mt-2.5 leading-relaxed bg-gray-950/60 p-2.5 rounded-lg border border-gray-800/80">
                          {match.surest_prediction.rationale}
                        </p>
                      )}
                    </div>

                    {/* Single Clean Add Button */}
                    {(() => {
                      const inSlip = legs.some(
                        (l) => l.match_id === match.id && l.selection === match.surest_prediction?.selection
                      );
                      return (
                        <button
                          onClick={() => {
                            if (match.surest_prediction) {
                              addLeg({
                                match_id: match.id,
                                fixture: match.fixture,
                                market: match.surest_prediction.market,
                                selection: match.surest_prediction.selection,
                                odds: match.surest_prediction.odds,
                                probability: match.surest_prediction.prob,
                                event_id: match.surest_prediction.event_id,
                                market_id: match.surest_prediction.market_id,
                                outcome_id: match.surest_prediction.outcome_id,
                                specifier: match.surest_prediction.specifier,
                              });
                            }
                          }}
                          className={`w-full py-2.5 rounded-xl font-extrabold text-xs transition flex items-center justify-center gap-2 ${
                            inSlip
                              ? "bg-gray-800 text-emerald-400 border border-emerald-500/50"
                              : "bg-emerald-500 hover:bg-emerald-400 text-gray-950 shadow-md shadow-emerald-500/20"
                          }`}
                        >
                          {inSlip ? (
                            <>
                              <Check className="h-4 w-4" />
                              <span>Surest Pick Added to Slip</span>
                            </>
                          ) : (
                            <>
                              <Plus className="h-4 w-4" />
                              <span>+ Add Surest Pick to Slip</span>
                            </>
                          )}
                        </button>
                      );
                    })()}
                  </div>
                ) : (
                  <div className="py-4 text-center text-xs text-gray-500">
                    Poisson simulation computing match distributions...
                  </div>
                )}

                {/* 🔥 THE ONE BEST PROP (Corners / Cards / 1H) */}
                {match.best_prop && (
                  <div className="bg-gradient-to-br from-amber-950/20 via-gray-900 to-gray-950 rounded-xl p-3.5 border border-amber-500/30 shadow-md space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center gap-1.5 text-xs text-amber-400 font-extrabold uppercase tracking-wider">
                        <Flame className="h-3.5 w-3.5 text-amber-400" />
                        <span>Best Prop Selection</span>
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-800 font-bold">
                        {match.best_prop.confidence_tier || "Sharp Prop"}
                      </span>
                    </div>

                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <span className="text-[10px] font-mono uppercase text-gray-400 px-1.5 py-0.5 rounded bg-gray-900 border border-gray-800">
                          {match.best_prop.market}
                        </span>
                        <h5 className="font-extrabold text-white text-sm mt-0.5">
                          {match.best_prop.selection}
                        </h5>
                        <p className="text-[11px] font-mono text-amber-400 mt-0.5">
                          Model Prob: <span className="text-white font-bold">{(match.best_prop.prob * 100).toFixed(1)}%</span>
                        </p>
                      </div>

                      <div className="flex flex-col items-end gap-1.5">
                        <span className="text-base font-black text-white font-mono">
                          @{match.best_prop.odds.toFixed(2)}
                        </span>
                        {(() => {
                          const propInSlip = legs.some(
                            (l) => l.match_id === match.id && l.selection === match.best_prop?.selection
                          );
                          return (
                            <button
                              onClick={() => {
                                if (match.best_prop) {
                                  addLeg({
                                    match_id: match.id,
                                    fixture: match.fixture,
                                    market: match.best_prop.market,
                                    selection: match.best_prop.selection,
                                    odds: match.best_prop.odds,
                                    probability: match.best_prop.prob,
                                    event_id: match.best_prop.event_id,
                                    market_id: match.best_prop.market_id,
                                    outcome_id: match.best_prop.outcome_id,
                                    specifier: match.best_prop.specifier,
                                  });
                                }
                              }}
                              className={`px-3 py-1.5 rounded-lg font-bold text-xs transition flex items-center gap-1 ${
                                propInSlip
                                  ? "bg-gray-800 text-amber-400 border border-amber-500/50"
                                  : "bg-amber-500 hover:bg-amber-400 text-gray-950 font-black shadow-md shadow-amber-500/20"
                              }`}
                            >
                              {propInSlip ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                              <span>{propInSlip ? "In Slip" : "+ Prop"}</span>
                            </button>
                          );
                        })()}
                      </div>
                    </div>
                  </div>
                )}

                {/* Card Action Footer */}
                <div className="flex items-center justify-between pt-2 border-t border-gray-800/60">
                  <button
                    onClick={() => setSelectedMatch(match as any)}
                    className="text-xs font-bold text-gray-300 hover:text-white flex items-center gap-1.5 transition py-1"
                  >
                    <Activity className="h-3.5 w-3.5 text-emerald-400" />
                    <span>View All Markets (Corners, Cards, Handicaps)</span>
                  </button>
                  <span className="text-[11px] font-mono text-gray-500">
                    SportyBet Live Odds
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
