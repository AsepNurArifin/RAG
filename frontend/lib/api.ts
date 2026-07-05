import { QueryResponse } from "../types";

// Base URL for the backend API.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

/**
 * Get auth token from localStorage.
 */
function getAuthHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("emind_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Authenticated fetch wrapper. Adds JWT token automatically.
 */
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = { ...getAuthHeaders(), ...options.headers } as Record<string, string>;

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (options.body instanceof FormData) {
    delete headers["Content-Type"];
  }

  return fetch(url, { ...options, headers });
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

  // ================================================================ //
  // Documents (Admin)
  // ================================================================ //

  async uploadDocument(file: File, category: string = "uncategorized") {
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

  async getDocuments(): Promise<any[]> {
    const response = await authFetch(`${API_BASE_URL}/documents`);
    if (!response.ok) throw new Error("Failed to fetch documents");
    return response.json();
  },

  async deleteDocument(id: string, filename: string): Promise<any> {
    const response = await authFetch(
      `${API_BASE_URL}/documents/${id}?filename=${encodeURIComponent(filename)}`,
      { method: "DELETE" }
    );
    if (!response.ok) throw new Error("Failed to delete document");
    return response.json();
  },

  // ================================================================ //
  // Metrics (Admin)
  // ================================================================ //

  async getMetrics(): Promise<any> {
    const response = await authFetch(`${API_BASE_URL}/metrics`);
    if (!response.ok) throw new Error("Failed to fetch metrics");
    return response.json();
  },

  // ================================================================ //
  // Sessions (Chat History)
  // ================================================================ //

  async getSessions(): Promise<any[]> {
    const response = await authFetch(`${API_BASE_URL}/sessions`);
    if (!response.ok) throw new Error("Failed to fetch sessions");
    return response.json();
  },

  async getSessionMessages(sessionId: string): Promise<any[]> {
    const response = await authFetch(`${API_BASE_URL}/sessions/${sessionId}/messages`);
    if (!response.ok) throw new Error("Failed to fetch messages");
    return response.json();
  },

  async deleteSession(sessionId: string): Promise<any> {
    const response = await authFetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: "DELETE",
    });
    if (!response.ok) throw new Error("Failed to delete session");
    return response.json();
  },

  // ================================================================ //
  // Users (Admin)
  // ================================================================ //

  async getUsers(): Promise<any[]> {
    const response = await authFetch(`${API_BASE_URL}/users`);
    if (!response.ok) throw new Error("Failed to fetch users");
    return response.json();
  },

  async createUser(data: {
    email: string;
    password: string;
    full_name: string;
    role: string;
  }): Promise<any> {
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
  ): Promise<any> {
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

  async deleteUser(id: string): Promise<any> {
    const response = await authFetch(`${API_BASE_URL}/users/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to delete user");
    }
    return response.json();
  },
};
