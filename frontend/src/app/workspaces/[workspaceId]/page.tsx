"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  FileText,
  Upload,
  Trash2,
  Send,
  Sparkles,
  Scale,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Bookmark,
  Layers,
  SlidersHorizontal,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import {
  Workspace,
  DocumentItem,
  QueryResponse,
  Citation,
  RetrievedChunk,
} from "@/types/api";
import { formatBytes, formatDate } from "@/lib/utils";
import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";

export default function WorkspaceDetailPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;

  // Workspace & Documents State
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Q&A State
  const [question, setQuestion] = useState("");
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.65);
  const [topK, setTopK] = useState(5);
  const [showFilters, setShowFilters] = useState(false);

  // Evidence Drawer State
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [activeChunk, setActiveChunk] = useState<RetrievedChunk | null>(null);

  useEffect(() => {
    if (workspaceId) {
      loadData();
    }
  }, [workspaceId]);

  async function loadData() {
    try {
      setLoading(true);
      const [ws, docs] = await Promise.all([
        apiClient.getWorkspace(workspaceId),
        apiClient.listDocuments(workspaceId),
      ]);
      setWorkspace(ws);
      setDocuments(docs);
    } catch (err: any) {
      alert(`Failed to load workspace data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Only PDF documents are supported.");
      return;
    }

    try {
      setUploading(true);
      await apiClient.uploadDocument(workspaceId, file);
      // Reload documents
      const docs = await apiClient.listDocuments(workspaceId);
      setDocuments(docs);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteDocument(docId: string, filename: string) {
    if (!confirm(`Are you sure you want to delete '${filename}'?`)) return;

    try {
      await apiClient.deleteDocument(workspaceId, docId);
      setDocuments(documents.filter((d) => d.id !== docId));
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  }

  async function handleQuerySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || queryLoading) return;

    try {
      setQueryLoading(true);
      setQueryResult(null);
      const res = await apiClient.submitQuery(workspaceId, question.trim(), {
        documentIds: selectedDocIds.length > 0 ? selectedDocIds : undefined,
        similarityThreshold,
        topK,
      });
      setQueryResult(res);
    } catch (err: any) {
      alert(`Query failed: ${err.message}`);
    } finally {
      setQueryLoading(false);
    }
  }

  function openCitation(citation: Citation) {
    setActiveCitation(citation);
    setActiveChunk(null);
    setDrawerOpen(true);
  }

  function openChunk(chunk: RetrievedChunk) {
    setActiveChunk(chunk);
    setActiveCitation(null);
    setDrawerOpen(true);
  }

  return (
    <div className="flex-1 flex flex-col max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Workspace Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-slate-400 mb-1">
            <Link href="/" className="hover:text-indigo-400">
              Workspaces
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span className="text-slate-200">{workspace?.title || "Workspace"}</span>
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            {workspace?.title || "Document Workspace"}
          </h1>
          {workspace?.description && (
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">{workspace.description}</p>
          )}
        </div>

        {/* Action Button: Cross-Doc Compare */}
        <div className="flex items-center gap-3">
          <Link
            href={`/workspaces/${workspaceId}/compare`}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700/80 hover:border-indigo-500/60 hover:bg-slate-800 text-slate-200 text-xs font-semibold transition-all shadow-sm"
          >
            <Scale className="h-4 w-4 text-indigo-400" />
            Cross-Document Compare
          </Link>
        </div>
      </div>

      {/* Main Split-Pane Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1 items-start">
        {/* Left Column: Document Library & Upload Dropzone (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Layers className="h-4 w-4 text-indigo-400" />
                Document Library ({documents.length})
              </h2>
              <button
                onClick={loadData}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                title="Refresh Library"
              >
                <RefreshCw className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Upload Dropzone */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className="group cursor-pointer p-6 rounded-xl border-2 border-dashed border-slate-800 hover:border-indigo-500/60 bg-slate-950/50 hover:bg-slate-950/80 transition-all text-center space-y-2"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={handleFileUpload}
                disabled={uploading}
              />
              <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto text-indigo-400 group-hover:scale-105 transition-transform">
                <Upload className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs font-medium text-slate-200">
                  {uploading ? "Ingesting & Embedding..." : "Click or drag PDF to ingest"}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">Max 10MB &bull; Page-Aware Provenance</p>
              </div>
            </div>

            {/* Document List */}
            <div className="space-y-2.5 max-h-[480px] overflow-y-auto pr-1">
              {documents.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-6">
                  No documents in this workspace yet. Upload a PDF to start asking grounded questions.
                </p>
              ) : (
                documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-850 hover:border-slate-700 transition-colors flex items-center justify-between gap-3 group"
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="h-8 w-8 rounded-lg bg-indigo-500/10 flex-shrink-0 flex items-center justify-center text-indigo-400">
                        <FileText className="h-4 w-4" />
                      </div>
                      <div className="overflow-hidden">
                        <h4 className="text-xs font-semibold text-slate-200 truncate" title={doc.filename}>
                          {doc.filename}
                        </h4>
                        <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-400">
                          <span>{doc.total_pages} {doc.total_pages === 1 ? "page" : "pages"}</span>
                          <span>&bull;</span>
                          <span>{doc.chunk_count} chunks</span>
                          <span>&bull;</span>
                          <span>{formatBytes(doc.file_size_bytes)}</span>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition-all flex-shrink-0"
                      title="Delete document"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Grounded Q&A Interface (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Question Submission Card */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-indigo-400" />
                Evidence-Grounded Inquiry
              </h2>
              <button
                type="button"
                onClick={() => setShowFilters(!showFilters)}
                className="text-xs font-medium text-slate-400 hover:text-indigo-400 flex items-center gap-1.5"
              >
                <SlidersHorizontal className="h-3.5 w-3.5" />
                {showFilters ? "Hide Parameters" : "Tuning Parameters"}
              </button>
            </div>

            {/* Optional Tuning Controls */}
            {showFilters && (
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">
                    Similarity Threshold: {similarityThreshold}
                  </label>
                  <input
                    type="range"
                    min="0.3"
                    max="0.95"
                    step="0.05"
                    value={similarityThreshold}
                    onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                  <span className="text-[10px] text-slate-500">
                    Passages below this score are discarded to avoid speculation.
                  </span>
                </div>
                <div>
                  <label className="block text-slate-400 font-medium mb-1">
                    Candidate Passages (Top-K): {topK}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="1"
                    value={topK}
                    onChange={(e) => setTopK(parseInt(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                  <span className="text-[10px] text-slate-500">
                    Maximum candidate evidence chunks retrieved.
                  </span>
                </div>
              </div>
            )}

            {/* Input Form */}
            <form onSubmit={handleQuerySubmit} className="space-y-3">
              <div className="relative">
                <textarea
                  rows={3}
                  required
                  placeholder="Ask a question across the documents in this workspace..."
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleQuerySubmit(e);
                    }
                  }}
                  className="w-full p-4 pr-12 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors resize-none"
                />
                <button
                  type="submit"
                  disabled={queryLoading || !question.trim() || documents.length === 0}
                  className="absolute bottom-3 right-3 p-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white transition-all shadow-md shadow-indigo-600/20"
                  title="Submit query"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
              <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                Answers cite verified document and page numbers. Unanswerable queries trigger deterministic abstention.
              </p>
            </form>
          </div>

          {/* Results Area */}
          {queryLoading && (
            <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800 text-center space-y-3 animate-pulse">
              <div className="h-8 w-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin mx-auto" />
              <p className="text-sm font-medium text-slate-300">
                Retrieving evidence passages & validating citations...
              </p>
            </div>
          )}

          {queryResult && (
            <div className="space-y-6">
              {/* Answer Card */}
              <div
                className={`p-6 rounded-2xl border ${
                  queryResult.is_abstained
                    ? "bg-amber-950/20 border-amber-900/40"
                    : "bg-slate-900/70 border-slate-800"
                } space-y-4 shadow-xl`}
              >
                {/* Header Badge */}
                <div className="flex items-center justify-between">
                  {queryResult.is_abstained ? (
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      <ShieldAlert className="h-3.5 w-3.5" />
                      Insufficient Evidence (Abstained)
                    </div>
                  ) : (
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Grounded & Verified
                    </div>
                  )}

                  {queryResult.citations.length > 0 && (
                    <span className="text-xs text-slate-400">
                      {queryResult.citations.length} Verified {queryResult.citations.length === 1 ? "Citation" : "Citations"}
                    </span>
                  )}
                </div>

                {/* Answer Text */}
                <div className="text-slate-100 text-sm leading-relaxed whitespace-pre-wrap">
                  {queryResult.answer}
                </div>

                {/* Abstention Explanation Callout */}
                {queryResult.is_abstained && queryResult.abstention_reason && (
                  <div className="p-3.5 rounded-xl bg-amber-900/10 border border-amber-800/30 text-xs text-amber-300/90 leading-relaxed">
                    <p className="font-semibold text-amber-200 mb-0.5">Abstention Policy Notice:</p>
                    {queryResult.abstention_reason}
                  </div>
                )}

                {/* Clickable Citation Badges */}
                {queryResult.citations.length > 0 && (
                  <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold text-slate-400 mr-1">Cited Evidence:</span>
                    {queryResult.citations.map((cite, idx) => (
                      <button
                        key={idx}
                        onClick={() => openCitation(cite)}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 transition-all hover:scale-105"
                      >
                        <Bookmark className="h-3 w-3 text-indigo-400" />
                        {cite.document_name} &bull; Page {cite.page_number}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Retrieved Candidate Passages Drawer / List */}
              {queryResult.retrieved_evidence.length > 0 && (
                <div className="p-5 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Retrieved Candidate Passages ({queryResult.retrieved_evidence.length})
                  </h3>
                  <div className="grid grid-cols-1 gap-3">
                    {queryResult.retrieved_evidence.map((chunk) => (
                      <div
                        key={chunk.chunk_id}
                        onClick={() => openChunk(chunk)}
                        className="cursor-pointer p-3.5 rounded-xl bg-slate-950/60 border border-slate-850 hover:border-indigo-500/40 hover:bg-slate-950 transition-all space-y-2"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                            <FileText className="h-3.5 w-3.5 text-indigo-400" />
                            {chunk.document_name} &bull; Page {chunk.page_number}
                          </span>
                          <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                            {(chunk.similarity_score * 100).toFixed(1)}% Match
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                          {chunk.content}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Slide-over Evidence Inspector Drawer */}
      <EvidenceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        citation={activeCitation}
        chunk={activeChunk}
      />
    </div>
  );
}
