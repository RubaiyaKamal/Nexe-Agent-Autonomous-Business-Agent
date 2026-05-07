"use client";
import { useEffect, useRef, useState } from "react";

const TERMINAL = new Set(["run_completed", "run_failed", "run_cancelled"]);

export function useSSE(url: string) {
  const [events, setEvents] = useState<any[]>([]);
  const [status, setStatus] = useState<"connecting" | "open" | "closed">("connecting");
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const fullUrl = token ? `${url}?token=${token}` : url;
    const es = new EventSource(fullUrl);
    esRef.current = es;

    es.onopen = () => setStatus("open");
    es.onerror = () => {
      setError("SSE connection error");
      es.close();
      setStatus("closed");
    };
    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setEvents((prev) => [...prev, data]);
      if (TERMINAL.has(data.event)) {
        es.close();
        setStatus("closed");
      }
    };

    return () => { es.close(); esRef.current = null; };
  }, [url]);

  return { events, status, error };
}
