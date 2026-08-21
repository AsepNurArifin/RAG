"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "user";
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // Check for existing session on mount via /api/auth/me.
  // Auth state comes from the httpOnly cookie set by the backend — no localStorage.
  useEffect(() => {
    fetch(`${API_BASE_URL}/auth/me`, { credentials: "include" })
      .then((res) => {
        if (!res.ok) throw new Error("No session");
        return res.json();
      })
      .then((userData) => setUser(userData))
      .catch(() => {
        setUser(null);
        if (pathname !== "/login") {
          router.push("/login");
        }
      })
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Redirect to login if not authenticated (except on /login page)
  useEffect(() => {
    if (!isLoading && !user && pathname !== "/login") {
      router.push("/login");
    }
  }, [isLoading, user, pathname, router]);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        console.error("[Login] Error:", response.status, error);
        throw new Error(error.detail || "Login gagal.");
      }

      const data = await response.json();
      setUser(data.user);

      if (data.user.role === "admin") {
        router.push("/admin");
      } else {
        router.push("/");
      }
    },
    [router]
  );

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch (err) {
      console.error("Logout failed", err);
    }
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isAdmin: user?.role === "admin",
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
