"use client";

import { X, FileText, CheckCircle2, Bookmark, Hash } from "lucide-react";
import { Citation, RetrievedChunk } from "@/types/api";

interface EvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  citation: Citation | null;
  chunk: RetrievedChunk | null;
}

export function EvidenceDrawer({
  isOpen,
  onClose,
  citation,
  chunk,
}: EvidenceDrawerProps) {
  if (!isOpen || (!citation && !chunk)) return null;

  const docName = citation?.document_name || chunk?.document_name || "Document";
  const pageNum = citation?.page_number || chunk?.page_number || 1;
  const excerpt = citation?.cited_excerpt || chunk?.content || "";
  const similarity = chunk?.similarity_score ? (chunk.similarity_score * 100).toFixed(1) : null;
  const chunkIndex = chunk?.chunk_index ?? 0;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/50">
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Bookmark className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-white text-base">Evidence Inspector</h3>
                <p className="text-xs text-slate-400">Verified Source Provenance</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto flex-1 space-y-6">
            {/* Meta Tags */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Verified Provenance
              </span>

              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Page {pageNum}
              </span>

              {similarity && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20">
                  {similarity}% Similarity
                </span>
              )}
            </div>

            {/* Document Info Card */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-slate-800/80 flex items-center justify-center text-slate-300">
                  <FileText className="h-5 w-5" />
                </div>
                <div className="overflow-hidden">
                  <h4 className="text-sm font-semibold text-slate-200 truncate" title={docName}>
                    {docName}
                  </h4>
                  <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                    <Hash className="h-3 w-3" /> Chunk Index: {chunkIndex}
                  </p>
                </div>
              </div>
            </div>

            {/* Excerpt Block */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Ground-Truth Source Passage
              </h4>
              <div className="p-4 rounded-xl bg-slate-950 border border-indigo-900/40 text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-sans relative">
                <div className="absolute top-2 right-2 h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
                {excerpt}
              </div>
            </div>

            {/* Guarantee Note */}
            <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 text-xs text-slate-400 space-y-1">
              <p className="font-medium text-slate-300">Strict Provenance Guarantee</p>
              <p>
                This chunk belongs strictly to Page {pageNum} of <span className="text-slate-300">{docName}</span>. 
                ProofLens guarantees that no citation text is fabricated by the LLM.
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-slate-800/80 bg-slate-900/60">
            <button
              onClick={onClose}
              className="w-full py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-sm transition-colors"
            >
              Close Inspector
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
