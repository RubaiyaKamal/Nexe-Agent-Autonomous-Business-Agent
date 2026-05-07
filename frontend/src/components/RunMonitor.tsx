"use client";
import { useSSE } from "@/hooks/useSSE";

const STATUS_ICON: Record<string, string> = {
  queued: "○", running: "⟳", succeeded: "✓", failed: "✗", skipped: "–", retrying: "↺",
};

export default function RunMonitor({ runId }: { runId: string }) {
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const { events, status } = useSSE(`${API}/api/v1/runs/${runId}/status/stream`);

  const taskEvents = events.filter((e) => e.payload?.task_id);
  const runEvent = events.find((e) =>
    ["run_completed", "run_failed", "run_cancelled"].includes(e.event)
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <span className={`w-2 h-2 rounded-full ${status === "open" ? "bg-green-500 animate-pulse" : "bg-gray-400"}`} />
        <span className="text-gray-500">{status}</span>
      </div>

      {taskEvents.map((e, i) => (
        <div key={i} className="flex items-center gap-3 border rounded p-3">
          <span className="text-lg w-6 text-center">{STATUS_ICON[e.payload?.status ?? ""] ?? "?"}</span>
          <div>
            <p className="text-sm font-medium">{e.payload?.description ?? e.event}</p>
            <p className="text-xs text-gray-400">{e.payload?.task_id}</p>
          </div>
        </div>
      ))}

      {runEvent && (
        <div className={`p-3 rounded font-semibold ${runEvent.event === "run_completed" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
          {runEvent.event === "run_completed" ? "Run completed" : "Run failed/cancelled"}
        </div>
      )}

      {events.length === 0 && status === "connecting" && (
        <p className="text-gray-400 animate-pulse">Waiting for events…</p>
      )}
    </div>
  );
}
