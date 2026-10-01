import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

// ─────────────────────────────────────────────
// Core Module Data
// ─────────────────────────────────────────────

const MODULES = [
  {
    to: "/chat",
    title: "Legal Chat Assistant",
    category: "Citation-Grounded Statutory RAG",
    desc: "Ask questions regarding your situation. Receive instant explanations grounded in verified Indian statutes, acts, and provisions.",
    badge: "Citation-Grounded",
    actionText: "Open Legal Chat",
  },
  {
    to: "/complaints",
    title: "Document & Complaint Studio",
    category: "Structured Drafting & PDF/DOCX Export",
    desc: "Draft, generate, and finalize structured legal complaints. Export formatted PDF and DOCX files ready for formal submission.",
    badge: "PDF & DOCX Export",
    actionText: "Open Document Studio",
  },
  {
    to: "/evidence",
    title: "Evidence Vault",
    category: "SHA-256 Fingerprint Verified Files",
    desc: "Organize documents, photographs, and media files with immutable SHA-256 fingerprint verification and evidence linking.",
    badge: "SHA-256 Verified",
    actionText: "Open Evidence Vault",
  },
];

const STATUTORY_DOMAINS = [
  { name: "Consumer Rights", act: "Consumer Protection Act 2019", icon: "⚖️" },
  { name: "Labour & Workplace", act: "Industrial Disputes & Factories Acts", icon: "🏢" },
  { name: "Women's Safety", act: "POSH Act 2013 & Domestic Violence Remedies", icon: "🛡️" },
  { name: "Educational Rights", act: "Right to Education & Fee Disputes", icon: "🎓" },
  { name: "Anti-Ragging", act: "UGC Anti-Ragging Regulations", icon: "📜" },
];

export default function DashboardPage() {
  const { user } = useAuth();

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="min-h-full px-6 py-8 sm:px-10 max-w-6xl mx-auto">
      {/* ── Executive Hero Card ── */}
      <div className="paper-surface p-8 sm:p-10 mb-8 border border-slate-200">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-teal-50 border border-teal-200 px-3 py-1 text-xs font-semibold text-teal-800 mb-3">
              <span className="h-2 w-2 rounded-full bg-teal-600" />
              {greeting} · Authorized Legal Workspace
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold font-serif-title text-slate-900 tracking-tight">
              Welcome, {user?.full_name?.split(" ")[0] || "User"}
            </h1>
            <p className="mt-2 text-sm text-slate-600 max-w-2xl leading-6">
              Your AI legal workspace is ready. Consult citation-grounded statutes, manage evidence with SHA-256 verification, and draft structured legal complaints.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link to="/chat" className="btn-teal text-sm py-2.5 px-5 shadow-xs">
              Start Legal Chat
            </Link>
            <Link to="/complaints" className="btn-outline-legal text-sm py-2.5 px-5">
              Draft Complaint
            </Link>
          </div>
        </div>
      </div>

      {/* ── Core Workspace Modules Grid ── */}
      <div className="mb-10">
        <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">
          Core Workspace Modules
        </p>
        <div className="grid gap-6 md:grid-cols-3">
          {MODULES.map(({ to, title, category, desc, badge, actionText }) => (
            <Link
              key={to}
              to={to}
              className="card-legal p-6 flex flex-col justify-between group hover:border-teal-600/50"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-bold text-teal-800 bg-teal-50 border border-teal-200 rounded-full px-2.5 py-0.5">
                    {badge}
                  </span>
                </div>
                <h2 className="text-lg font-bold text-slate-900 font-serif-title group-hover:text-teal-800 transition-colors">
                  {title}
                </h2>
                <p className="text-xs font-semibold text-slate-500 mt-0.5 mb-2">
                  {category}
                </p>
                <p className="text-xs text-slate-600 leading-5">
                  {desc}
                </p>
              </div>

              <div className="mt-6 flex items-center gap-1 text-xs font-bold text-teal-700 group-hover:gap-2 transition-all">
                <span>{actionText}</span>
                <span>→</span>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* ── Statutory Coverage ── */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-teal-700">
              Statutory Coverage
            </p>
            <h2 className="text-xl font-bold font-serif-title text-slate-900">
              Supported Legal Categories
            </h2>
          </div>
          <span className="text-xs font-semibold text-slate-600 bg-slate-100 border border-slate-200 px-3 py-1 rounded-full">
            5 Grounded Domains
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {STATUTORY_DOMAINS.map(({ name, act, icon }, idx) => (
            <div key={idx} className="card-legal p-4 flex flex-col justify-between">
              <div className="text-2xl mb-2">{icon}</div>
              <div>
                <h3 className="text-xs font-bold text-slate-900">{name}</h3>
                <p className="text-[11px] text-slate-500 mt-1 leading-4">{act}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Legal Disclaimer & Notice ── */}
      <div className="paper-surface p-6 bg-slate-50 border border-slate-200">
        <div className="flex items-start gap-3">
          <svg className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
          <div className="text-xs text-slate-700 leading-5">
            <span className="font-bold text-slate-900">Statutory Legal Information Grounding Notice: </span>
            Nyaya AI provides citation-grounded Indian legal information and document drafting assistance. Outputs do not constitute legal representation or formal legal advice. Consult a qualified advocate for official litigation.
          </div>
        </div>
      </div>
    </div>
  );
}