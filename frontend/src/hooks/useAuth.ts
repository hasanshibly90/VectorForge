import { useCallback, useEffect, useState } from "react";
import { getMe, login as loginApi, register as registerApi } from "../api/client";
import type { User } from "../types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem("vf_token");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const res = await getMe();
      setUser(res.data);
    } catch {
      localStorage.removeItem("vf_token");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (email: string, password: string) => {
    const res = await loginApi(email, password);
    localStorage.setItem("vf_token", res.data.access_token);
    await loadUser();
  };

  const register = async (email: string, password: string) => {
    const res = await registerApi(email, password);
    localStorage.setItem("vf_token", res.data.access_token);
    await loadUser();
  };

  const logout = () => {
    localStorage.removeItem("vf_token");
    setUser(null);
  };

  return { user, loading, login, register, logout };
}
