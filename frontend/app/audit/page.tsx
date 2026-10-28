import React from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, ShieldCheck, Trophy } from "lucide-react";
import RecentPicksAudit from "../../components/RecentPicksAudit";

export const dynamic = "force-dynamic";

function yesterdayInLagos() {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Africa/Lagos",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const part = (type: string) => parts.find((entry) => entry.type === type)?.value || "";
  const day = new Date(`${part("year")}-${part("month")}-${part("day")}T00:00:00Z`);
  day.setUTCDate(day.getUTCDate() - 1);
  return day.toISOString().slice(0, 10);
}

async function getAuditData(date: string) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/audit/recent?date=${encodeURIComponent(date)}`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

export default async function AuditPage({
  searchParams,
}: {
  searchParams?: { date?: string };
}) {
  const selectedDate = searchParams?.date || yesterdayInLagos();
  const auditData = await getAuditData(selectedDate);

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <div>
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition font-mono"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Terminal Dashboard</span>
        </Link>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-800 bg-gray-900/70 px-4 py-3">
        <form action="/audit" method="get" className="flex items-center gap-2">
          <label htmlFor="audit-date" className="text-xs text-gray-400">Results date</label>
          <input id="audit-date" name="date" type="date" defaultValue={selectedDate} className="rounded-lg bg-gray-950 border border-gray-700 px-2 py-1.5 text-xs text-white" />
          <button className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-white">Show</button>
        </form>
        <a href="https://sportscore.com/" rel="dofollow" className="text-[11px] text-gray-500 hover:text-emerald-400">Powered by SportScore</a>
      </div>

      {auditData ? (
        <RecentPicksAudit data={auditData} />
      ) : (
        <div className="py-16 text-center text-gray-400 bg-gray-900 border border-gray-800 rounded-2xl">
          <Trophy className="h-8 w-8 mx-auto mb-2 text-gray-600" />
          <p className="font-semibold text-white">Loading Audit Data...</p>
          <p className="text-xs text-gray-500 mt-1">Ensure the FastAPI backend is running on port 8000.</p>
        </div>
      )}
    </div>
  );
}
