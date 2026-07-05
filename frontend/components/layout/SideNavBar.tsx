"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus, History, Database, Settings, Users, LogOut, User } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export function SideNavBar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  
  const navItems = [
    { label: "Knowledge Vault", href: "/admin", icon: Database },
    { label: "Audit Settings", href: "/admin/metrics", icon: Settings },
    { label: "User Management", href: "/admin/users", icon: Users },
  ];

  return (
    <nav className="bg-surface dark:bg-surface w-sidebar-width h-full fixed left-0 top-0 border-r border-outline-variant dark:border-outline-variant bg-surface-container-low flex flex-col py-margin px-4 z-20">
      <div className="mb-8 pl-4">
        <h1 className="font-h2 text-h2 font-semibold text-primary dark:text-primary mb-1">
          EnterpriseMind AI
        </h1>
        <p className="font-data-label text-data-label text-secondary flex items-center">
          <span className="w-2 h-2 rounded-full bg-cyan mr-2 inline-block shadow-[0_0_8px_rgba(79,168,184,0.6)]"></span>
          System Active
        </p>
      </div>

      <button className="w-full bg-brass text-on-primary font-body-sm text-body-sm font-semibold py-3 rounded-DEFAULT mb-8 hover:brightness-110 transition-all flex justify-center items-center scale-98 active:opacity-80 gap-2 cursor-pointer">
        <Plus className="w-4 h-4 text-on-primary" />
        New Analysis
      </button>

      <ul className="flex-grow space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.href === "/admin" 
            ? pathname === "/admin" 
            : pathname.startsWith(item.href);
          return (
            <li key={item.label}>
              <Link
                href={item.href}
                className={`flex items-center pl-4 py-3 rounded-DEFAULT transition-colors duration-200 scale-98 active:opacity-80 gap-3
                  ${isActive 
                    ? "text-secondary font-bold border-l-2 border-secondary bg-surface-container-highest" 
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest"
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                <span className="font-body-sm text-body-sm">{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="mt-auto pt-4 border-t border-outline-variant">
        <div className="flex items-center gap-3 pl-4 py-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center border border-outline-variant">
            <User className="w-4 h-4 text-on-surface-variant" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-body-sm text-body-sm text-on-surface truncate">
              {user?.full_name || "Admin"}
            </p>
            <p className="font-data-mono text-[10px] text-on-surface-variant truncate uppercase">
              {user?.role || "admin"}
            </p>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center gap-2 pl-4 py-2 text-on-surface-variant hover:text-error hover:bg-surface-container-highest rounded transition-colors cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
          <span className="font-body-sm text-body-sm">Logout</span>
        </button>
      </div>
    </nav>
  );
}
