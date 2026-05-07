import LogViewer from "@/components/LogViewer";

export default function RunLogsPage({ params }: { params: { id: string } }) {
  return (
    <main className="max-w-5xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Execution Log</h1>
      <p className="text-sm text-gray-500">Run: {params.id}</p>
      <LogViewer runId={params.id} />
    </main>
  );
}
