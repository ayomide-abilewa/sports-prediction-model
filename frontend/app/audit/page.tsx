import React from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, ShieldCheck, Trophy } from "lucide-react";
import RecentPicksAudit from "../../components/RecentPicksAudit";

export const dynamic = "force-dynamic";

async function getAuditData() {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/v1/performance/audit", { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

export default async function AuditPage() {
  const auditData = await getAuditData();

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
