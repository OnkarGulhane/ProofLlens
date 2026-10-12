export interface Workspace {
  id: string;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  document_count: number;
}

export interface DocumentItem {
  id: string;
  workspace_id: string;
  filename: string;
  file_size_bytes: number;
  total_pages: number;
  chunk_count: number;
  status: "PENDING" | "PARSING" | "INDEXING" | "READY" | "FAILED" | "UNSUPPORTED";
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentPageItem {
  id: string;
  page_number: number;
  character_count: number;
  raw_text: string;
  created_at: string;
}

export interface DocumentDetail extends DocumentItem {
  pages: DocumentPageItem[];
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  chunk_index: number;
  content: string;
  similarity_score: number;
  rank: number;
}

export interface Citation {
  citation_id: string;
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  cited_excerpt: string;
  verification_status: "VERIFIED" | "PARTIAL" | "UNVERIFIED";
}

export interface QueryResponse {
  query_run_id: string;
  workspace_id: string;
  question: string;
  answer: string;
  is_abstained: boolean;
  abstention_reason: string | null;
  citations: Citation[];
  retrieved_evidence: RetrievedChunk[];
}

export interface DocumentFinding {
  document_id: string;
  document_name: string;
  summary: string;
  citations: Citation[];
}

export type ConsensusStatus = "AGREEMENT" | "DIFFERENCE" | "CONTRADICTION" | "INCOMPARABLE";

export interface ComparisonSynthesis {
  consensus: ConsensusStatus;
  analysis: string;
}

export interface ComparisonResponse {
  comparison_run_id: string;
  workspace_id: string;
  topic: string;
  documents_analyzed: string[];
  findings: DocumentFinding[];
  synthesis: ComparisonSynthesis;
}
