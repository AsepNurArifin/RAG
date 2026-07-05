import type { Metadata } from "next";
import "./globals.css";
import { ActiveAgentProvider } from "../context/ActiveAgentContext";
import { AuthProvider } from "../context/AuthContext";

export const metadata: Metadata = {
  title: "EnterpriseMind AI | Active Analysis",
  description: "Intelligent Multi-Agent Knowledge Assistant with factual verification and source citations.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-on-background font-body-md min-h-screen overflow-x-hidden selection:bg-secondary selection:text-on-secondary antialiased flex">
        
        <AuthProvider>
          <ActiveAgentProvider>
            {children}
          </ActiveAgentProvider>
        </AuthProvider>
        
      </body>
    </html>
  );
}
