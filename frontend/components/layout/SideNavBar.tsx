"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database, Settings, Users, LogOut, User, Menu, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { motion, AnimatePresence } from "framer-motion";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";

interface SideNavBarProps {
  onToggleSidebar?: (open: boolean) => void;
  isSidebarOpen?: boolean;
}

export function SideNavBar({ onToggleSidebar, isSidebarOpen = false }: SideNavBarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  
  const navItems = [
    { label: "Knowledge Vault", href: "/admin", icon: Database },
    { label: "Audit Settings", href: "/admin/metrics", icon: Settings },
    { label: "User Management", href: "/admin/users", icon: Users },
  ];

  const handleNavClick = () => {
    onToggleSidebar?.(false);
  };

  const sidebarContent = (
    <nav className="w-[280px] h-full flex flex-col py-6 px-4">
      {/* Header */}
      <div className="mb-8 pl-2 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white mb-1">
            EnterpriseMind AI
          </h1>
          <p className="text-xs font-medium text-blue-100 flex items-center">
            <span className="w-2 h-2 rounded-full bg-emerald-400 mr-2 shadow-[0_0_8px_rgba(52,211,153,0.5)]"></span>
            System Active
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onToggleSidebar?.(false)}
          className="md:hidden text-white hover:bg-blue-800/60 h-8 w-8"
        >
          <X className="w-5 h-5" />
        </Button>
      </div>

      {/* Navigation list */}
      <ul className="flex-grow space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.href === "/admin" 
            ? pathname === "/admin" 
            : pathname.startsWith(item.href);
            
          return (
            <li key={item.label}>
              <Link href={item.href} onClick={handleNavClick}>
                <motion.div
                  whileHover={{ x: 4 }}
                  whileTap={{ scale: 0.98 }}
                  className={`flex items-center pl-3 pr-4 py-2.5 rounded-lg transition-all gap-3 cursor-pointer
                    ${isActive 
                      ? "bg-blue-800/80 text-white font-semibold border-l-4 border-[#F2C300]" 
                      : "text-blue-100 hover:bg-blue-800/40 hover:text-white"
                    }
                  `}
                >
                  <Icon className={`w-5 h-5 ${isActive ? "text-[#F2C300]" : "text-blue-200"}`} />
                  <span className="text-sm">{item.label}</span>
                </motion.div>
              </Link>
            </li>
          );
        })}
      </ul>

      {/* User Profile & Logout */}
      <div className="mt-auto pt-4 border-t border-blue-700/50">
        <div className="flex items-center gap-3 px-3 py-3 mx-1 rounded-xl bg-blue-800/50 border border-blue-700/40 text-white">
          <Avatar className="w-9 h-9 border border-blue-700 shadow-sm bg-blue-900/50">
            <AvatarFallback className="bg-blue-900 text-blue-100">
              <User className="w-4 h-4" />
            </AvatarFallback>
          </Avatar>
          
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white truncate font-semibold">
              {user?.full_name || "Admin"}
            </p>
            <p className="font-mono text-[10px] text-blue-200 truncate uppercase tracking-wider">
              {user?.role || "admin"}
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
        className="fixed top-4 left-4 z-30 md:hidden bg-[#0077ff] text-white hover:bg-blue-700 shadow-lg h-10 w-10"
      >
        <Menu className="w-5 h-5" />
      </Button>

      {/* Desktop sidebar — always visible */}
      <div className="hidden md:flex fixed left-0 top-0 h-full w-[280px] bg-[#0077ff] border-r border-blue-700/30 z-20 shadow-md flex-col">
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
              className="fixed left-0 top-0 h-full w-[280px] bg-[#0077ff] z-40 md:hidden shadow-2xl flex flex-col"
            >
              {sidebarContent}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
