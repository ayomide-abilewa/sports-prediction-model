"use client";

import React from "react";
import { Layers, Plus } from "lucide-react";
import { useSlip } from "./SlipContext";

export interface AccumulatorSlipProps {
  slip: {
    category: string;
    slip_name: string;
    combined_odds: number;
    joint_probability: number;
    expected_return: number;
    risk_class: string;
    leg_count: number;
    legs: Array<{
      match_id: number;
      fixture: string;
      market: string;
      selection: string;
      odds: number;
      probability: number;
      expected_value?: number;
      kickoff?: string;
    }>;
  };
}

export default function AccumulatorCard({ slip }: AccumulatorSlipProps) {
  const { addLeg, setIsOpen } = useSlip();
  const handleLoadAllToBuilder = () => {
    slip.legs.forEach((leg) => {
      addLeg({
        match_id: leg.match_id,
        fixture: leg.fixture,
        market: leg.market,
        selection: leg.selection,
        odds: leg.odds,
        probability: leg.probability,
        kickoff: leg.kickoff,
      });
    });
    setIsOpen(true);
  };

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
      {/* Top Slip Header */}
      <div className="bg-gray-900/90 px-6 py-5 border-b border-gray-800 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-extrabold text-white text-base sm:text-lg">{slip.slip_name}</h3>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono font-bold">
              {slip.risk_class}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {slip.leg_count} Matches • Cross-league correlation checked • Kelly-optimized
          </p>
        </div>

        <div className="flex items-center gap-6">
          <div className="text-right">
            <p className="text-[11px] text-gray-400 uppercase tracking-wider">Combined Odds</p>
            <p className="text-2xl font-black text-emerald-400 font-mono">{slip.combined_odds.toFixed(2)}x</p>
          </div>
          <div className="text-right">
            <p className="text-[11px] text-gray-400 uppercase tracking-wider">Joint Win Prob</p>
            <p className="text-2xl font-black text-white font-mono">{(slip.joint_probability * 100).toFixed(1)}%</p>
          </div>
          <div className="text-right">
            <p className="text-[11px] text-gray-400 uppercase tracking-wider">Edge (EV)</p>
            <p className="text-2xl font-black text-purple-400 font-mono">+{(slip.expected_return * 100).toFixed(1)}%</p>
          </div>
        </div>
      </div>

      {/* Suggested slip actions */}
      <div className="bg-emerald-950/20 border-b border-gray-800 px-6 py-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-emerald-300">Suggested picks</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleLoadAllToBuilder}
            className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 font-semibold text-xs border border-gray-700 transition flex items-center gap-1.5"
          >
            <Layers className="h-3.5 w-3.5 text-purple-400" />
            <span>Load in My Slip Builder</span>
          </button>
        </div>
      </div>

      {/* Slip Legs */}
      <div className="divide-y divide-gray-800/60">
        {slip.legs.map((leg, lIndex) => (
          <div
            key={lIndex}
            className="px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-gray-800/30 transition text-sm"
          >
            <div className="flex items-center gap-3">
              <span className="h-7 w-7 rounded-full bg-gray-800 text-gray-300 font-mono text-xs flex items-center justify-center font-bold">
                {lIndex + 1}
              </span>
              <div>
                <p className="font-bold text-white text-sm sm:text-base">{leg.fixture}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs font-mono text-gray-400 uppercase">{leg.market}:</span>
                  <span className="text-xs font-black text-emerald-400 capitalize">{leg.selection}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-6 sm:text-right">
              <div>
                <p className="text-[11px] text-gray-400">Model Probability</p>
                <p className="font-mono text-xs text-gray-300 font-semibold">{(leg.probability * 100).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-[11px] text-gray-400">Available Odds</p>
                <p className="font-mono text-base font-extrabold text-white">{leg.odds.toFixed(2)}</p>
              </div>
              <button
                onClick={() =>
                  addLeg({
                    match_id: leg.match_id,
                    fixture: leg.fixture,
                    market: leg.market,
                    selection: leg.selection,
                    odds: leg.odds,
                    probability: leg.probability,
                    kickoff: leg.kickoff,
                  })
                }
                className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-emerald-400 transition"
                title="Add individual leg to custom slip"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
