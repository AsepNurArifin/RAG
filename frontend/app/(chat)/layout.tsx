"use client";

import { useState, Suspense } from "react";
import { UserSideNavBar } from "../../components/layout/UserSideNavBar";
import { ProcessRail } from "../../components/layout/ProcessRail";

export const dynamic = "force-dynamic";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="bg-[#F2C300] h-screen flex w-full overflow-hidden">
      <Suspense fallback={null}>
        <UserSideNavBar onToggleSidebar={setIsSidebarOpen} isSidebarOpen={isSidebarOpen} />
      </Suspense>
      <div className="flex-grow md:ml-[280px] md:mr-[64px] h-screen flex flex-col p-4 overflow-hidden">
        {children}
      </div>
      <ProcessRail />
    </div>
  );
}
