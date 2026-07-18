"use client";

import { useState, Suspense } from "react";
import { UserSideNavBar } from "../../components/layout/UserSideNavBar";
import { ProcessRail } from "../../components/layout/ProcessRail";

export const dynamic = "force-dynamic";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="bg-[#f8fafc] h-screen flex w-full overflow-hidden">
      <Suspense fallback={null}>
        <UserSideNavBar onToggleSidebar={setIsSidebarOpen} isSidebarOpen={isSidebarOpen} />
      </Suspense>
      <div className="flex-grow md:ml-[280px] h-screen flex flex-col p-4 overflow-hidden relative">
        {children}
        <ProcessRail />
      </div>
    </div>
  );
}
