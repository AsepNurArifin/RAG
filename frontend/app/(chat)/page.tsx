"use client";

import { Suspense } from "react";
import { ChatWindow } from "../../components/ChatWindow";
import { useSearchParams, useRouter } from "next/navigation";

function ChatContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const selectedSessionId = searchParams.get("session") || undefined;

  return (
    <ChatWindow
      externalSessionId={selectedSessionId}
      onSessionChange={(newSessionId) => {
        // Hanya update URL jika kita sedang di sesi kosong (New Chat) 
        // dan ChatWindow baru saja membuat sesi baru.
        // Ini mencegah "bouncing" (infinite loop) dengan state lama.
        if (newSessionId && !selectedSessionId) {
          router.replace(`/?session=${newSessionId}`);
        }
      }}
    />
  );
}

export default function Home() {
  return (
    <main className="w-full h-full">
      <div className="max-w-6xl mx-auto h-full">
        <Suspense fallback={<div className="text-center opacity-50 p-20">Memuat...</div>}>
          <ChatContent />
        </Suspense>
      </div>
    </main>
  );
}
