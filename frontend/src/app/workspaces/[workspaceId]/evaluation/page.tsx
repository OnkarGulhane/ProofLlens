"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ShieldCheck,
  Play,
  RotateCw,
  ArrowLeft,
  FileText,
  GitCompare,
  BarChart3,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Layers,
  Sparkles,
  Award,
  ChevronRight,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { Workspace, EvaluationRun, EvaluationCaseResult } from "@/types/api";

export default function WorkspaceEvaluationPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.workspaceId as string;

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [evalRuns, setEvalRuns] = useState<EvaluationRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [wsData, runs] = await Promise.all([
          apiClient.getWorkspace(workspaceId),
          apiClient.listEvaluations(workspaceId),
        ]);
        setWorkspace(wsData);
        setEvalRuns(runs);
        if (runs.length > 0) {
          setSelectedRun(runs[0]);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load workspace evaluations.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [workspaceId]);

  async function handleRunEvaluation() {
    try {
      setRunning(true);
      setError(null);
      const newRun = await apiClient.runEvaluation(workspaceId, {
        suite_name: "ProofLens Benchmark Suite v1",
      });
      setEvalRuns((prev) => [newRun, ...prev]);
      setSelectedRun(newRun);
    } catch (err: any) {
      setError(err.message || "Failed to execute evaluation suite.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-30 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            href="/"
            className="flex items-center space-x-2 text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-xs uppercase font-semibold tracking-wider">Workspaces</span>
          </Link>
          <span className="text-slate-700">/</span>
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-200">{workspace?.title || "Workspace"}</span>
            <span className="text-xs bg-slate-800 text-slate-400 border border-slate-700/60 px-2 py-0.5 rounded-full">
              Evaluation
            </span>
          </div>
        </div>

        {/* Workspace Navigation Pills */}
        <div className="flex items-center space-x-2">
          <Link
            href={`/workspaces/${workspaceId}`}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Q&A & Library</span>
          </Link>
          <Link
            href={`/workspaces/${workspaceId}/compare`}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition"
          >
            <GitCompare className="w-3.5 h-3.5" />
            <span>Compare Matrix</span>
          </Link>
          <div className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Benchmark Evaluation</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 flex flex-col space-y-8">
        {/* Hero Header */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 relative overflow-hidden backdrop-blur">
          <div className="absolute -top-24 -right-24 w-80 h-80 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="relative flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2 max-w-2xl">
              <div className="flex items-center space-x-2">
                <span className="bg-sky-500/10 text-sky-400 text-xs font-medium px-2.5 py-0.5 rounded-full border border-sky-500/20 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Quantitative Assurance Gate
                </span>
                <span className="text-xs text-slate-500">Suite v1.0</span>
              </div>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Benchmark Evaluation & Epistemic Audit
              </h1>
              <p className="text-sm text-slate-400 leading-relaxed">
                Executes standardized test suites measuring Retrieval Hit Rate (Target &ge;85%),
                Server-Side Citation Validity (100%), and Zero-Hallucination Negative Abstention Accuracy (100%).
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={handleRunEvaluation}
                disabled={running}
                className="flex items-center space-x-2 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 text-white font-medium px-5 py-2.5 rounded-xl shadow-lg shadow-sky-600/20 transition hover:scale-[1.02] active:scale-[0.98] disabled:cursor-not-allowed"
              >
                {running ? (
                  <>
                    <RotateCw className="w-4 h-4 animate-spin" />
                    <span>Executing Suite...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    <span>Run Benchmark Evaluation</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm rounded-xl flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Quantitative Metrics Cards */}
        {selectedRun ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Retrieval Hit Rate */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span>Retrieval Hit Rate</span>
                <span className="text-slate-500 font-mono">Target &ge; 85%</span>
              </div>
              <div className="flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-white">
                  {(selectedRun.retrieval_hit_rate * 100).toFixed(1)}%
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                    selectedRun.retrieval_hit_rate >= 0.85
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  }`}
                >
                  {selectedRun.retrieval_hit_rate >= 0.85 ? "Target Met" : "Sub-Optimal"}
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, selectedRun.retrieval_hit_rate * 100)}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-400">
                Golden page passage retrieved in Top-5 candidates.
              </p>
            </div>

            {/* Citation Validity */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span>Citation Validity</span>
                <span className="text-slate-500 font-mono">Target 100%</span>
              </div>
              <div className="flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-white">
                  {(selectedRun.citation_validity_rate * 100).toFixed(1)}%
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                    selectedRun.citation_validity_rate === 1.0
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                  }`}
                >
                  {selectedRun.citation_validity_rate === 1.0 ? "100% Verified" : "Failed"}
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-sky-500 h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, selectedRun.citation_validity_rate * 100)}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-400">
                Server-validated provenance; 0 fake citations.
              </p>
            </div>

            {/* Abstention Accuracy */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span>Abstention Accuracy</span>
                <span className="text-slate-500 font-mono">Target 100%</span>
              </div>
              <div className="flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-white">
                  {(selectedRun.abstention_accuracy * 100).toFixed(1)}%
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                    selectedRun.abstention_accuracy === 1.0
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                  }`}
                >
                  {selectedRun.abstention_accuracy === 1.0 ? "Zero Hallucination" : "Failed"}
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(100, selectedRun.abstention_accuracy * 100)}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-400">
                Explicit abstention on unanswerable/adversarial queries.
              </p>
            </div>

            {/* Total Passed Cases */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span>Test Suite Score</span>
                <span className="text-slate-500 font-mono">Deterministic</span>
              </div>
              <div className="flex items-baseline space-x-2">
                <span className="text-3xl font-extrabold text-white">
                  {selectedRun.passed_cases}/{selectedRun.total_cases}
                </span>
                <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-md font-medium">
                  {((selectedRun.passed_cases / selectedRun.total_cases) * 100).toFixed(0)}% Pass
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-teal-500 h-1.5 rounded-full transition-all duration-500"
                  style={{
                    width: `${(selectedRun.passed_cases / selectedRun.total_cases) * 100}%`,
                  }}
                />
              </div>
              <p className="text-[11px] text-slate-400">
                All benchmark test cases executed cleanly.
              </p>
            </div>
          </div>
        ) : (
          <div className="border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-3">
            <Award className="w-12 h-12 text-slate-600 mx-auto" />
            <h3 className="text-base font-semibold text-slate-300">No Benchmark Runs Recorded Yet</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Click &quot;Run Benchmark Evaluation&quot; to test grounded retrieval, citation verification, and
              abstention accuracy.
            </p>
          </div>
        )}

        {/* Detailed Test Cases Table */}
        {selectedRun && selectedRun.raw_results?.cases && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur flex flex-col">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <h2 className="text-sm font-semibold text-white">Benchmark Test Case Audit Log</h2>
                <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full">
                  {selectedRun.raw_results.cases.length} Cases
                </span>
              </div>
              <span className="text-xs text-slate-500">
                Run ID: <span className="font-mono">{selectedRun.id.slice(0, 8)}...</span>
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-6 font-semibold">Case ID</th>
                    <th className="py-3 px-6 font-semibold">Category</th>
                    <th className="py-3 px-6 font-semibold">Query / Probe</th>
                    <th className="py-3 px-6 font-semibold">Status</th>
                    <th className="py-3 px-6 font-semibold">Latency</th>
                    <th className="py-3 px-6 font-semibold">Verification Audit Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {selectedRun.raw_results.cases.map((c: EvaluationCaseResult) => (
                    <tr key={c.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 px-6 font-mono font-medium text-slate-200">
                        {c.id}
                      </td>
                      <td className="py-3.5 px-6">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
                            c.type === "POSITIVE"
                              ? "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                              : c.type === "NEGATIVE"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              : "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                          }`}
                        >
                          {c.type}
                        </span>
                      </td>
                      <td className="py-3.5 px-6 max-w-sm">
                        <p className="text-slate-200 font-medium truncate">{c.query}</p>
                      </td>
                      <td className="py-3.5 px-6">
                        <div className="flex items-center space-x-1.5">
                          {c.status === "PASS" ? (
                            <>
                              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                              <span className="font-semibold text-emerald-400">PASS</span>
                            </>
                          ) : (
                            <>
                              <XCircle className="w-4 h-4 text-rose-400" />
                              <span className="font-semibold text-rose-400">FAIL</span>
                            </>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-6 font-mono text-slate-400">
                        {c.latency_ms} ms
                      </td>
                      <td className="py-3.5 px-6 text-slate-400 max-w-md">
                        <span className="line-clamp-2">{c.notes}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Previous Runs History */}
        {evalRuns.length > 1 && (
          <div className="space-y-3">
            <h3 className="text-xs uppercase font-semibold tracking-wider text-slate-400">
              Evaluation History
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {evalRuns.map((run) => (
                <button
                  key={run.id}
                  onClick={() => setSelectedRun(run)}
                  className={`text-left p-4 rounded-xl border transition ${
                    selectedRun?.id === run.id
                      ? "bg-sky-500/10 border-sky-500/30 text-white"
                      : "bg-slate-900/40 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-slate-200">
                      {run.suite_name}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {new Date(run.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <div className="flex items-center space-x-3 text-xs">
                    <span>
                      Pass:{" "}
                      <strong className="text-slate-200">
                        {run.passed_cases}/{run.total_cases}
                      </strong>
                    </span>
                    <span>
                      Retrieval:{" "}
                      <strong className="text-emerald-400">
                        {(run.retrieval_hit_rate * 100).toFixed(0)}%
                      </strong>
                    </span>
                    <span>
                      Abstain:{" "}
                      <strong className="text-indigo-400">
                        {(run.abstention_accuracy * 100).toFixed(0)}%
                      </strong>
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
