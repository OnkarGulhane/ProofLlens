"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Scale,
  ChevronRight,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Bookmark,
  Sparkles,
  ArrowLeft,
  XCircle,
  HelpCircle,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import {
  Workspace,
  DocumentItem,
  ComparisonResponse,
  Citation,
  ConsensusStatus,
} from "@/types/api";
import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";

export default function ComparePage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [topic, setTopic] = useState("");
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [comparing, setComparing] = useState(false);
  const [comparisonResult, setComparisonResult] = useState<ComparisonResponse | null>(null);

  // Evidence Drawer State
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

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
      // Auto-select first two documents if available
      if (docs.length >= 2) {
        setSelectedDocIds([docs[0].id, docs[1].id]);
      }
    } catch (err: any) {
      alert(`Error loading data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function toggleDocSelection(docId: string) {
    if (selectedDocIds.includes(docId)) {
      setSelectedDocIds(selectedDocIds.filter((id) => id !== docId));
    } else {
      setSelectedDocIds([...selectedDocIds, docId]);
    }
  }

  async function handleCompare(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim() || selectedDocIds.length < 2 || comparing) return;

    try {
      setComparing(true);
      setComparisonResult(null);
      const res = await apiClient.compareDocuments(workspaceId, topic.trim(), selectedDocIds);
      setComparisonResult(res);
    } catch (err: any) {
      alert(`Comparison failed: ${err.message}`);
    } finally {
      setComparing(false);
    }
  }

  function getConsensusBadge(consensus: ConsensusStatus) {
    switch (consensus) {
      case "AGREEMENT":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-4 w-4" /> Agreement Across Sources
          </span>
        );
      case "DIFFERENCE":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Scale className="h-4 w-4" /> Distinct Perspectives / Scope
          </span>
        );
      case "CONTRADICTION":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="h-4 w-4" /> Contradiction Detected
          </span>
        );
      case "INCOMPARABLE":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <HelpCircle className="h-4 w-4" /> Incomparable Scopes
          </span>
        );
    }
  }

  return (
    <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8">
      {/* Top Breadcrumb & Navigation */}
      <div className="flex items-center justify-between pb-6 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-slate-400 mb-1">
            <Link href="/" className="hover:text-indigo-400">
              Workspaces
            </Link>
            <ChevronRight className="h-3 w-3" />
            <Link href={`/workspaces/${workspaceId}`} className="hover:text-indigo-400">
              {workspace?.title || "Workspace"}
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span className="text-slate-200">Comparison Matrix</span>
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <Scale className="h-6 w-6 text-indigo-400" />
            Cross-Document Comparison
          </h1>
        </div>

        <Link
          href={`/workspaces/${workspaceId}`}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Q&A
        </Link>
      </div>

      {/* Comparison Setup Form */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
        <form onSubmit={handleCompare} className="space-y-6">
          {/* Topic Input */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
              Topic or Claim to Compare
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Cloud migration timeline and budgetary impact"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
            />
          </div>

          {/* Document Picker */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-2">
              Select Documents to Compare (Min 2)
            </label>
            {documents.length < 2 ? (
              <p className="text-xs text-amber-400 bg-amber-500/10 p-3 rounded-xl border border-amber-500/20">
                You need at least 2 documents in this workspace to run a comparison. Please upload more documents first.
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {documents.map((doc) => {
                  const isSelected = selectedDocIds.includes(doc.id);
                  return (
                    <div
                      key={doc.id}
                      onClick={() => toggleDocSelection(doc.id)}
                      className={`cursor-pointer p-3.5 rounded-xl border transition-all flex items-center justify-between gap-3 ${
                        isSelected
                          ? "bg-indigo-950/40 border-indigo-500/60 text-white"
                          : "bg-slate-950/60 border-slate-850 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center gap-2.5 overflow-hidden">
                        <FileText className={`h-4 w-4 flex-shrink-0 ${isSelected ? "text-indigo-400" : "text-slate-500"}`} />
                        <span className="text-xs font-medium truncate" title={doc.filename}>
                          {doc.filename}
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {}} // handled by parent div
                        className="rounded accent-indigo-500"
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Submit Action */}
          <div className="flex items-center justify-end">
            <button
              type="submit"
              disabled={comparing || !topic.trim() || selectedDocIds.length < 2}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/20"
            >
              <Sparkles className="h-4 w-4" />
              {comparing ? "Comparing Documents..." : "Run Side-by-Side Comparison"}
            </button>
          </div>
        </form>
      </div>

      {/* Comparison Loading Skeleton */}
      {comparing && (
        <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800 text-center space-y-4 animate-pulse">
          <div className="h-10 w-10 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-300">
            Extracting partitioned evidence and analyzing cross-document alignment...
          </p>
        </div>
      )}

      {/* Comparison Results View */}
      {comparisonResult && (
        <div className="space-y-6">
          {/* Synthesis Banner */}
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              {getConsensusBadge(comparisonResult.synthesis.consensus)}
              <span className="text-xs text-slate-400 font-medium">
                {comparisonResult.findings.length} Documents Analyzed
              </span>
            </div>

            <div className="text-slate-200 text-sm leading-relaxed">
              {comparisonResult.synthesis.analysis}
            </div>
          </div>

          {/* Side-by-Side Findings Matrix Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
            {comparisonResult.findings.map((finding) => (
              <div
                key={finding.document_id}
                className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between space-y-4 shadow-lg hover:border-slate-700 transition-colors"
              >
                <div>
                  <div className="flex items-center gap-3 pb-3 border-b border-slate-800">
                    <div className="h-9 w-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="overflow-hidden">
                      <h3 className="text-sm font-bold text-white truncate" title={finding.document_name}>
                        {finding.document_name}
                      </h3>
                      <p className="text-[11px] text-slate-400">Document Evidence Record</p>
                    </div>
                  </div>

                  <div className="text-slate-300 text-xs sm:text-sm leading-relaxed mt-4">
                    {finding.summary}
                  </div>
                </div>

                {finding.citations.length > 0 && (
                  <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center gap-2">
                    <span className="text-[11px] font-semibold text-slate-400">Citations:</span>
                    {finding.citations.map((cite, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setActiveCitation(cite);
                          setDrawerOpen(true);
                        }}
                        className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 transition-all"
                      >
                        <Bookmark className="h-3 w-3 text-indigo-400" />
                        Page {cite.page_number}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Drawer */}
      <EvidenceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        citation={activeCitation}
        chunk={null}
      />
    </div>
  );
}
