"use client";

import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { ShieldCheck, Mail, Lock, AlertCircle, Loader2, Sparkles } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { motion } from "framer-motion";

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
    <div className="w-full min-h-screen flex items-center justify-center bg-[#f8fafc] p-6 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-[#0077ff]/10 rounded-full blur-3xl opacity-30 pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-[#F2C300]/10 rounded-full blur-3xl opacity-30 pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-full max-w-lg z-10"
      >
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200, damping: 15 }}
            className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-[#004790] shadow-md mb-6"
          >
            <Sparkles className="w-10 h-10 text-white" />
          </motion.div>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-slate-900">
            EnterpriseMind AI
          </h1>
          <p className="text-base font-semibold text-slate-600 mt-2 bg-white px-3 py-1 rounded-full border border-slate-200 shadow-sm inline-block">
            Internal Knowledge Assistant — Secure Login
          </p>
        </div>

        <Card className="shadow-xl border border-slate-200 bg-white p-4 md:p-6 rounded-2xl">
          <CardHeader className="pb-6">
            <CardTitle className="text-2xl text-center text-slate-900 font-bold">Masuk ke Sistem</CardTitle>
            <CardDescription className="text-center text-base text-slate-600 mt-1">
              Masukkan kredensial Anda untuk melanjutkan
            </CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}>
                <Alert variant="destructive" className="mb-6 bg-red-50 border border-red-200 text-red-800">
                  <AlertCircle className="h-5 w-5 text-red-600" />
                  <AlertDescription className="text-sm font-medium">{error}</AlertDescription>
                </Alert>
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="login-email" className="text-sm font-semibold text-slate-700">Email Perusahaan</Label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <Input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="nama@perusahaan.com"
                    required
                    disabled={isSubmitting}
                    className="h-12 pl-12 pr-4 text-base bg-white border-slate-300 focus-visible:ring-[#0077ff] text-slate-800 rounded-xl"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="login-password" className="text-sm font-semibold text-slate-700">Kata Sandi</Label>
                </div>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <Input
                    id="login-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    disabled={isSubmitting}
                    className="h-12 pl-12 pr-4 text-base bg-white border-slate-300 focus-visible:ring-[#0077ff] text-slate-800 rounded-xl"
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="w-full h-12 bg-[#0077ff] hover:bg-[#0047b3] text-white shadow-lg hover:shadow-xl transition-all mt-6 text-base font-bold rounded-xl cursor-pointer"
                disabled={isSubmitting || !email || !password}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    Memverifikasi...
                  </>
                ) : (
                  "Masuk"
                )}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex justify-center flex-col gap-4 border-t border-slate-200 pt-6 mt-6">
            <p className="text-center text-sm text-slate-600 font-medium">
              Hubungi admin jika Anda belum memiliki akun.
            </p>
            <p className="text-center font-mono text-[10px] text-slate-400 uppercase tracking-widest">
              EnterpriseMind AI v0.1.0
            </p>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
}
