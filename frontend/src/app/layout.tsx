import type { Metadata } from "next";
import Link from "next/link";
import { FileSearch, Sparkles, BookOpen } from "lucide-react";
import "./globals.css";

export const metadata: Metadata = {
  title: "ProofLens AI — From Documents to Verifiable Answers",
  description: "Evidence-first document intelligence platform for grounded Q&A, citation verification, and cross-document comparison.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="flex flex-col min-h-screen bg-slate-950 text-slate-100">
        {/* Top Navbar */}
        <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
          <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-200">
                <FileSearch className="h-5 w-5 text-white" />
              </div>
              <div>
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                  ProofLens<span className="text-indigo-400"> AI</span>
                </span>
                <span className="hidden sm:inline-block ml-2 text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Verifiable Evidence
                </span>
              </div>
            </Link>

            <nav className="flex items-center gap-4 text-sm font-medium">
              <Link
                href="/"
                className="text-slate-300 hover:text-white hover:bg-slate-900/80 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
              >
                <BookOpen className="h-4 w-4 text-slate-400" />
                Workspaces
              </Link>
            </nav>
          </div>
        </header>

        {/* Main Body */}
        <main className="flex-1 flex flex-col">{children}</main>

        {/* Footer */}
        <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
            <span>ProofLens AI — Evidence-First Document Intelligence</span>
            <span className="text-slate-600">FastAPI &bull; PostgreSQL 17 + pgvector &bull; Next.js 14</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
