import React from "react";
import Link from "next/link";
import { Flame, Layers, ShieldCheck, Sparkles, Trophy } from "lucide-react";
import AccumulatorCard from "../../components/AccumulatorCard";
import DailyAccumulatorBookButton from "../../components/DailyAccumulatorBookButton";

async function getAccumulators(category: string) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/accumulators?category=${category}`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

async function getDailyCard(date?: string) {
  try {
    const dateParam = date ? `&date=${encodeURIComponent(date)}` : "";
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/accumulators/daily?max_matches=30${dateParam}`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export default async function AccumulatorsPage({
  searchParams,
}: {
  searchParams?: { category?: string; date?: string };
}) {
  const currentCategory = searchParams?.category || "solid_core";
  const slips = await getAccumulators(currentCategory);
  const dailyCard = await getDailyCard(searchParams?.date);

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
          Constraint-optimized accumulator slips with correlation detection, SportyBet booking code generation, and mathematical edge ranking.
        </p>
      </div>

      <section className="bg-[#111827] border border-gray-800 rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-gray-800 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-bold text-white">Daily market shortlist</h2>
            <p className="text-xs text-gray-400 mt-1">
              {dailyCard ? `${dailyCard.leg_count} of up to 30 available fixtures · ${dailyCard.date} WAT` : "Live fixture feed unavailable"}
            </p>
          </div>
          <form action="/accumulators" method="get" className="flex items-center gap-2">
            <input type="hidden" name="category" value={currentCategory} />
            <label htmlFor="daily-date" className="text-xs text-gray-400">Fixture date</label>
            <input id="daily-date" name="date" type="date" defaultValue={dailyCard?.date || searchParams?.date} className="rounded-lg bg-gray-900 border border-gray-700 px-2 py-1.5 text-xs text-white" />
            <button className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-white">Show</button>
          </form>
          {dailyCard?.leg_count > 0 && (
            <div className="text-right text-xs text-gray-400">
              <div>Combined odds <span className="font-mono text-white">{Number(dailyCard.combined_odds) >= 1e6 ? Number(dailyCard.combined_odds).toExponential(2) : Number(dailyCard.combined_odds).toLocaleString()}</span></div>
              <div>Estimated joint chance <span className="font-mono text-white">{Number(dailyCard.joint_probability) * 100 < 0.01 ? `${(Number(dailyCard.joint_probability) * 100).toExponential(2)}%` : `${(Number(dailyCard.joint_probability) * 100).toPrecision(3)}%`}</span></div>
            </div>
          )}
        </div>
        {dailyCard?.legs?.length ? (
          <div className="max-h-[32rem] overflow-y-auto divide-y divide-gray-800/70">
            {dailyCard.legs.map((leg: any, i: number) => (
              <div key={`${leg.event_id}-${leg.market_id}-${leg.outcome_id}`} className="px-5 py-3 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">{i + 1}. {leg.fixture}</p>
                  <p className="text-xs text-gray-400">{leg.league} · {new Date(leg.kickoff).toLocaleTimeString("en-NG", { hour: "2-digit", minute: "2-digit", timeZone: "Africa/Lagos" })} WAT</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-emerald-300">{leg.market}: {leg.selection} <span className="text-gray-400">@{Number(leg.odds).toFixed(2)}</span></p>
                  <p className="text-[11px] text-gray-500">{(Number(leg.probability) * 100).toFixed(1)}% · {leg.probability_source === "model" ? "model forecast" : "market-implied"}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="p-5 text-sm text-gray-400">No supported upcoming markets were returned for today.</p>
        )}
        {dailyCard?.warnings?.map((warning: string) => (
          <p key={warning} className="px-5 py-2 text-[11px] text-amber-300/80 border-t border-gray-800">{warning}</p>
        ))}
        {dailyCard?.legs?.length > 0 && <DailyAccumulatorBookButton legs={dailyCard.legs} date={dailyCard.date} />}
      </section>

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
          <div className="bg-[#111827] border border-gray-800 rounded-2xl p-8 text-center text-gray-400">
            <Layers className="h-8 w-8 mx-auto mb-3 text-gray-600" />
            <p className="font-semibold text-white">No active combinations generated for this recipe</p>
            <p className="text-xs text-gray-500 mt-1">
              Ensure the FastAPI backend is running with upcoming fixtures seeded.
            </p>
          </div>
        ) : (
          slips.map((slip: any, index: number) => (
            <AccumulatorCard key={index} slip={slip} />
          ))
        )}
      </div>
    </div>
  );
}
