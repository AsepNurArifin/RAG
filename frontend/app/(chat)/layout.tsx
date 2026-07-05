import { UserSideNavBar } from "../../components/layout/UserSideNavBar";
import { ProcessRail } from "../../components/layout/ProcessRail";

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <UserSideNavBar />
      <ProcessRail />
      {/* Layout margins: left = sidebar-width (280px), right = processrail (64px) */}
      <div className="flex-1 ml-[280px] mr-[64px]">
        {children}
      </div>
    </>
  );
}
