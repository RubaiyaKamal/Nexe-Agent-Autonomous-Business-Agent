"use client";
import { useState, useCallback } from "react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function parseJwt(token: string) {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return null;
  }
}

export function useAuth() {
  const [currentUser, setCurrentUser] = useState<{ email: string; sub: string } | null>(() => {
    if (typeof window === "undefined") return null;
    const t = localStorage.getItem("access_token");
    return t ? parseJwt(t) : null;
  });

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await axios.post(`${API}/api/v1/auth/token`, { email, password });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setCurrentUser(parseJwt(data.access_token));
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setCurrentUser(null);
  }, []);

  const refreshToken = useCallback(async () => {
    const refresh = localStorage.getItem("refresh_token");
    if (!refresh) return;
    const { data } = await axios.post(`${API}/api/v1/auth/refresh`, { refresh_token: refresh });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setCurrentUser(parseJwt(data.access_token));
  }, []);

  return { currentUser, login, logout, refreshToken };
}
