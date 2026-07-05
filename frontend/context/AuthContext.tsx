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
  token: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // Check for existing token on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("emind_token");
    const savedUser = localStorage.getItem("emind_user");

    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));

      // Verify token is still valid
      fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${savedToken}` },
      })
        .then((res) => {
          if (!res.ok) throw new Error("Token expired");
          return res.json();
        })
        .then((userData) => {
          setUser(userData);
          localStorage.setItem("emind_user", JSON.stringify(userData));
        })
        .catch(() => {
          // Token invalid — clear and redirect
          localStorage.removeItem("emind_token");
          localStorage.removeItem("emind_user");
          setToken(null);
          setUser(null);
          router.push("/login");
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
      if (pathname !== "/login") {
        router.push("/login");
      }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Redirect to login if not authenticated (except on /login page)
  useEffect(() => {
    if (!isLoading) {
      if (!token && pathname !== "/login") {
        router.push("/login");
      } else if (token && pathname === "/login") {
        router.push(user?.role === "admin" ? "/admin" : "/");
      } else if (token && user) {
        // Jika admin mencoba mengakses halaman user (chat), log out dan paksa login
        if (user.role === "admin" && !pathname.startsWith("/admin")) {
          // Kita tidak bisa langsung memanggil fungsi logout() yang didefinisikan di bawah,
          // karena fungsi logout() dibuat dengan useCallback di bawah scope ini.
          // Jadi kita bersihkan localStorage manual dan redirect.
          localStorage.removeItem("emind_token");
          localStorage.removeItem("emind_user");
          router.push("/login");
          setTimeout(() => window.location.reload(), 100);
        }
        // Mencegah user biasa mengakses halaman admin
        else if (user.role === "user" && pathname.startsWith("/admin")) {
          router.push("/");
        }
      }
    }
  }, [isLoading, token, pathname, router, user]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Login gagal.");
    }

    const data = await response.json();
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem("emind_token", data.access_token);
    localStorage.setItem("emind_user", JSON.stringify(data.user));

    if (data.user.role === "admin") {
      router.push("/admin");
    } else {
      router.push("/");
    }
  }, [router]);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("emind_token");
    localStorage.removeItem("emind_user");
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
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
