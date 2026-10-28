import React from "react";
import { BarChart2, Shield } from "lucide-react";

export const dynamic = "force-dynamic";

async function getSummary() {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/performance/summary`, { cache: "no-store" });
    return response.ok ? await response.json() : null;
  } catch {
    return null;
  }
}

export default async function PerformancePage() {
  const summary = await getSummary();
  const stats = summary?.dataset_statistics;
  const models = summary?.model_versions ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Prediction Tracking</h1>
        <p className="text-gray-400 text-sm mt-1">Only saved forecasts and graded results are reported here.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          ["Saved forecasts", stats?.saved_predictions ?? 0],
          ["Settled forecasts", stats?.settled_predictions ?? 0],
          ["Completed matches", stats?.finished_matches ?? 0],
          ["Configured competitions", stats?.active_leagues ?? 0],
        ].map(([label, value]) => (
          <div key={label} className="bg-[#111827] border border-gray-800 rounded-xl p-5">
            <p className="text-xs uppercase tracking-wider text-gray-400">{label}</p>
            <p className="text-2xl font-bold text-white mt-2">{Number(value).toLocaleString()}</p>
          </div>
        ))}
      </div>

      <section className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-gray-800 flex items-center gap-2">
          <BarChart2 className="h-5 w-5 text-emerald-400" />
          <h2 className="font-bold text-white">Model records</h2>
        </div>
        {models.length ? (
          <div className="divide-y divide-gray-800">
            {models.map((model: any, index: number) => (
              <div key={`${model.name}-${model.version}-${index}`} className="p-5 flex flex-wrap items-center justify-between gap-3 text-sm">
                <div>
                  <p className="font-semibold text-white">{model.name} · {model.version}</p>
                  <p className="text-xs text-gray-400">{model.training_samples ?? "—"} training samples · {model.status}</p>
                </div>
                <div className="text-xs text-gray-300 text-right">
                  Brier {model.brier_score ?? "not measured"} · Log loss {model.log_loss ?? "not measured"} · CLV {model.clv_rate ?? "not measured"}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="p-6 text-sm text-gray-400">No model runs or measured performance scores have been saved yet.</p>
        )}
      </section>

      <div className="bg-blue-950/30 border border-blue-900/60 rounded-xl p-5 flex gap-3 text-sm text-blue-100">
        <Shield className="h-5 w-5 shrink-0 text-blue-300" />
        <p>Forecasts are saved when generated and graded only after a completed score is available. Calibration and closing-line value will appear after enough tracked data exists.</p>
      </div>
    </div>
  );
}
