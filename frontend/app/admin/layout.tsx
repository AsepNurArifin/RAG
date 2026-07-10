"use client";

import { useState } from "react";
import { SideNavBar } from "../../components/layout/SideNavBar";
import { ProcessRail } from "../../components/layout/ProcessRail";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="bg-[#F2C300] min-h-screen flex w-full overflow-hidden">
      <SideNavBar onToggleSidebar={setIsSidebarOpen} isSidebarOpen={isSidebarOpen} />
      <div className="flex-grow md:ml-[280px] md:mr-[64px] pt-16 md:pt-8 p-4 md:p-8 min-h-screen overflow-y-auto">
        {children}
      </div>
      <ProcessRail />
    </div>
  );
}
