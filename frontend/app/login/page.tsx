"use client";

import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { ShieldCheck, Mail, Lock, AlertCircle, Loader2 } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login gagal.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full flex-1 min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md">
        {/* Logo / Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-surface-container-high border border-outline-variant mb-6">
            <ShieldCheck className="w-8 h-8 text-secondary" />
          </div>
          <h1 className="font-h2 text-h2 font-semibold text-primary">
            EnterpriseMind AI
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant mt-2">
            Internal Knowledge Assistant — Secure Login
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-8 shadow-lg">
          <h2 className="font-h3 text-h3 text-on-surface mb-6 text-center">
            Masuk ke Sistem
          </h2>

          {error && (
            <div className="flex items-center gap-2 bg-error/10 border border-error/30 text-error rounded px-4 py-3 mb-6 font-body-sm text-body-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email */}
            <div>
              <label
                htmlFor="login-email"
                className="block font-data-label text-data-label text-on-surface-variant uppercase tracking-widest mb-2"
              >
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-outline-variant" />
                <input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="nama@perusahaan.com"
                  required
                  disabled={isSubmitting}
                  className="w-full bg-surface-container-high border border-outline rounded py-3 pl-10 pr-4 text-on-surface font-body-sm text-body-sm focus:border-secondary focus:ring-1 focus:ring-secondary transition-all placeholder:text-outline-variant/50 disabled:opacity-50"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="login-password"
                className="block font-data-label text-data-label text-on-surface-variant uppercase tracking-widest mb-2"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-outline-variant" />
                <input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={isSubmitting}
                  className="w-full bg-surface-container-high border border-outline rounded py-3 pl-10 pr-4 text-on-surface font-body-sm text-body-sm focus:border-secondary focus:ring-1 focus:ring-secondary transition-all placeholder:text-outline-variant/50 disabled:opacity-50"
                />
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting || !email || !password}
              className="w-full bg-brass text-on-primary font-body-sm text-body-sm font-semibold py-3 rounded hover:brightness-110 transition-all flex justify-center items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Memverifikasi...
                </>
              ) : (
                "Masuk"
              )}
            </button>
          </form>

          <p className="text-center font-body-sm text-body-sm text-on-surface-variant mt-6 opacity-60">
            Hubungi admin jika belum memiliki akun.
          </p>
        </div>

        {/* Footer */}
        <p className="text-center font-data-mono text-[10px] text-on-surface-variant mt-8 opacity-40 uppercase">
          EnterpriseMind AI v0.1.0 — Internal Use Only
        </p>
      </div>
    </div>
  );
}
