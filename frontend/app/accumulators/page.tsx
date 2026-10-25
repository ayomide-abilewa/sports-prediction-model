import React from "react";
import Link from "next/link";
import { Check, Flame, Layers, ShieldCheck, Sparkles, Trophy } from "lucide-react";

async function getAccumulators(category: string) {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/v1/accumulators?category=${category}`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

export default async function AccumulatorsPage({
  searchParams,
}: {
  searchParams?: { category?: string };
}) {
  const currentCategory = searchParams?.category || "solid_core";
  const slips = await getAccumulators(currentCategory);

  const categories = [
    { id: "banker_rollover", name: "Banker Rollover", odds: "2.0x - 2.5x", icon: ShieldCheck, color: "text-emerald-400" },
    { id: "solid_core", name: "Solid Core Multiplier", odds: "5.0x - 7.0x", icon: Trophy, color: "text-blue-400" },
    { id: "sharp_multi", name: "Sharp Multi-League", odds: "12x - 20x", icon: Sparkles, color: "text-purple-400" },
    { id: "high_yield", name: "Weekend High-Yield", odds: "40x - 100x+", icon: Flame, color: "text-amber-400" },
  ];

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Accumulator & Combination Engine</h1>
        <p className="text-gray-400 text-sm mt-1">
          Constraint-optimized accumulator slips with correlation detection and mathematical edge ranking.
        </p>
      </div>

      {/* Product Category Selector Tabs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const isActive = cat.id === currentCategory;
          return (
            <Link
              key={cat.id}
              href={`/accumulators?category=${cat.id}`}
              className={`p-4 rounded-xl border text-left transition flex flex-col justify-between ${
                isActive
                  ? "bg-gray-800 border-emerald-500 shadow-md shadow-emerald-500/10"
                  : "bg-[#111827] border-gray-800 hover:border-gray-700 hover:bg-gray-800/50"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <Icon className={`h-5 w-5 ${cat.color}`} />
                <span className="text-xs font-mono font-semibold text-gray-400">{cat.odds}</span>
              </div>
              <div>
                <p className={`font-bold text-sm ${isActive ? "text-white" : "text-gray-200"}`}>{cat.name}</p>
                <p className="text-xs text-gray-500 mt-0.5">Optimized combination</p>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Generated Slips Display */}
      <div className="space-y-6">
        {slips.length === 0 ? (
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-8 text-center text-gray-400">
            <Layers className="h-8 w-8 mx-auto mb-3 text-gray-600" />
            <p className="font-semibold text-white">No active combinations generated for this recipe</p>
            <p className="text-xs text-gray-500 mt-1">
              Ensure the FastAPI backend is running with sufficient historical fixtures seeded.
            </p>
          </div>
        ) : (
          slips.map((slip: any, index: number) => (
            <div key={index} className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
              <div className="bg-gray-900/80 px-6 py-4 border-b border-gray-800 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-white text-base sm:text-lg flex items-center gap-2">
                    <span>{slip.slip_name}</span>
                    <span className="text-xs px-2.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
                      {slip.risk_class}
                    </span>
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">{slip.leg_count} Legs • Correlation-checked</p>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-xs text-gray-400 uppercase">Combined Odds</p>
                    <p className="text-xl font-extrabold text-emerald-400 font-mono">{slip.combined_odds.toFixed(2)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-400 uppercase">Joint Win Prob</p>
                    <p className="text-xl font-extrabold text-white font-mono">{(slip.joint_probability * 100).toFixed(1)}%</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-400 uppercase">Expected Edge</p>
                    <p className="text-xl font-extrabold text-purple-400 font-mono">+{(slip.expected_return * 100).toFixed(1)}%</p>
                  </div>
                </div>
              </div>

              {/* Legs Table */}
              <div className="divide-y divide-gray-800/60">
                {slip.legs.map((leg: any, lIndex: number) => (
                  <div key={lIndex} className="px-6 py-3.5 flex items-center justify-between text-sm hover:bg-gray-800/30 transition">
                    <div className="flex items-center gap-3">
                      <span className="h-6 w-6 rounded-full bg-gray-800 text-gray-400 font-mono text-xs flex items-center justify-center font-bold">
                        {lIndex + 1}
                      </span>
                      <div>
                        <p className="font-semibold text-white">{leg.fixture}</p>
                        <p className="text-xs text-gray-400 font-mono">{leg.market} • <span className="text-emerald-400 font-bold capitalize">{leg.selection}</span></p>
                      </div>
                    </div>
                    <div className="flex items-center gap-6 text-right">
                      <div>
                        <p className="text-xs text-gray-400">Model Prob</p>
                        <p className="font-mono text-xs text-gray-300 font-medium">{(leg.probability * 100).toFixed(0)}%</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">Leg Odds</p>
                        <p className="font-mono text-sm font-bold text-white">{leg.odds.toFixed(2)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
