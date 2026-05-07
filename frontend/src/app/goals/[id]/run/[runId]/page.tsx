import RunMonitor from "@/components/RunMonitor";
import Link from "next/link";

export default function RunPage({ params }: { params: { id: string; runId: string } }) {
  return (
    <main className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Live Run Monitor</h1>
      <RunMonitor runId={params.runId} />
      <Link href={`/runs/${params.runId}/logs`} className="text-blue-600 hover:underline text-sm">
        View full execution log →
      </Link>
    </main>
  );
}
