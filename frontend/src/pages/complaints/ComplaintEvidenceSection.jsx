import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listEvidence } from "../../api/evidence";
import { getApiErrorMessage } from "../../api/client";

// ─────────────────────────────────────────────
// Processing status config — user-friendly labels
// matching Step 4 of the specification
// ─────────────────────────────────────────────

const STATUS_CONFIG = {
  pending: {
    label: "Waiting to be processed",
    dot:   "bg-slate-400",
    badge: "bg-slate-100 text-slate-600 border-slate-200",
    icon:  null,
    grounding: false,
  },
  processing: {
    label: "Extracting usable text…",
    dot:   "bg-blue-400",
    badge: "bg-blue-50 text-blue-700 border-blue-200",
    spin:  true,
    grounding: false,
  },
  ready: {
    label: "Ready for complaint grounding",
    dot:   "bg-emerald-500",
    badge: "bg-emerald-50 text-emerald-700 border-emerald-200",
    icon:  "check",
    grounding: true,
  },
  no_text: {
    label: "No extractable text found",
    dot:   "bg-slate-400",
    badge: "bg-slate-100 text-slate-500 border-slate-200",
    icon:  "warn",
    grounding: false,
  },
  requires_ocr: {
    label: "Image stored securely — text extraction requires OCR",
    dot:   "bg-amber-400",
    badge: "bg-amber-50 text-amber-700 border-amber-200",
    icon:  "warn",
    grounding: false,
  },
  failed: {
    label: "Processing failed",
    dot:   "bg-red-400",
    badge: "bg-red-50 text-red-700 border-red-200",
    icon:  "x",
    grounding: false,
  },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-semibold ${cfg.badge}`}>
      {cfg.spin ? (
        <span className="h-2 w-2 flex-shrink-0 rounded-full border-2 border-current border-t-transparent animate-spin-smooth" aria-hidden="true" />
      ) : (
        <span className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${cfg.dot}`} aria-hidden="true" />
      )}
      {cfg.label}
    </span>
  );
}

function formatBytes(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const EXT_ICONS = {
  pdf:  "📄", txt: "📝", docx: "📋",
  jpg:  "🖼️",  jpeg: "🖼️", png: "🖼️", webp: "🖼️",
};

// ─────────────────────────────────────────────
// GroundingNote
// Explains to the user which evidence can actually
// contribute to AI grounding, without exposing
// private extracted text.
// ─────────────────────────────────────────────

function GroundingNote({ evidenceList }) {
  if (!evidenceList.length) return null;

  const ready  = evidenceList.filter((e) => e.processing_status === "ready");
  const others = evidenceList.filter((e) => e.processing_status !== "ready");

  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3.5 text-xs leading-5 text-slate-600">
      <p className="font-semibold text-slate-700 mb-1.5">
        AI grounding summary
      </p>
      {ready.length > 0 ? (
        <ul className="space-y-1">
          {ready.map((e) => (
            <li key={e.id} className="flex items-center gap-1.5 text-emerald-700">
              <svg className="h-3.5 w-3.5 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
              </svg>
              <span className="font-medium truncate">{e.title || e.original_filename}</span>
              <span className="text-emerald-500">— ready for grounding</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-amber-700">
          No evidence is ready for grounding yet. Process your uploaded files first.
        </p>
      )}
      {others.length > 0 && (
        <ul className="mt-1.5 space-y-1">
          {others.map((e) => {
            const cfg = STATUS_CONFIG[e.processing_status] || STATUS_CONFIG.pending;
            return (
              <li key={e.id} className="flex items-center gap-1.5 text-slate-500">
                <svg className="h-3.5 w-3.5 flex-shrink-0 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
                <span className="font-medium truncate">{e.title || e.original_filename}</span>
                <span className="text-slate-400">— {cfg.label}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// EvidenceRow — single row in the summary table
// ─────────────────────────────────────────────

function EvidenceRow({ item }) {
  const ext  = item.file_extension?.toLowerCase();
  const icon = EXT_ICONS[ext] || "📁";
  return (
    <div className="flex items-start gap-3 rounded-xl border border-slate-100 bg-white px-4 py-3">
      <span className="text-lg leading-none mt-0.5 flex-shrink-0">{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <p className="truncate text-sm font-medium text-slate-800">
            {item.title || item.original_filename}
          </p>
          {item.title && item.title !== item.original_filename && (
            <p className="text-xs text-slate-400 font-mono truncate">
              {item.original_filename}
            </p>
          )}
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-400">
          {ext && <span className="font-mono uppercase">{ext}</span>}
          <span>·</span>
          <span>{formatBytes(item.size_bytes)}</span>
        </div>
        <div className="mt-1.5">
          <StatusBadge status={item.processing_status} />
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// ComplaintEvidenceSection
//
// Props:
//   complaint: the current complaint object
//   isFinalized: boolean
// ─────────────────────────────────────────────

export default function ComplaintEvidenceSection({ complaint, isFinalized }) {
  const navigate = useNavigate();

  const [evidence, setEvidence]     = useState([]);
  const [loading,  setLoading]      = useState(true);
  const [error,    setError]        = useState(null);

  const complaintId = complaint?.id;

  async function load() {
    if (!complaintId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listEvidence({ complaintId });
      setEvidence([...data].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not load evidence for this complaint."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function fetchEvidence() {
      if (!complaintId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await listEvidence({ complaintId });
        setEvidence([...data].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
      } catch (err) {
        setError(getApiErrorMessage(err, "Could not load evidence for this complaint."));
      } finally {
        setLoading(false);
      }
    }
    fetchEvidence();
  }, [complaintId]);

  // Navigate to Evidence Vault with this complaint pre-selected
  // We do NOT put sensitive IDs in the URL pathname — we use the
  // standard Evidence Vault route with a URLSearchParam for filter.
  function handleManageEvidence() {
    navigate(`/evidence?complaint=${complaintId}`);
  }

  function handleAddEvidence() {
    // Navigate to evidence vault with upload intent and complaint context
    navigate(`/evidence?complaint=${complaintId}&upload=1`);
  }

  return (
    <div className="space-y-4 animate-fade-up">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-lg"
            style={{ background: "linear-gradient(135deg, #f59e0b, #d97706)" }}
          >
            <svg className="h-4 w-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-slate-700">
            Evidence for this complaint
          </h3>
          {!loading && evidence.length > 0 && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
              {evidence.length}
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {!isFinalized && (
            <button
              type="button"
              id="add-evidence-btn"
              onClick={handleAddEvidence}
              className="flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-1 transition-colors"
            >
              <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
              </svg>
              Add evidence
            </button>
          )}
          {evidence.length > 0 && (
            <button
              type="button"
              id="manage-evidence-btn"
              onClick={handleManageEvidence}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-1 transition-colors"
            >
              <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z" clipRule="evenodd" />
              </svg>
              Manage in vault
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      {loading ? (
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100" />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600 flex items-center justify-between">
          <span>{error}</span>
          <button type="button" onClick={load} className="text-xs underline hover:text-red-800 transition-colors">
            Retry
          </button>
        </div>
      ) : evidence.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-5 py-8 text-center">
          <div
            className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl"
            style={{ background: "linear-gradient(135deg, rgb(245 158 11 / 0.12), rgb(217 119 6 / 0.08))" }}
          >
            <svg className="h-5 w-5 text-amber-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 7.5h-.75A2.25 2.25 0 004.5 9.75v7.5a2.25 2.25 0 002.25 2.25h7.5a2.25 2.25 0 002.25-2.25v-7.5a2.25 2.25 0 00-2.25-2.25h-.75m0-3l-3-3m0 0l-3 3m3-3v11.25m6-2.25h.75a2.25 2.25 0 012.25 2.25v7.5a2.25 2.25 0 01-2.25 2.25h-7.5a2.25 2.25 0 01-2.25-2.25v-.75" />
            </svg>
          </div>
          <p className="text-sm font-semibold text-slate-700">No evidence linked yet</p>
          <p className="mt-1 text-xs text-slate-400 max-w-xs mx-auto">
            Upload and associate evidence to help the AI ground your complaint in verified facts.
          </p>
          {!isFinalized && (
            <button
              type="button"
              onClick={handleAddEvidence}
              className="mt-4 inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2"
              style={{ background: "linear-gradient(135deg, #f59e0b, #d97706)" }}
            >
              <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M9.25 13.25a.75.75 0 001.5 0V4.636l2.955 3.129a.75.75 0 001.09-1.03l-4.25-4.5a.75.75 0 00-1.09 0l-4.25 4.5a.75.75 0 101.09 1.03L9.25 4.636v8.614z" />
                <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
              </svg>
              Upload evidence
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {evidence.map((item) => (
            <EvidenceRow key={item.id} item={item} />
          ))}
        </div>
      )}

      {/* Grounding note — shown when there is at least one evidence item */}
      {!loading && !error && evidence.length > 0 && (
        <GroundingNote evidenceList={evidence} />
      )}
    </div>
  );
}
