"use client";
import { useState } from "react";
import api from "@/lib/api";

export default function SettingsPage() {
  const [autoExecute, setAutoExecute] = useState(false);
  const [saved, setSaved] = useState(false);

  const save = async () => {
    await api.patch("/api/v1/users/me", { auto_execute: autoExecute });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <main className="max-w-xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Settings</h1>
      <div className="border rounded p-4 flex justify-between items-center">
        <div>
          <p className="font-medium">Auto-execute mode</p>
          <p className="text-sm text-gray-500">Automatically run approved plans without manual confirmation</p>
        </div>
        <button
          onClick={() => setAutoExecute(!autoExecute)}
          className={`w-12 h-6 rounded-full transition ${autoExecute ? "bg-blue-600" : "bg-gray-300"}`}
        >
          <span className={`block w-5 h-5 bg-white rounded-full shadow transition transform ${autoExecute ? "translate-x-6" : "translate-x-0.5"}`} />
        </button>
      </div>
      <button onClick={save} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
        {saved ? "Saved!" : "Save Settings"}
      </button>
    </main>
  );
}
