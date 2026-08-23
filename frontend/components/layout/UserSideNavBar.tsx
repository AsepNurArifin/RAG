"use client";

import { useState, useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Plus, History, LogOut, User, Trash2, MessageSquare, Menu, X, Sparkles } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from "@/components/ui/dialog";

interface Session {
  id: string;
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface UserSideNavBarProps {
  onNewChat?: () => void;
  onToggleSidebar?: (open: boolean) => void;
  isSidebarOpen?: boolean;
}

export function UserSideNavBar({ onNewChat, onToggleSidebar, isSidebarOpen = false }: UserSideNavBarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeSessionId = searchParams.get("session") || undefined;
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);

  useEffect(() => {
    loadSessions();

    // Refresh daftar sesi saat ChatWindow membuat sesi baru (tanpa reload).
    const handleSessionCreated = () => loadSessions();
    window.addEventListener("emind:session-created", handleSessionCreated);
    return () => window.removeEventListener("emind:session-created", handleSessionCreated);
  }, []);

  const loadSessions = async () => {
    setIsLoadingSessions(true);
    try {
      const data = await api.getSessions();
      setSessions(data || []);
    } catch (err) {
      console.error("Failed to load sessions:", err);
      setSessions([]);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    setSessionToDelete(sessionId);
  };

  const confirmDeleteSession = async () => {
    if (!sessionToDelete) return;
    try {
      await api.deleteSession(sessionToDelete);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionToDelete));
      if (activeSessionId === sessionToDelete) {
        router.push("/");
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
    } finally {
      setSessionToDelete(null);
    }
  };

  const handleNewChat = () => {
    if (onNewChat) {
      onNewChat();
    } else {
      window.location.href = "/";
    }
  };

  const handleSessionClick = (sessionId: string) => {
    router.push(`/?session=${sessionId}`);
    onToggleSidebar?.(false);
  };

  const sidebarContent = (
    <nav className="w-[280px] h-full flex flex-col py-6 px-4">
      {/* Header */}
      <div className="mb-6 pl-2 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-lg font-bold tracking-tight text-white">
              EnterpriseMind
            </h1>
          </div>
          <p className="text-xs font-medium text-blue-100 flex items-center pl-10">
            <span className="w-2 h-2 rounded-full bg-emerald-400 mr-2 shadow-[0_0_8px_rgba(52,211,153,0.5)]"></span>
            System Active
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onToggleSidebar?.(false)}
          className="md:hidden text-white hover:bg-white/10 h-8 w-8"
        >
          <X className="w-5 h-5" />
        </Button>
      </div>

      {/* New Analysis Button */}
      <Button
        onClick={handleNewChat}
        className="w-full bg-[#F2C300] hover:bg-[#d8a815] text-slate-900 font-bold py-3 gap-2 mb-6 shadow-sm"
      >
        <Plus className="w-4 h-4 text-slate-900" />
        New Analysis
      </Button>

      {/* Mission Logs Header */}
      <div className="flex items-center gap-2 pl-2 mb-3">
        <History className="w-4 h-4 text-blue-200" />
        <span className="text-xs font-semibold text-blue-200 uppercase tracking-wider">
          Mission Logs
        </span>
      </div>

      {/* Session List */}
      <div className="flex-grow overflow-y-auto space-y-1 pr-1">
        {isLoadingSessions ? (
          <div className="text-center py-4">
            <span className="text-sm text-blue-200/60 animate-pulse">
              Memuat riwayat...
            </span>
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="w-6 h-6 text-blue-300/40 mx-auto mb-2" />
            <span className="text-xs text-blue-200/50">
              Belum ada percakapan
            </span>
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.session_id === activeSessionId;
            return (
              <motion.div
                key={session.id}
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleSessionClick(session.session_id)}
                className={`w-full text-left flex items-center justify-between pl-3 pr-2 py-2 rounded-lg transition-all group cursor-pointer
                  ${isActive
                    ? "bg-white/15 text-white font-semibold border-l-4 border-[#F2C300]"
                    : "text-blue-100 hover:bg-white/10 hover:text-white"
                  }
                `}
              >
                <span className="text-sm truncate flex-1 mr-2">
                  {session.title || "Untitled"}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={(e) => handleDeleteSession(e, session.session_id)}
                  className="opacity-0 group-hover:opacity-100 hover:text-red-300 hover:bg-red-500/20 text-blue-200 h-7 w-7 rounded-md transition-all cursor-pointer shrink-0"
                  title="Hapus sesi"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </motion.div>
            );
          })
        )}
      </div>

      {/* User Profile & Logout */}
      <div className="mt-auto pt-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-3 py-3 mx-1 rounded-xl bg-white/10 border border-white/10 text-white">
          <Avatar className="w-9 h-9 border border-white/20 shadow-sm bg-[#0077ff]">
            <AvatarFallback className="bg-[#0077ff] text-white">
              <User className="w-4 h-4" />
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white truncate font-semibold">
              {user?.full_name || "User"}
            </p>
            <p className="font-mono text-[10px] text-blue-200 truncate uppercase tracking-wider">
              {user?.role || "user"}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            className="text-blue-200 hover:text-red-300 hover:bg-red-500/20 rounded-lg shrink-0 h-8 w-8"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </nav>
  );

  return (
    <>
      {/* Hamburger button — mobile only */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => onToggleSidebar?.(!isSidebarOpen)}
        className="fixed top-4 left-4 z-30 md:hidden bg-[#004790] text-white hover:bg-[#0077ff] shadow-lg h-10 w-10"
      >
        <Menu className="w-5 h-5" />
      </Button>

      {/* Desktop sidebar — always visible */}
      <div className="hidden md:flex fixed left-0 top-0 h-full w-[280px] bg-[#004790] border-r border-blue-800/30 z-20 shadow-md flex-col">
        {sidebarContent}
      </div>

      {/* Mobile sidebar — overlay */}
      <AnimatePresence>
        {isSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => onToggleSidebar?.(false)}
              className="fixed inset-0 bg-black/50 z-30 md:hidden"
            />
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="fixed left-0 top-0 h-full w-[280px] bg-[#004790] z-40 md:hidden shadow-2xl flex flex-col"
            >
              {sidebarContent}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Delete Confirmation Dialog */}
      <Dialog open={sessionToDelete !== null} onOpenChange={(open) => !open && setSessionToDelete(null)}>
        <DialogContent className="sm:max-w-[400px] bg-white shadow-xl">
          <DialogHeader>
            <DialogTitle className="text-slate-900 font-bold text-lg">Hapus Riwayat Chat</DialogTitle>
            <DialogDescription className="text-slate-600 mt-2">
              Apakah Anda yakin ingin menghapus riwayat percakapan ini secara permanen? Tindakan ini tidak dapat dibatalkan.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4 flex gap-2">
            <DialogClose render={
              <Button variant="outline" className="border-[#0077ff]/30 hover:bg-[#0077ff]/10 hover:text-[#0077ff] text-slate-750 font-semibold">
                Batal
              </Button>
            } />
            <Button
              onClick={confirmDeleteSession}
              className="bg-red-600 hover:bg-red-700 text-white font-semibold"
            >
              Hapus
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
