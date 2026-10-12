"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FolderPlus,
  BookOpen,
  ArrowRight,
  ShieldCheck,
  FileText,
  Sparkles,
  Search,
  Scale,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { Workspace } from "@/types/api";
import { formatDate } from "@/lib/utils";

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal / form state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadWorkspaces();
  }, []);

  async function loadWorkspaces() {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.listWorkspaces();
      setWorkspaces(data);
    } catch (err: any) {
      setError(err.message || "Failed to load workspaces. Is the backend server running?");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;

    try {
      setCreating(true);
      const created = await apiClient.createWorkspace(newTitle.trim(), newDesc.trim() || undefined);
      setWorkspaces([created, ...workspaces]);
      setNewTitle("");
      setNewDesc("");
      setShowCreateModal(false);
    } catch (err: any) {
      alert(`Error creating workspace: ${err.message}`);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-b from-indigo-950/40 via-slate-900/60 to-slate-950 border border-slate-800/80 p-8 sm:p-12 shadow-2xl">
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <ShieldCheck className="h-4 w-4" />
            Evidence-First Architecture
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
            From Documents to{" "}
            <span className="bg-gradient-to-r from-indigo-400 via-indigo-300 to-violet-400 bg-clip-text text-transparent">
              Verifiable Answers
            </span>
          </h1>
          <p className="text-slate-400 text-base sm:text-lg leading-relaxed">
            Investigate collections of PDF reports and papers. Ask questions with guaranteed
            page-level citations, inspect verbatim evidence, and compare claims across documents.
          </p>

          <div className="pt-2 flex flex-wrap gap-4">
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/30 hover:shadow-indigo-600/50 hover:scale-[1.02]"
            >
              <FolderPlus className="h-4 w-4" />
              New Workspace
            </button>
          </div>
        </div>

        {/* Decorative Grid Icons */}
        <div className="hidden lg:grid grid-cols-2 gap-4 absolute right-12 top-1/2 -translate-y-1/2 opacity-25 pointer-events-none">
          <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20">
            <Search className="h-10 w-10 text-indigo-400" />
          </div>
          <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20">
            <Scale className="h-10 w-10 text-violet-400" />
          </div>
        </div>
      </div>

      {/* Workspaces Section */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Active Workspaces</h2>
            <p className="text-sm text-slate-400">Select a workspace to investigate documents</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="text-sm font-medium text-indigo-400 hover:text-indigo-300 flex items-center gap-1.5"
          >
            <FolderPlus className="h-4 w-4" />
            Add Workspace
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="h-44 rounded-2xl bg-slate-900/60 border border-slate-800 animate-pulse"
              />
            ))}
          </div>
        ) : error ? (
          <div className="p-6 rounded-2xl bg-rose-950/20 border border-rose-900/40 text-center space-y-3">
            <p className="text-rose-400 text-sm font-medium">{error}</p>
            <button
              onClick={loadWorkspaces}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-white"
            >
              Retry Connection
            </button>
          </div>
        ) : workspaces.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-4">
            <div className="h-12 w-12 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
              <BookOpen className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold text-white">No Workspaces Found</h3>
            <p className="text-sm text-slate-400 max-w-md mx-auto">
              Get started by creating your first document workspace for grounded Q&A and cross-document comparison.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors"
            >
              <FolderPlus className="h-4 w-4" />
              Create First Workspace
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {workspaces.map((ws) => (
              <Link
                key={ws.id}
                href={`/workspaces/${ws.id}`}
                className="group relative p-6 rounded-2xl bg-slate-900/70 border border-slate-800/80 hover:border-indigo-500/50 hover:bg-slate-900 transition-all duration-200 flex flex-col justify-between space-y-4 hover:shadow-xl hover:shadow-indigo-500/5"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:bg-indigo-500 group-hover:text-white transition-colors">
                      <BookOpen className="h-5 w-5" />
                    </div>
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700/60 flex items-center gap-1.5">
                      <FileText className="h-3 w-3 text-indigo-400" />
                      {ws.document_count} {ws.document_count === 1 ? "Doc" : "Docs"}
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-white group-hover:text-indigo-300 transition-colors line-clamp-1">
                    {ws.title}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                    {ws.description || "No description provided."}
                  </p>
                </div>

                <div className="pt-4 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-500">
                  <span>{formatDate(ws.created_at)}</span>
                  <span className="flex items-center gap-1 font-semibold text-indigo-400 group-hover:translate-x-1 transition-transform">
                    Enter <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Create Workspace Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-6">
            <div>
              <h3 className="text-lg font-bold text-white">Create New Workspace</h3>
              <p className="text-xs text-slate-400 mt-1">
                A workspace organizes a related collection of documents and search queries.
              </p>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Workspace Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Q3 Earnings Analysis"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Description (Optional)
                </label>
                <textarea
                  rows={3}
                  placeholder="Notes about the documents in this workspace..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors resize-none"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 text-sm transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !newTitle.trim()}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm transition-colors shadow-lg shadow-indigo-600/30"
                >
                  {creating ? "Creating..." : "Create Workspace"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
