import { QueryResponse, Document, Session, Metrics, UserData, Message, UploadResponse, WorkflowStatusResponse } from "../types";

// Base URL for the backend API.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

/**
 * Auth is handled by httpOnly cookie (emind_token) set by the backend.
 * No token in localStorage, no Authorization header needed.
 */
function getAuthHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
  };
}

/**
 * Authenticated fetch wrapper. Uses httpOnly cookie auth (credentials: "include").
 * Uses same-origin proxy (next.config.ts rewrites) to avoid CORS issues.
 */
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = { ...getAuthHeaders(), ...options.headers } as Record<string, string>;

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (options.body instanceof FormData) {
    delete headers["Content-Type"];
  }

  // httpOnly cookie sent automatically; "include" ensures cross-origin cookies work
  return fetch(url, { ...options, headers, credentials: "include" });
}

export const api = {
  // ================================================================ //
  // Query
  // ================================================================ //

  async query(text: string, sessionId?: string): Promise<QueryResponse> {
    const response = await authFetch(`${API_BASE_URL}/query`, {
      method: "POST",
      body: JSON.stringify({
        query: text,
        session_id: sessionId || undefined,
      }),
    });

    if (!response.ok) {
      let errorMessage = "Failed to fetch response";
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {}
      throw new Error(errorMessage);
    }

    return response.json();
  },

  async queryStream(
    text: string, 
    sessionId: string | undefined, 
    onAgentUpdate: (agent: string) => void,
    onResult: (result: QueryResponse) => void,
    onError: (error: Error) => void,
    signal?: AbortSignal
  ) {
    try {
      const response = await authFetch(`${API_BASE_URL}/query`, {
        method: "POST",
        body: JSON.stringify({
          query: text,
          session_id: sessionId || undefined,
        }),
        signal,
      });

      if (!response.ok) {
        throw new Error("Failed to fetch response");
      }

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let receivedResult = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || ""; // Keep the incomplete part

        for (const part of parts) {
          if (part.startsWith("data: ")) {
            const dataStr = part.substring(6);
            try {
              const data = JSON.parse(dataStr);
              if (data.type === "agent") {
                onAgentUpdate(data.agent);
              } else if (data.type === "result") {
                receivedResult = true;
                onResult(data);
              } else if (data.type === "error") {
                receivedResult = true;
                onError(new Error(data.message));
              }
            } catch (e) {
              console.error("Parse error:", e);
            }
          }
        }
      }

      // Stream ended without a result or error event — backend likely crashed
      if (!receivedResult) {
        onError(new Error("Koneksi ke server terputus. Silakan coba lagi."));
      }
    } catch (e: any) {
      onError(e);
    }
  },

  // ================================================================ //
  // Documents (Admin)
  // ================================================================ //

  async uploadDocument(file: File, category: string = "uncategorized"): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);

    const response = await authFetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = "Failed to upload document";
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {}
      throw new Error(errorMessage);
    }

    return response.json();
  },

  async getWorkflowStatus(workflowId: string): Promise<WorkflowStatusResponse> {
    const response = await authFetch(`${API_BASE_URL}/workflows/${workflowId}`);
    if (!response.ok) throw new Error("Failed to fetch workflow status");
    return response.json();
  },

  async getDocuments(): Promise<Document[]> {
    const response = await authFetch(`${API_BASE_URL}/documents`);
    if (!response.ok) throw new Error("Failed to fetch documents");
    return response.json();
  },

  async deleteDocument(id: string): Promise<void> {
    const response = await authFetch(
      `${API_BASE_URL}/documents/${id}`,
      { method: "DELETE" }
    );
    if (!response.ok) throw new Error("Failed to delete document");
    return response.json();
  },

  // ================================================================ //
  // Metrics (Admin)
  // ================================================================ //

  async getMetrics(): Promise<Metrics> {
    const response = await authFetch(`${API_BASE_URL}/metrics`);
    if (!response.ok) throw new Error("Failed to fetch metrics");
    return response.json();
  },

  // ================================================================ //
  // Sessions (Chat History)
  // ================================================================ //

  async getSessions(): Promise<Session[]> {
    const response = await authFetch(`${API_BASE_URL}/sessions`);
    if (!response.ok) throw new Error("Failed to fetch sessions");
    return response.json();
  },

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    const response = await authFetch(`${API_BASE_URL}/sessions/${sessionId}/messages`);
    if (!response.ok) throw new Error("Failed to fetch messages");
    return response.json();
  },

  async deleteSession(sessionId: string): Promise<void> {
    await authFetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: "DELETE",
    });
  },

  // ================================================================ //
  // Users (Admin)
  // ================================================================ //

  async getUsers(): Promise<UserData[]> {
    const response = await authFetch(`${API_BASE_URL}/users`);
    if (!response.ok) throw new Error("Failed to fetch users");
    return response.json();
  },

  async createUser(data: {
    email: string;
    password: string;
    full_name: string;
    role: string;
  }): Promise<UserData> {
    const response = await authFetch(`${API_BASE_URL}/users`, {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to create user");
    }
    return response.json();
  },

  async updateUser(
    id: string,
    data: { full_name?: string; role?: string; is_active?: boolean }
  ): Promise<UserData> {
    const response = await authFetch(`${API_BASE_URL}/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to update user");
    }
    return response.json();
  },

  async deleteUser(id: string): Promise<void> {
    await authFetch(`${API_BASE_URL}/users/${id}`, {
      method: "DELETE",
    });
  },
};
