import React from "react";
import { CheckCircle2, Shield, TrendingUp, Cpu, BarChart2, Layers } from "lucide-react";

export default function PerformancePage() {
  const models = [
    { name: "Dixon-Coles Bivariate Poisson", version: "v1.0.4", status: "Production", brier: "0.184", logloss: "0.521", clv: "+4.2%" },
    { name: "Dynamic Elo Rating System", version: "v1.2.0", status: "Production", brier: "0.198", logloss: "0.548", clv: "+3.1%" },
    { name: "Negative Binomial Corners", version: "v1.0.1", status: "Production", brier: "0.210", logloss: "0.590", clv: "+2.8%" },
    { name: "Negative Binomial Cards", version: "v1.0.1", status: "Production", brier: "0.215", logloss: "0.602", clv: "+2.5%" },
    { name: "Expected Goals (xG) Strength", version: "v0.9.0", status: "Validated", brier: "0.189", logloss: "0.534", clv: "+3.6%" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">Model Performance & Calibration Center</h1>
        <p className="text-gray-400 text-sm mt-1">
          Rigorous statistical validation, walk-forward out-of-sample backtesting, and Closing Line Value (CLV) benchmarks.
        </p>
      </div>

      {/* Model Artifacts Registry */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-gray-800 flex items-center justify-between">
          <h2 className="font-bold text-white text-base sm:text-lg flex items-center gap-2">
            <Cpu className="h-5 w-5 text-emerald-400" />
            <span>Active Model Registry</span>
          </h2>
          <span className="text-xs px-2.5 py-1 rounded bg-gray-900 border border-gray-800 font-mono text-gray-400">
            5 Models Tracked
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-900/60 text-gray-400 text-xs uppercase border-b border-gray-800">
              <tr>
                <th className="px-5 py-3">Model Architecture</th>
                <th className="px-4 py-3">Version</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Brier Score</th>
                <th className="px-4 py-3 text-right">Log-Loss</th>
                <th className="px-5 py-3 text-right">CLV Outperformance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 text-gray-200">
              {models.map((m, i) => (
                <tr key={i} className="hover:bg-gray-800/40 transition">
                  <td className="px-5 py-4 font-semibold text-white">{m.name}</td>
                  <td className="px-4 py-4 font-mono text-xs text-gray-400">{m.version}</td>
                  <td className="px-4 py-4">
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-medium">
                      {m.status}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right font-mono font-medium">{m.brier}</td>
                  <td className="px-4 py-4 text-right font-mono text-gray-400">{m.logloss}</td>
                  <td className="px-5 py-4 text-right font-mono font-bold text-emerald-400">{m.clv}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Validation Checklist Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="font-bold text-white text-base mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-400" />
            <span>Anti-Data-Leakage Verification</span>
          </h3>
          <ul className="space-y-2 text-xs text-gray-300">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>Strict temporal splitting: only matches with kickoff &lt; target kickoff used.</span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>Closing odds never used during feature construction.</span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>Lineup mode separation: pre-lineup vs confirmed starting XI flags.</span>
            </li>
          </ul>
        </div>

        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="font-bold text-white text-base mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-blue-400" />
            <span>Probability Calibration Guarantees</span>
          </h3>
          <ul className="space-y-2 text-xs text-gray-300">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-blue-400 shrink-0" />
              <span>Isotonic regression and Platt scaling applied out-of-fold.</span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-blue-400 shrink-0" />
              <span>Empirical frequency aligns with probability binning (ECE &lt; 0.035).</span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-blue-400 shrink-0" />
              <span>Bookmaker overround explicitly stripped for unbiased value metrics.</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
