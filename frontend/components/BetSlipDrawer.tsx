"use client";

import React, { useState } from "react";
import { useSlip } from "./SlipContext";
import { Check, Copy, Flame, Layers, Trash2, X } from "lucide-react";

export default function BetSlipDrawer() {
  const {
    legs,
    removeLeg,
    clearSlip,
    combinedOdds,
    jointProbability,
    bookingCode,
    generateBookingCode,
    isOpen,
    setIsOpen,
  } = useSlip();

  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleCopy = () => {
    if (bookingCode) {
      navigator.clipboard.writeText(bookingCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    await generateBookingCode();
    setLoading(false);
  };

  return (
    <>
      {/* Floating Bottom-Right Trigger Button */}
      {legs.length > 0 && !isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 px-5 py-3 rounded-full bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-extrabold text-sm shadow-2xl shadow-emerald-500/50 flex items-center gap-3 transition-transform transform hover:scale-105"
        >
          <Layers className="h-5 w-5" />
          <span>Slip ({legs.length})</span>
          <span className="bg-gray-950 text-emerald-400 px-2 py-0.5 rounded-full text-xs font-mono">
            {combinedOdds.toFixed(2)}x
          </span>
        </button>
      )}

      {/* Slip Slide-Over Drawer */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md bg-[#0e1626] border-l border-gray-800 h-full flex flex-col justify-between shadow-2xl p-6 overflow-y-auto">
            {/* Header */}
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-gray-800">
                <div className="flex items-center gap-2">
                  <Layers className="h-5 w-5 text-emerald-400" />
                  <h2 className="text-lg font-bold text-white">Bet Slip Builder</h2>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono font-bold">
                    {legs.length} Picks
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {legs.length > 0 && (
                    <button
                      onClick={clearSlip}
                      className="text-xs text-gray-400 hover:text-red-400 flex items-center gap-1 transition"
                      title="Clear slip"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      <span>Clear</span>
                    </button>
                  )}
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-1 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>

              {/* Legs List */}
              <div className="py-4 space-y-3">
                {legs.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <p className="text-sm font-medium">Your bet slip is empty</p>
                    <p className="text-xs mt-1">Click "+ Add to Slip" on any game to start combining odds.</p>
                  </div>
                ) : (
                  legs.map((leg, i) => (
                    <div
                      key={i}
                      className="p-3.5 rounded-xl bg-gray-900/90 border border-gray-800 hover:border-gray-700 transition flex items-start justify-between gap-3"
                    >
                      <div className="flex-1">
                        <p className="font-semibold text-white text-xs">{leg.fixture}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs font-mono text-gray-400 uppercase">{leg.market}:</span>
                          <span className="text-xs font-bold text-emerald-400 capitalize">{leg.selection}</span>
                        </div>
                        <p className="text-[11px] text-gray-500 mt-1 font-mono">
                          Est. Win Prob: {(leg.probability * 100).toFixed(0)}%
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <span className="font-bold text-sm text-white font-mono">{leg.odds.toFixed(2)}</span>
                        <button
                          onClick={() => removeLeg(leg.match_id, leg.market, leg.selection)}
                          className="text-gray-500 hover:text-red-400 transition"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Footer Summary & Booking Code Action */}
            {legs.length > 0 && (
              <div className="pt-4 border-t border-gray-800 space-y-4">
                <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-800 space-y-2">
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>Combined Odds</span>
                    <span className="font-mono font-bold text-emerald-400 text-base">{combinedOdds.toFixed(2)}x</span>
                  </div>
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>Est. Combined Probability</span>
                    <span className="font-mono font-medium text-white">{(jointProbability * 100).toFixed(1)}%</span>
                  </div>
                </div>

                {/* Booking Code Display */}
                {bookingCode ? (
                  <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/50 space-y-2 text-center animate-fade-in">
                    <p className="text-xs text-emerald-300 font-semibold uppercase tracking-wider flex items-center justify-center gap-1.5">
                      <Flame className="h-4 w-4 text-emerald-400" />
                      <span>SportyBet Booking Code</span>
                    </p>
                    <div className="flex items-center justify-center gap-3">
                      <span className="font-mono text-2xl font-black text-white tracking-widest bg-gray-950 px-4 py-1.5 rounded-lg border border-emerald-500/40">
                        {bookingCode}
                      </span>
                      <button
                        onClick={handleCopy}
                        className="p-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-bold transition flex items-center gap-1.5 text-xs"
                      >
                        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        <span>{copied ? "Copied" : "Copy"}</span>
                      </button>
                    </div>
                    <p className="text-[11px] text-gray-400 mt-1">
                      Paste this code into SportyBet / Bet9ja to load this exact slip.
                    </p>
                  </div>
                ) : (
                  <button
                    onClick={handleGenerate}
                    disabled={loading}
                    className="w-full py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-extrabold text-sm shadow-lg shadow-emerald-500/20 transition flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {loading ? (
                      <span>Generating Code...</span>
                    ) : (
                      <>
                        <Flame className="h-4 w-4" />
                        <span>Generate Booking Code (SportyBet)</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
