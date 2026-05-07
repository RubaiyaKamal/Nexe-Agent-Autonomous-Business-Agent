import PlanReview from "@/components/PlanReview";

export default function PlanPage({ params }: { params: { id: string } }) {
  return (
    <main className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Plan Review</h1>
      <PlanReview goalId={params.id} />
    </main>
  );
}
