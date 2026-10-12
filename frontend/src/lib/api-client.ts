import {
  Workspace,
  DocumentItem,
  DocumentDetail,
  QueryResponse,
  ComparisonResponse,
  EvaluationRun,
  EvaluationRunRequest,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

class ApiClient {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
      ...options?.headers,
    };

    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorMsg = `API Error ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        errorMsg = errorJson.message || errorJson.detail || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }

    if (res.status === 204) {
      return {} as T;
    }

    return (await res.json()) as T;
  }

  // Workspaces
  async listWorkspaces(): Promise<Workspace[]> {
    return this.request<Workspace[]>("/workspaces");
  }

  async createWorkspace(title: string, description?: string): Promise<Workspace> {
    return this.request<Workspace>("/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description }),
    });
  }

  async getWorkspace(id: string): Promise<Workspace> {
    return this.request<Workspace>(`/workspaces/${id}`);
  }

  async deleteWorkspace(id: string): Promise<void> {
    return this.request<void>(`/workspaces/${id}`, {
      method: "DELETE",
    });
  }

  // Documents
  async listDocuments(workspaceId: string): Promise<DocumentItem[]> {
    return this.request<DocumentItem[]>(`/workspaces/${workspaceId}/documents`);
  }

  async getDocument(workspaceId: string, documentId: string): Promise<DocumentDetail> {
    return this.request<DocumentDetail>(`/workspaces/${workspaceId}/documents/${documentId}`);
  }

  async uploadDocument(workspaceId: string, file: File): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append("file", file);

    return this.request<DocumentItem>(`/workspaces/${workspaceId}/documents`, {
      method: "POST",
      body: formData,
    });
  }

  async deleteDocument(workspaceId: string, documentId: string): Promise<void> {
    return this.request<void>(`/workspaces/${workspaceId}/documents/${documentId}`, {
      method: "DELETE",
    });
  }

  // Q&A
  async submitQuery(
    workspaceId: string,
    question: string,
    options?: {
      documentIds?: string[];
      similarityThreshold?: number;
      topK?: number;
    }
  ): Promise<QueryResponse> {
    return this.request<QueryResponse>(`/workspaces/${workspaceId}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        document_ids: options?.documentIds,
        similarity_threshold: options?.similarityThreshold ?? 0.65,
        top_k: options?.topK ?? 5,
      }),
    });
  }

  // Cross-Document Comparison
  async compareDocuments(
    workspaceId: string,
    topic: string,
    documentIds: string[]
  ): Promise<ComparisonResponse> {
    return this.request<ComparisonResponse>(`/workspaces/${workspaceId}/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic,
        document_ids: documentIds,
      }),
    });
  }

  // Benchmark Evaluations
  async runEvaluation(
    workspaceId: string,
    payload?: EvaluationRunRequest
  ): Promise<EvaluationRun> {
    return this.request<EvaluationRun>(`/workspaces/${workspaceId}/evaluations/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload ?? {}),
    });
  }

  async listEvaluations(workspaceId: string): Promise<EvaluationRun[]> {
    return this.request<EvaluationRun[]>(`/workspaces/${workspaceId}/evaluations`);
  }

  async getEvaluation(workspaceId: string, evaluationId: string): Promise<EvaluationRun> {
    return this.request<EvaluationRun>(
      `/workspaces/${workspaceId}/evaluations/${evaluationId}`
    );
  }
}

export const apiClient = new ApiClient();

