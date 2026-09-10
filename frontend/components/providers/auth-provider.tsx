"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE_URL, ApiError, buildHeaders, extractTokenBundle, normalizeUser, parseResponse } from "@/lib/api";
import type { TokenBundle, UserProfile } from "@/lib/types";

interface RegisterPayload { email: string; password: string; full_name: string; organization_name: string }
interface AuthContextValue {
  user: UserProfile | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  apiFetch: <T>(path: string, init?: RequestInit) => Promise<T>;
}

const ACCESS_KEY = "rag.access_token";
const REFRESH_KEY = "rag.refresh_token";
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const accessRef = useRef("");
  const refreshRef = useRef("");
  const refreshPromiseRef = useRef<Promise<string> | null>(null);

  const storeTokens = useCallback((bundle: TokenBundle) => {
    accessRef.current = bundle.accessToken;
    refreshRef.current = bundle.refreshToken;
    sessionStorage.setItem(ACCESS_KEY, bundle.accessToken);
    sessionStorage.setItem(REFRESH_KEY, bundle.refreshToken);
    if (bundle.user) setUser(bundle.user);
  }, []);

  const clearAuth = useCallback(() => {
    accessRef.current = "";
    refreshRef.current = "";
    sessionStorage.removeItem(ACCESS_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
    setUser(null);
  }, []);

  const publicJson = useCallback(async <T,>(path: string, body: unknown): Promise<T> => {
    const headers = buildHeaders({ "Content-Type": "application/json" });
    const response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", headers, body: JSON.stringify(body) });
    return parseResponse<T>(response);
  }, []);

  const refreshAccess = useCallback(async (): Promise<string> => {
    if (refreshPromiseRef.current) return refreshPromiseRef.current;
    const token = refreshRef.current || sessionStorage.getItem(REFRESH_KEY) || "";
    if (!token) throw new ApiError("Your session has expired. Please sign in again.", { status: 401, code: "SESSION_EXPIRED" });

    refreshPromiseRef.current = (async () => {
      try {
        const data = await publicJson<unknown>("/auth/refresh", { refresh_token: token });
        const bundle = extractTokenBundle(data);
        storeTokens(bundle);
        return bundle.accessToken;
      } catch (error) {
        clearAuth();
        throw error;
      } finally {
        refreshPromiseRef.current = null;
      }
    })();

    return refreshPromiseRef.current;
  }, [clearAuth, publicJson, storeTokens]);

  const apiFetch = useCallback(async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
    const execute = async (token: string) => {
      const headers = buildHeaders(init.headers);
      if (token) headers.set("Authorization", `Bearer ${token}`);
      if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
      return fetch(`${API_BASE_URL}${path}`, { ...init, headers });
    };

    let response = await execute(accessRef.current);
    if (response.status === 401 && path !== "/auth/refresh" && refreshRef.current) {
      const refreshed = await refreshAccess();
      response = await execute(refreshed);
    }
    return parseResponse<T>(response);
  }, [refreshAccess]);

  const loadMe = useCallback(async () => {
    const data = await apiFetch<unknown>("/auth/me");
    setUser(normalizeUser(data));
  }, [apiFetch]);

  useEffect(() => {
    let active = true;
    async function restore() {
      accessRef.current = sessionStorage.getItem(ACCESS_KEY) || "";
      refreshRef.current = sessionStorage.getItem(REFRESH_KEY) || "";
      if (!accessRef.current && !refreshRef.current) {
        if (active) setLoading(false);
        return;
      }
      try {
        await loadMe();
      } catch {
        clearAuth();
      } finally {
        if (active) setLoading(false);
      }
    }
    void restore();
    return () => { active = false; };
  }, [clearAuth, loadMe]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await publicJson<unknown>("/auth/login", { email, password });
    const bundle = extractTokenBundle(data);
    storeTokens(bundle);
    if (!bundle.user) await loadMe();
  }, [loadMe, publicJson, storeTokens]);

  const register = useCallback(async (payload: RegisterPayload) => {
    const data = await publicJson<unknown>("/auth/register", payload);
    const bundle = extractTokenBundle(data);
    storeTokens(bundle);
    if (!bundle.user) await loadMe();
  }, [loadMe, publicJson, storeTokens]);

  const logout = useCallback(async () => {
    const refreshToken = refreshRef.current;
    try {
      if (accessRef.current && refreshToken) {
        await apiFetch<unknown>("/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) });
      }
    } finally {
      clearAuth();
    }
  }, [apiFetch, clearAuth]);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    isAuthenticated: Boolean(user),
    login,
    register,
    logout,
    apiFetch,
  }), [apiFetch, loading, login, logout, register, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
