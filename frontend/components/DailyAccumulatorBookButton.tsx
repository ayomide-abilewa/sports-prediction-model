"use client";

import { useState } from "react";

type DailyLeg = {
  match_id: number;
  event_id: string;
  market_id: string;
  outcome_id: string;
  specifier?: string;
  fixture: string;
  kickoff: string;
  market: string;
  selection: string;
  odds: number;
  probability: number;
};

export default function DailyAccumulatorBookButton({ legs, date }: { legs: DailyLeg[]; date: string }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [shareUrl, setShareUrl] = useState("");

  async function createCode() {
    setBusy(true);
    setMessage("");
    setShareUrl("");
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/accumulators/custom`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slip_name: `Daily ${date} ${legs.length}-match accumulator`,
          legs: legs.map((leg) => ({ ...leg, kickoff: leg.kickoff })),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "The bookmaker could not create this share code.");
      setShareUrl(data.share_url);
      setMessage(`Share code: ${data.booking_code}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create the share code.");
    } finally {
      setBusy(false);
    }
  }

  if (!legs.length) return null;

  return (
    <div className="p-5 border-t border-gray-800 flex flex-wrap items-center gap-3">
      <button onClick={createCode} disabled={busy} className="rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-gray-950 disabled:opacity-50">
        {busy ? "Checking selections…" : `Create ${legs.length}-match SportyBet share code`}
      </button>
      {message && <p className="text-xs text-gray-300 break-all">{message}</p>}
      {shareUrl && <a className="text-xs text-emerald-300 underline" href={shareUrl} target="_blank" rel="noreferrer">Open booking</a>}
    </div>
  );
}
