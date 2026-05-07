"use client";
import { useState } from "react";
import { useQuery, gql } from "@apollo/client";

const LOGS_QUERY = gql`
  query GetLogs($runId: UUID!, $status: String, $limit: Int, $offset: Int) {
    logs(filter: { runId: $runId, status: $status, limit: $limit, offset: $offset }) {
      id timestamp status reasoningSummary taskId errorContext
      inputSnapshot outputSnapshot retryCount
    }
    runAuditSummary(runId: $runId) {
      totalLogEntries
      byStatus { status count }
    }
  }
`;

const STATUS_COLOR: Record<string, string> = {
  succeeded: "text-green-600", failed: "text-red-600",
  skipped: "text-gray-400", retrying: "text-yellow-600",
  running: "text-blue-500", queued: "text-gray-500",
};

export default function LogViewer({ runId }: { runId: string }) {
  const [filter, setFilter] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, loading } = useQuery(LOGS_QUERY, {
    variables: { runId, status: filter || undefined, limit: 100, offset: 0 },
  });

  if (loading) return <p className="text-gray-400 animate-pulse">Loading logs…</p>;

  const logs = data?.logs ?? [];
  const summary = data?.runAuditSummary;

  return (
    <div className="space-y-4">
      {summary && (
        <div className="flex gap-4 text-sm text-gray-600">
          <span>Total entries: <strong>{summary.totalLogEntries}</strong></span>
          {summary.byStatus.map((s: any) => (
            <span key={s.status}>{s.status}: <strong>{s.count}</strong></span>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <select value={filter} onChange={(e) => setFilter(e.target.value)} className="border rounded px-2 py-1 text-sm">
          <option value="">All statuses</option>
          {["queued","running","succeeded","failed","skipped","retrying"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <table className="w-full text-sm border rounded">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left p-2">Time</th>
            <th className="text-left p-2">Status</th>
            <th className="text-left p-2">Summary</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log: any) => (
            <>
              <tr
                key={log.id}
                onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                className="border-t cursor-pointer hover:bg-gray-50"
              >
                <td className="p-2 text-gray-400 whitespace-nowrap">{new Date(log.timestamp).toLocaleTimeString()}</td>
                <td className={`p-2 font-mono font-medium ${STATUS_COLOR[log.status] ?? ""}`}>{log.status}</td>
                <td className="p-2">{log.reasoningSummary}</td>
              </tr>
              {expanded === log.id && (
                <tr key={`${log.id}-detail`} className="bg-gray-50">
                  <td colSpan={3} className="p-3">
                    <pre className="text-xs overflow-auto">{JSON.stringify({ input: log.inputSnapshot, output: log.outputSnapshot, error: log.errorContext }, null, 2)}</pre>
                  </td>
                </tr>
              )}
            </>
          ))}
          {logs.length === 0 && (
            <tr><td colSpan={3} className="p-4 text-center text-gray-400">No log entries</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
