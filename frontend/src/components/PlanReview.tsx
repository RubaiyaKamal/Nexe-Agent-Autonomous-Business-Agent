"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";

type Task = {
  id: string; description: string; task_type: string;
  complexity: string; status: string; order_index: number; is_critical_path: boolean;
};
type Plan = { id: string; goal_id: string; status: string; task_count: number; tasks: Task[] };

const COMPLEXITY_COLOR: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-red-100 text-red-700",
};

export default function PlanReview({ goalId }: { goalId: string }) {
  const router = useRouter();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const { data } = await api.get(`/api/v1/goals/${goalId}/plan`);
        setPlan(data);
        setLoading(false);
      } catch (err: any) {
        if (err.response?.status === 202) {
          timeout = setTimeout(poll, 2000);
        } else {
          setLoading(false);
        }
      }
    };
    poll();
    return () => clearTimeout(timeout);
  }, [goalId]);

  const approve = async () => {
    setActing(true);
    try {
      const { data } = await api.post(`/api/v1/goals/${goalId}/plan/approve`);
      router.push(`/goals/${goalId}/run/${data.id}`);
    } finally { setActing(false); }
  };

  const cancel = async () => {
    setActing(true);
    try {
      await api.post(`/api/v1/goals/${goalId}/plan/cancel`);
      router.push("/goals");
    } finally { setActing(false); }
  };

  if (loading) return <p className="text-gray-400 animate-pulse">Planning in progress…</p>;
  if (!plan) return <p className="text-red-500">No plan found.</p>;

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <button
          onClick={approve} disabled={acting || plan.status !== "draft"}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
        >Approve & Run</button>
        <button
          onClick={cancel} disabled={acting || plan.status !== "draft"}
          className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50"
        >Cancel Plan</button>
      </div>
      {(!plan.tasks || plan.tasks.length === 0) && (
        <p className="text-yellow-600 text-sm border border-yellow-200 rounded p-3 bg-yellow-50">
          No tasks were generated for this plan. The planner may have failed silently — check the worker logs or re-submit the goal.
        </p>
      )}
      <ol className="space-y-2">
        {(plan.tasks ?? []).map((t) => (
          <li key={t.id} className="border rounded p-3">
            <div className="flex gap-2 items-start">
              <span className="text-gray-400 text-sm w-6">{t.order_index + 1}.</span>
              <div className="flex-1">
                <p className="font-medium">{t.description}</p>
                <div className="flex gap-2 mt-1 text-xs">
                  <span className="bg-gray-100 px-2 py-0.5 rounded">{t.task_type}</span>
                  <span className={`px-2 py-0.5 rounded ${COMPLEXITY_COLOR[t.complexity]}`}>{t.complexity}</span>
                  {t.is_critical_path && <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded">critical path</span>}
                </div>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
