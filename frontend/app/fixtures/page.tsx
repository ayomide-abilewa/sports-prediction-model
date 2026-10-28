import React from "react";
import MatchList from "../../components/MatchList";

export const dynamic = "force-dynamic";

async function getMatches() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/predictions/matches?limit=120`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

export default async function FixturesPage() {
  const matches = await getMatches();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Analyzed Match Fixtures</h1>
        <p className="text-gray-400 text-sm mt-1">
          Historical and upcoming matches with AI surest predictions, expected goals (xG), and interactive bet slip builder.
        </p>
      </div>

      <MatchList fixtures={matches} />
    </div>
  );
}
