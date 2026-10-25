import React from "react";
import { Calendar, CheckCircle2, Clock, Trophy } from "lucide-react";

async function getFixtures() {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/v1/fixtures?limit=50", { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    return [];
  }
}

export default async function FixturesPage() {
  const fixtures = await getFixtures();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Analyzed Match Fixtures</h1>
        <p className="text-gray-400 text-sm mt-1">
          Historical and upcoming matches across Premier League, La Liga, and Serie A.
        </p>
      </div>

      <div className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800 flex items-center justify-between text-xs text-gray-400">
          <span>Showing {fixtures.length} matches</span>
          <span>Coverage: 100% of major European leagues</span>
        </div>

        <div className="divide-y divide-gray-800/60">
          {fixtures.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No fixtures loaded. Ensure the backend is running.
            </div>
          ) : (
            fixtures.map((f: any) => {
              const isFinished = f.status === "finished";
              const kickoffDate = new Date(f.kickoff).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "short",
                year: "numeric",
              });

              return (
                <div key={f.id} className="p-4 sm:px-6 hover:bg-gray-800/30 transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-lg bg-gray-800 flex items-center justify-center text-gray-400">
                      <Trophy className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-gray-400">
                          {f.league}
                        </span>
                        <span className="text-xs text-gray-500">{kickoffDate}</span>
                      </div>
                      <p className="font-bold text-white text-base mt-1">
                        {f.home_team} <span className="text-gray-500 font-normal">vs</span> {f.away_team}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {isFinished ? (
                      <div className="px-3 py-1 rounded bg-gray-900 border border-gray-800 text-right">
                        <span className="text-xs text-gray-400 uppercase font-mono mr-2">FT</span>
                        <span className="font-mono font-bold text-emerald-400 text-base">
                          {f.ft_home_goals} - {f.ft_away_goals}
                        </span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-950/40 border border-amber-800/60 px-2.5 py-1 rounded">
                        <Clock className="h-3.5 w-3.5" />
                        <span>Scheduled</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
