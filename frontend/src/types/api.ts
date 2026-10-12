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

export interface EvaluationCaseResult {
  id: string;
  type: "POSITIVE" | "NEGATIVE" | "INJECTION";
  query: string;
  status: "PASS" | "FAIL";
  retrieval_hit: boolean | null;
  is_abstained: boolean;
  citations_count: number;
  latency_ms: number;
  notes: string;
}

export interface EvaluationSummary {
  total_positive_cases: number;
  retrieval_hits: number;
  total_citations: number;
  valid_citations: number;
  total_negative_cases: number;
  correct_abstentions: number;
}

export interface EvaluationRunRequest {
  suite_name?: string;
}

export interface EvaluationRun {
  id: string;
  workspace_id: string;
  suite_name: string;
  total_cases: number;
  passed_cases: number;
  retrieval_hit_rate: number;
  citation_validity_rate: number;
  abstention_accuracy: number;
  raw_results: {
    cases: EvaluationCaseResult[];
    summary: EvaluationSummary;
  };
  created_at: string;
}

