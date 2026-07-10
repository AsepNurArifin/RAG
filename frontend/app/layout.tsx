import type { Metadata } from "next";
import "./globals.css";
import { ActiveAgentProvider } from "../context/ActiveAgentContext";
import { AuthProvider } from "../context/AuthContext";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

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
    <html lang="en" className={cn("font-sans", geist.variable)}>
        <body className="bg-background text-foreground font-sans min-h-screen overflow-x-hidden selection:bg-blue-200 selection:text-blue-900 antialiased flex flex-col md:flex-row">
        <ErrorBoundary>
          <AuthProvider>
            <ActiveAgentProvider>
              {children}
            </ActiveAgentProvider>
          </AuthProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
