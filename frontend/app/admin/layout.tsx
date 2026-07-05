import { SideNavBar } from "../../components/layout/SideNavBar";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <SideNavBar />
      {/* Layout margins: left = sidebar-width (280px). No process rail on the right */}
      <div className="flex-1 ml-[280px]">
        {children}
      </div>
    </>
  );
}
