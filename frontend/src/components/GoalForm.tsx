"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";

const MAX_LEN = 2000;

export default function GoalForm({ onSubmitted }: { onSubmitted?: () => void }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return setError("Goal text is required");
    if (text.length > MAX_LEN) return setError(`Goal must be ≤ ${MAX_LEN} characters`);
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/api/v1/goals", { text });
      onSubmitted?.();
      router.push(`/goals/${data.id}/plan`);
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Submission failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Describe your business goal..."
        rows={5}
        className="w-full border rounded px-3 py-2 resize-none"
        maxLength={MAX_LEN}
      />
      <div className="flex justify-between text-sm text-gray-500">
        <span>{error && <span className="text-red-600">{error}</span>}</span>
        <span>{text.length}/{MAX_LEN}</span>
      </div>
      <button
        type="submit"
        disabled={loading}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "Submitting…" : "Submit Goal"}
      </button>
    </form>
  );
}
