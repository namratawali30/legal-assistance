import { useState } from "react";
import { getApiErrorMessage } from "../../api/client";
import ProcessingStatusBadge from "./ProcessingStatusBadge";
import FingerprintBadge from "../../components/common/FingerprintBadge";

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function formatBytes(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

const CATEGORY_LABELS = {
  consumer_rights:    "Consumer Rights",
  labour_rights:      "Labour Rights",
  womens_safety:      "Women's Safety",
  educational_rights: "Educational Rights",
  anti_ragging:       "Anti-Ragging",
};

// ── Metadata row ──
function MetaRow({ label, value, mono, title }) {
  if (value == null || value === "" || value === "—") return null;
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
      <dt className="w-44 flex-shrink-0 text-xs font-medium text-slate-500">{label}</dt>
      <dd className={`text-xs text-slate-700 ${mono ? "break-all font-mono" : ""}`} title={title}>
        {value}
      </dd>
    </div>
  );
}

// ── Section card ──
function DetailCard({ title, icon, children }) {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50/50 px-5 py-3">
        <span className="text-sm">{icon}</span>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">{title}</h3>
      </div>
      <div className="px-5 py-4">{children}</div>
    </div>
  );
}

import { useFocusTrap } from "../../hooks/useFocusTrap";

// ── Confirm dialog ──
function ConfirmDialog({ title, message, confirmLabel, onConfirm, onCancel }) {
  const dialogRef = useFocusTrap(true, onCancel);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="ev-confirm-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-fade-in"
      onClick={onCancel}
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md animate-fade-up card p-6 shadow-xl outline-none"
        style={{ boxShadow: "var(--shadow-lg)" }}
      >
        <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-red-100">
          <svg className="h-5 w-5 text-red-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
        </div>
        <h2 id="ev-confirm-title" className="text-base font-semibold text-slate-900">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">{message}</p>
        <div className="mt-5 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-300 transition-colors min-h-[44px]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors min-h-[44px]"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}


// ── Inline spinner ──
function Spinner({ color = "white" }) {
  return (
    <span
      className="h-3.5 w-3.5 flex-shrink-0 animate-spin rounded-full border-2 border-t-transparent"
      style={{
        borderColor: color,
        borderTopColor: "transparent",
      }}
      aria-hidden="true"
    />
  );
}

// ─────────────────────────────────────────────
// EvidenceDetailPanel
// ─────────────────────────────────────────────

export default function EvidenceDetailPanel({
  evidence,
  onUpdated,
  onDeleted,
  processHandler,
  downloadHandler,
  deleteHandler,
  linkedComplaint,
}) {
  const [processing,        setProcessing]        = useState(false);
  const [downloading,       setDownloading]       = useState(false);
  const [deleting,          setDeleting]          = useState(false);
  const [actionError,       setActionError]       = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const ps         = evidence.processing_status;
  const canProcess = ps === "pending";
  const canRetry   = ps === "failed" || ps === "requires_ocr";
  const isProcessing = ps === "processing";

  async function handleProcess(retry = false) {
    setProcessing(true);
    setActionError(null);
    try {
      const updated = await processHandler(evidence.id, { retry });
      onUpdated(updated);
    } catch (err) {
      setActionError(getApiErrorMessage(err, "Could not start processing."));
    } finally {
      setProcessing(false);
    }
  }

  async function handleDownload() {
    setDownloading(true);
    setActionError(null);
    try {
      await downloadHandler(evidence.id, evidence.original_filename);
    } catch (err) {
      setActionError(getApiErrorMessage(err, "Download failed."));
    } finally {
      setDownloading(false);
    }
  }

  async function handleDeleteConfirmed() {
    setShowDeleteConfirm(false);
    setDeleting(true);
    setActionError(null);
    try {
      await deleteHandler(evidence.id);
      onDeleted(evidence.id);
    } catch (err) {
      setActionError(getApiErrorMessage(err, "Could not delete evidence."));
      setDeleting(false);
    }
  }

  return (
    <div className="min-h-full bg-mesh">
      {/* ── Header ── */}
      <div
        className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur px-6 py-4"
        style={{ boxShadow: "0 1px 0 0 rgb(0 0 0 / 0.05)" }}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold text-slate-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
              {evidence.title || evidence.original_filename}
            </h1>
            {evidence.title && evidence.title !== evidence.original_filename && (
              <p className="mt-0.5 text-xs text-slate-400 font-mono truncate">{evidence.original_filename}</p>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {canProcess && (
              <button
                type="button"
                id="process-evidence-btn"
                onClick={() => handleProcess(false)}
                disabled={processing}
                className="btn-primary"
              >
                {processing ? (
                  <><Spinner />Processing…</>
                ) : (
                  <>
                    <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clipRule="evenodd" />
                    </svg>
                    Process
                  </>
                )}
              </button>
            )}

            {canRetry && (
              <button
                type="button"
                id="retry-process-btn"
                onClick={() => handleProcess(true)}
                disabled={processing}
                className="inline-flex items-center gap-1.5 rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 disabled:opacity-50 transition-colors"
              >
                {processing ? (
                  <><Spinner color="#d97706" />Retrying…</>
                ) : (
                  <>
                    <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39z" clipRule="evenodd" />
                    </svg>
                    Retry processing
                  </>
                )}
              </button>
            )}

            {isProcessing && (
              <span className="flex items-center gap-1.5 text-sm font-medium text-blue-700">
                <Spinner color="#1d4ed8" />
                Processing…
              </span>
            )}

            <button
              type="button"
              id="download-evidence-btn"
              onClick={handleDownload}
              disabled={downloading || deleting}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-2 disabled:opacity-50 transition-colors"
            >
              {downloading ? (
                <><Spinner color="#64748b" />Downloading…</>
              ) : (
                <>
                  <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z" />
                    <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
                  </svg>
                  Download
                </>
              )}
            </button>

            <button
              type="button"
              id="delete-evidence-btn"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={deleting || processing}
              className="inline-flex items-center gap-1.5 rounded-xl border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2 disabled:opacity-50 transition-colors"
            >
              {deleting ? (
                <><Spinner color="#dc2626" />Deleting…</>
              ) : (
                <>
                  <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4z" clipRule="evenodd" />
                  </svg>
                  Delete
                </>
              )}
            </button>
          </div>
        </div>

        {/* Processing status */}
        <div className="mt-3">
          <ProcessingStatusBadge status={ps} showDescription />
        </div>
      </div>

      {/* ── Body ── */}
      <div className="px-6 py-6 space-y-5">
        {/* Action error */}
        {actionError && (
          <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3.5 text-sm text-red-700">
            <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
            </svg>
            <span className="flex-1">{actionError}</span>
            <button type="button" className="text-red-400 hover:text-red-700 transition-colors" onClick={() => setActionError(null)} aria-label="Dismiss">
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
        )}

        {/* Status-specific notices */}
        {ps === "requires_ocr" && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3.5 text-sm text-amber-900 flex items-start gap-3">
            <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495z" clipRule="evenodd" />
            </svg>
            <div>
              <strong>OCR required.</strong> This file contains image-based content.
              Optical character recognition (OCR) is not yet supported.
              The original file is preserved and can be downloaded.
            </div>
          </div>
        )}

        {ps === "failed" && evidence.processing_error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3.5 text-sm text-red-800">
            <strong>Processing failed.</strong> {evidence.processing_error}
          </div>
        )}

        {ps === "ready" && (evidence.evidence_type === "audio" || evidence.evidence_type === "video") && (
          <div className="rounded-xl border border-indigo-200 bg-indigo-50/90 p-4 text-xs text-indigo-950 space-y-1.5">
            <div className="font-bold flex items-center gap-1.5 text-indigo-900">
              <span>🎙️</span> AI-GENERATED TRANSCRIPT
            </div>
            <p className="text-slate-700 leading-relaxed">
              Review important words, names, dates, and numbers against the original recording.
            </p>
          </div>
        )}

        {ps === "ready" && evidence.extracted_character_count > 0 && (
          <div className="rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50 px-4 py-3.5 text-sm text-emerald-800 flex items-start gap-3">
            <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-emerald-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
            </svg>
            <div>
              <strong>Ready for complaint grounding.</strong>{" "}
              {evidence.extracted_character_count.toLocaleString()} characters extracted
              {evidence.extracted_page_count
                ? ` across ${evidence.extracted_page_count} page${evidence.extracted_page_count !== 1 ? "s" : ""}`
                : ""}
              .
            </div>
          </div>
        )}


        {/* File details */}
        <DetailCard title="File details" icon="📄">
          <dl className="space-y-3">
            <MetaRow label="Original filename" value={evidence.original_filename} />
            <MetaRow label="Evidence type"     value={evidence.evidence_type ? evidence.evidence_type.charAt(0).toUpperCase() + evidence.evidence_type.slice(1) : null} />
            <MetaRow label="MIME type"          value={evidence.media_type} mono />
            <MetaRow label="Extension"          value={evidence.file_extension ? evidence.file_extension.toUpperCase() : null} />
            <MetaRow label="File size"          value={formatBytes(evidence.size_bytes)} />
            <MetaRow label="Uploaded"           value={formatDate(evidence.created_at)} />
            <MetaRow label="Last updated"       value={formatDate(evidence.updated_at)} />
          </dl>
        </DetailCard>

        {/* Complaint association */}
        <DetailCard title="Complaint association" icon="📋">
          {evidence.complaint_id ? (
            linkedComplaint ? (
              <dl className="space-y-3">
                <MetaRow label="Complaint" value={linkedComplaint.title} />
                <MetaRow label="Category"  value={CATEGORY_LABELS[linkedComplaint.category] || linkedComplaint.category} />
                <MetaRow label="Status"    value={linkedComplaint.status.charAt(0).toUpperCase() + linkedComplaint.status.slice(1)} />
              </dl>
            ) : (
              <p className="text-xs text-slate-600 font-mono">ID: {evidence.complaint_id}</p>
            )
          ) : (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <svg className="h-4 w-4 text-slate-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
              </svg>
              Not linked to a complaint.
            </div>
          )}
        </DetailCard>

        {/* Processing details */}
        {(ps === "ready" || ps === "no_text" || ps === "requires_ocr" || ps === "failed") && (
          <DetailCard title="Processing details" icon="⚙️">
            <dl className="space-y-3">
              <MetaRow label="Processing status"  value={ps} />
              <MetaRow label="Extraction method"  value={evidence.extraction_method} />
              <MetaRow label="Characters extracted" value={evidence.extracted_character_count > 0 ? evidence.extracted_character_count.toLocaleString() : null} />
              <MetaRow label="Pages extracted"    value={evidence.extracted_page_count != null ? String(evidence.extracted_page_count) : null} />
              <MetaRow label="Processed at"       value={formatDate(evidence.processed_at)} />
            </dl>
          </DetailCard>
        )}

        {/* Integrity */}
        <DetailCard title="Integrity & Hash Fingerprint" icon="🔒">
          <div className="space-y-2">
            <dt className="text-xs font-medium text-slate-500">SHA-256 Cryptographic Fingerprint</dt>
            <dd>
              <FingerprintBadge hash={evidence.sha256} verified={Boolean(evidence.sha256)} verifiedLabel="SHA-256 Validated" />
            </dd>
          </div>
        </DetailCard>

        {/* Privacy notice */}
        <div className="flex items-start gap-3 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3.5 text-xs leading-5 text-blue-800">
          <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
          </svg>
          <span>
            <strong className="text-blue-900">Privacy and integrity.</strong>{" "}
            This file is stored privately and accessible only to your account.
            It may be used to ground AI-generated complaint text.
            File integrity is verified by the SHA-256 hash shown above.
            AI-derived text extraction supplements — but does not replace — your original file.
          </span>
        </div>
      </div>

      {/* Confirm delete dialog */}
      {showDeleteConfirm && (
        <ConfirmDialog
          title="Delete this evidence?"
          message="This will permanently delete the file and its metadata. Evidence linked to a finalized complaint cannot be deleted. This action cannot be undone."
          confirmLabel="Delete evidence"
          onConfirm={handleDeleteConfirmed}
          onCancel={() => setShowDeleteConfirm(false)}
        />
      )}
    </div>
  );
}
