"use client";

import { useState, useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Plus, History, LogOut, User, Trash2, MessageSquare } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../lib/api";

interface Session {
  id: string;
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface UserSideNavBarProps {
  onNewChat?: () => void;
}

export function UserSideNavBar({ onNewChat }: UserSideNavBarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeSessionId = searchParams.get("session") || undefined;
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);

  // Load sessions
  useEffect(() => {
    loadSessions();
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

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (!confirm("Hapus riwayat percakapan ini?")) return;
    try {
      await api.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (activeSessionId === sessionId) {
        router.push("/");
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const handleNewChat = () => {
    if (onNewChat) {
      onNewChat();
    } else {
      window.location.href = "/";
    }
  };

  return (
    <nav className="bg-surface dark:bg-surface w-sidebar-width h-full fixed left-0 top-0 border-r border-outline-variant dark:border-outline-variant bg-surface-container-low flex flex-col py-margin px-4 z-20">
      {/* Header */}
      <div className="mb-6 pl-4">
        <h1 className="font-h2 text-h2 font-semibold text-primary dark:text-primary mb-1">
          EnterpriseMind AI
        </h1>
        <p className="font-data-label text-data-label text-secondary flex items-center">
          <span className="w-2 h-2 rounded-full bg-cyan mr-2 inline-block shadow-[0_0_8px_rgba(79,168,184,0.6)]"></span>
          System Active
        </p>
      </div>

      {/* New Analysis Button */}
      <button 
        onClick={handleNewChat}
        className="w-full bg-brass text-on-primary font-body-sm text-body-sm font-semibold py-3 rounded-DEFAULT mb-4 hover:brightness-110 transition-all flex justify-center items-center scale-98 active:opacity-80 gap-2 cursor-pointer"
      >
        <Plus className="w-4 h-4 text-on-primary" />
        New Analysis
      </button>

      {/* Mission Logs Header */}
      <div className="flex items-center gap-2 pl-4 mb-2">
        <History className="w-4 h-4 text-on-surface-variant" />
        <span className="font-data-label text-data-label text-on-surface-variant uppercase tracking-widest">
          Mission Logs
        </span>
      </div>

      {/* Session List */}
      <div className="flex-grow overflow-y-auto space-y-1 pr-1 scrollbar-thin">
        {isLoadingSessions ? (
          <div className="text-center py-4">
            <span className="font-body-sm text-body-sm text-on-surface-variant opacity-50">
              Memuat riwayat...
            </span>
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="w-6 h-6 text-on-surface-variant opacity-30 mx-auto mb-2" />
            <span className="font-body-sm text-body-sm text-on-surface-variant opacity-50">
              Belum ada percakapan
            </span>
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.session_id === activeSessionId;
            return (
              <div
                key={session.id}
                onClick={() => router.push(`/?session=${session.session_id}`)}
                className={`w-full text-left flex items-center justify-between pl-4 pr-2 py-2.5 rounded transition-colors duration-200 group cursor-pointer
                  ${isActive
                    ? "text-secondary font-bold border-l-2 border-secondary bg-surface-container-highest"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest"
                  }
                `}
              >
                <span className="font-body-sm text-body-sm truncate flex-1 mr-2">
                  {session.title || "Untitled"}
                </span>
                <button
                  onClick={(e) => handleDeleteSession(e, session.session_id)}
                  className="opacity-0 group-hover:opacity-60 hover:!opacity-100 hover:text-error transition-opacity p-1 cursor-pointer"
                  title="Hapus sesi"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* User Profile & Logout */}
      <div className="mt-auto pt-4 border-t border-outline-variant">
        <div className="flex items-center gap-3 pl-4 py-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center border border-outline-variant">
            <User className="w-4 h-4 text-on-surface-variant" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-body-sm text-body-sm text-on-surface truncate">
              {user?.full_name || "User"}
            </p>
            <p className="font-data-mono text-[10px] text-on-surface-variant truncate uppercase">
              {user?.role || "user"}
            </p>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full bg-secondary hover:bg-secondary/90 text-on-secondary font-data-label text-data-label uppercase tracking-widest py-3 px-4 rounded flex items-center justify-center transition-colors shadow-glow"
        >
          <LogOut className="w-4 h-4" />
          <span className="font-body-sm text-body-sm">Logout</span>
        </button>
      </div>
    </nav>
  );
}
