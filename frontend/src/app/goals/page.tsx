"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import api from "@/lib/api";
import GoalForm from "@/components/GoalForm";

type Goal = { id: string; text: string; status: string; submitted_at: string };

const STATUS_COLORS: Record<string, string> = {
  received: "bg-gray-100 text-gray-700",
  planning: "bg-yellow-100 text-yellow-700",
  plan_ready: "bg-blue-100 text-blue-700",
  approved: "bg-purple-100 text-purple-700",
  executing: "bg-orange-100 text-orange-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-gray-200 text-gray-500",
  failed: "bg-red-100 text-red-700",
};

export default function GoalsPage() {
  const router = useRouter();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [showForm, setShowForm] = useState(false);

  const fetchGoals = () => {
    api.get("/api/v1/goals").then((r) => setGoals(r.data)).catch(() => {});
  };

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    fetchGoals();
  }, [router]);

  return (
    <main className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Goals</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          {showForm ? "Cancel" : "New Goal"}
        </button>
      </div>
      {showForm && (
        <div className="border rounded p-4">
          <GoalForm onSubmitted={fetchGoals} />
        </div>
      )}
      <table className="w-full text-sm border rounded overflow-hidden">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left p-3">Goal</th>
            <th className="text-left p-3">Status</th>
            <th className="text-left p-3">Submitted</th>
          </tr>
        </thead>
        <tbody>
          {goals.map((g) => (
            <tr key={g.id} className="border-t hover:bg-gray-50">
              <td className="p-3">
                <Link href={`/goals/${g.id}/plan`} className="text-blue-600 hover:underline">
                  {g.text.slice(0, 80)}{g.text.length > 80 ? "…" : ""}
                </Link>
              </td>
              <td className="p-3">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[g.status] ?? ""}`}>
                  {g.status}
                </span>
              </td>
              <td className="p-3 text-gray-500">{new Date(g.submitted_at).toLocaleString()}</td>
            </tr>
          ))}
          {goals.length === 0 && (
            <tr><td colSpan={3} className="p-4 text-center text-gray-400">No goals yet</td></tr>
          )}
        </tbody>
      </table>
    </main>
  );
}
