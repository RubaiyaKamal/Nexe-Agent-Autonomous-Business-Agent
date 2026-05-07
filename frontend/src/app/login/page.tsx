"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { useAuth } from "@/hooks/useAuth";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function parseJwt(token: string) {
  try { return JSON.parse(atob(token.split(".")[1])); } catch { return null; }
}

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/goals");
    } catch {
      setError("Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/api/v1/auth/register`, {
        email,
        password,
        display_name: displayName,
      });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      router.push("/goals");
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded shadow w-96 space-y-4">
        <h1 className="text-2xl font-bold">Nexe Agent</h1>

        <div className="flex border-b">
          <button
            className={`px-4 py-2 text-sm font-medium ${tab === "login" ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500"}`}
            onClick={() => { setTab("login"); setError(""); }}
          >
            Sign in
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium ${tab === "register" ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500"}`}
            onClick={() => { setTab("register"); setError(""); }}
          >
            Create account
          </button>
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        {tab === "login" ? (
          <form onSubmit={handleLogin} className="space-y-3">
            <input
              type="email" placeholder="Email" value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border rounded px-3 py-2"
              required
            />
            <input
              type="password" placeholder="Password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded px-3 py-2"
              required
            />
            <button
              type="submit" disabled={loading}
              className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="space-y-3">
            <input
              type="text" placeholder="Display name" value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full border rounded px-3 py-2"
              required
            />
            <input
              type="email" placeholder="Email" value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border rounded px-3 py-2"
              required
            />
            <input
              type="password" placeholder="Password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border rounded px-3 py-2"
              required minLength={8}
            />
            <button
              type="submit" disabled={loading}
              className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
