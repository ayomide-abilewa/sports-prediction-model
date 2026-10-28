"use client";

import React, { useState } from "react";

export interface LiveMatchItem {
  match_id: number;
  fixture: string;
  home_team: string;
  away_team: string;
  league: string;
  kickoff: string | null;
  status: string;
  live_minute: number | null;
  period: string;
  score: {
    home: number;
    away: number;
  };
  live_stats: {
    possession_home: number | null;
    shots_on_target_home: number | null;
    shots_on_target_away: number | null;
    corners_home: number | null;
    corners_away: number | null;
    cards_home: number | null;
    cards_away: number | null;
    red_cards_home: number | null;
    red_cards_away: number | null;
  };
  surest_in_play_pick?: {
    market: string;
    selection: string;
    probability: number;
    live_odds: number | null;
    fair_odds?: number;
    confidence_tier: string;
  };
  top_in_play_picks?: Array<{
    market: string;
    selection: string;
    probability: number;
    live_odds: number | null;
    fair_odds?: number;
    confidence_tier: string;
  }>;
  live_narrative?: string;
  remaining_projected_xg?: {
    home: number;
    away: number;
    total: number;
  };
  next_goal_probabilities?: {
    home: number;
    away: number;
    no_more_goals: number;
  };
  all_live_markets?: Array<{
    market: string;
    selection: string;
    probability: number;
    live_odds: number | null;
    fair_odds?: number;
    confidence_tier: string;
  }>;
}

export default function LiveMatchesSection({ matches }: { matches: LiveMatchItem[] }) {
  const [activeMatchId, setActiveMatchId] = useState<number>(matches[0]?.match_id || 0);

  if (!matches || matches.length === 0) {
    return null;
  }

  const activeMatch = matches.find((m) => m.match_id === activeMatchId) || matches[0];
  const surest = activeMatch.surest_in_play_pick;

  return (
    <div className="bg-[#0e1626] border border-red-500/30 rounded-2xl p-6 shadow-2xl relative overflow-hidden space-y-6">
      {/* Background Live Glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-red-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="relative flex h-3.5 w-3.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-red-500"></span>
          </span>
          <div>
            <h2 className="text-xl font-black text-white flex items-center gap-2">
              <span>Live Match Data & Model Outlook</span>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-red-950 text-red-400 border border-red-800 font-mono font-bold">
                {matches.length} Matches Live
              </span>
            </h2>
            <p className="text-xs text-gray-400">
              Live scores and provider-supplied match statistics. Model outlooks are uncalibrated and shown only when a live clock is available.
            </p>
          </div>
        </div>

        {/* Live Match Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 max-w-full">
          {matches.map((m) => (
            <button
              key={m.match_id}
              onClick={() => setActiveMatchId(m.match_id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition whitespace-nowrap flex items-center gap-2 ${
                m.match_id === activeMatch.match_id
                  ? "bg-red-500 text-white shadow-md shadow-red-500/30"
                  : "bg-gray-900 text-gray-400 hover:text-white border border-gray-800"
              }`}
            >
              <span>{m.fixture}</span>
              <span className="font-mono text-[11px] bg-black/40 px-1.5 py-0.5 rounded">
                {m.score.home}-{m.score.away}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Active Live Match Spotlight Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Live Scoreboard & In-Game Stats */}
        <div className="lg:col-span-1 bg-gray-900/90 border border-gray-800 rounded-2xl p-5 flex flex-col justify-between space-y-5">
          <div>
            <div className="flex items-center justify-between text-xs mb-3">
              <span className="px-2.5 py-0.5 rounded-full bg-gray-800 text-gray-300 font-semibold text-[11px]">
                {activeMatch.league}
              </span>
              <div className="flex items-center gap-1.5 text-red-400 font-mono font-bold text-xs bg-red-950/60 border border-red-900/60 px-2.5 py-0.5 rounded-full">
                <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
                <span>{activeMatch.live_minute == null ? activeMatch.period : `${activeMatch.live_minute}' (${activeMatch.period})`}</span>
              </div>
            </div>

            {/* Live Score Big Display */}
            <div className="text-center py-4 bg-gray-950/60 rounded-xl border border-gray-800/80">
              <div className="grid grid-cols-3 items-center">
                <p className="font-black text-white text-base truncate px-2">{activeMatch.home_team}</p>
                <div className="font-mono font-black text-3xl sm:text-4xl text-emerald-400 tracking-wider">
                  {activeMatch.score.home} - {activeMatch.score.away}
                </div>
                <p className="font-black text-white text-base truncate px-2">{activeMatch.away_team}</p>
              </div>
            </div>
          </div>

          {/* In-Game Match Statistics */}
          <div className="space-y-3 text-xs">
            <h4 className="font-bold text-gray-400 uppercase tracking-wider text-[11px]">
              Live In-Game Match Stats
            </h4>

            {/* Possession Bar */}
            <div>
              <div className="flex justify-between text-[11px] text-gray-300 font-mono mb-1">
                <span>{activeMatch.live_stats.possession_home == null ? "—" : `${activeMatch.live_stats.possession_home}%`}</span>
                <span className="text-gray-500">Possession</span>
                <span>{activeMatch.live_stats.possession_home == null ? "—" : `${100 - activeMatch.live_stats.possession_home}%`}</span>
              </div>
              <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden flex">
                <div
                  className="bg-emerald-500 h-full"
                  style={{ width: `${activeMatch.live_stats.possession_home ?? 0}%` }}
                />
                <div
                  className="bg-blue-500 h-full"
                  style={{ width: `${activeMatch.live_stats.possession_home == null ? 0 : 100 - activeMatch.live_stats.possession_home}%` }}
                />
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-3 gap-2 text-center pt-2">
              <div className="p-2 rounded-lg bg-gray-950/60 border border-gray-800">
                <p className="text-[10px] text-gray-400 uppercase">Shots On Target</p>
                <p className="font-mono font-bold text-white text-sm mt-0.5">
                  {activeMatch.live_stats.shots_on_target_home ?? "—"} - {activeMatch.live_stats.shots_on_target_away ?? "—"}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-gray-950/60 border border-gray-800">
                <p className="text-[10px] text-gray-400 uppercase">Corners</p>
                <p className="font-mono font-bold text-emerald-400 text-sm mt-0.5">
                  {activeMatch.live_stats.corners_home ?? "—"} - {activeMatch.live_stats.corners_away ?? "—"}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-gray-950/60 border border-gray-800">
                <p className="text-[10px] text-gray-400 uppercase">Yellow Cards</p>
                <p className="font-mono font-bold text-amber-400 text-sm mt-0.5">
                  {activeMatch.live_stats.cards_home ?? "—"} - {activeMatch.live_stats.cards_away ?? "—"}
                </p>
              </div>
            </div>

            {/* Next Goal Probability Bar */}
            {activeMatch.next_goal_probabilities && (
              <div className="p-2.5 rounded-lg bg-gray-950/60 border border-gray-800 space-y-1">
                <p className="text-[10px] font-bold text-gray-400 uppercase">Next goal model estimate:</p>
                <div className="flex justify-between text-[11px] font-mono">
                  <span className="text-emerald-400">
                    {activeMatch.home_team}: {(activeMatch.next_goal_probabilities.home * 100).toFixed(0)}%
                  </span>
                  <span className="text-gray-400">
                    No Goal: {(activeMatch.next_goal_probabilities.no_more_goals * 100).toFixed(0)}%
                  </span>
                  <span className="text-blue-400">
                    {activeMatch.away_team}: {(activeMatch.next_goal_probabilities.away * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Live model forecast. The platform does not receive verified in-play prices. */}
        <div className="lg:col-span-2 space-y-4 flex flex-col justify-between">
          {/* AI In-Play Highlight Banner */}
          {surest && (
            <div className="p-5 rounded-2xl bg-gradient-to-r from-red-950/40 via-gray-900 to-emerald-950/30 border border-red-500/40 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-500/20 text-red-300 text-xs font-black uppercase tracking-wider">
                  <span>UNPRICED MODEL OUTLOOK</span>
                </span>
                <span className="text-xs font-mono text-emerald-400 font-bold">{surest.confidence_tier}</span>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <p className="text-xs text-gray-400 font-mono uppercase">{surest.market}</p>
                  <p className="text-2xl font-black text-white">{surest.selection}</p>
                  <p className="text-xs text-emerald-400 font-mono mt-0.5">
                    Model estimate: <span className="font-extrabold text-white">{(surest.probability * 100).toFixed(1)}%</span>
                    {surest.fair_odds != null && <> · Model fair price: <span className="font-extrabold text-white">{surest.fair_odds.toFixed(2)}</span></>}
                  </p>
                </div>

                {/* Live Narrative */}
                {activeMatch.live_narrative && (
                  <p className="text-xs text-gray-300 leading-relaxed border-t border-gray-800/80 pt-2.5">
                    <span className="font-bold text-white">Model note:</span> {activeMatch.live_narrative}
                  </p>
                )}
              </div>
            </div>
            )}
          {!surest && (
            <div className="p-5 rounded-2xl bg-gray-900 border border-gray-800 text-sm text-gray-300">
              {activeMatch.live_narrative || "No supported live forecast is available for this match."} No bookmaker price is supplied, so there is no bet button.
            </div>
          )}
          </div>
        </div>
      </div>
    );
}
