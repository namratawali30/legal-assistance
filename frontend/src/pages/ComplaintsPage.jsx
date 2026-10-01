import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  createComplaint,
  deleteComplaint,
  exportComplaintDocx,
  exportComplaintPdf,
  finalizeComplaint,
  generateComplaint,
  getComplaint,
  listComplaints,
  triggerBlobDownload,
  updateComplaint,
  updateGeneratedText,
} from "../api/complaints";

import { getApiErrorMessage } from "../api/client";

import ComplaintList         from "./complaints/ComplaintList";
import ComplaintEditor       from "./complaints/ComplaintEditor";
import ComplaintGeneratedView from "./complaints/ComplaintGeneratedView";
import ComplaintEvidenceSection from "./complaints/ComplaintEvidenceSection";
import LifecycleBar          from "./complaints/LifecycleBar";
import ComplaintStatusBadge  from "./complaints/ComplaintStatusBadge";

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

const CATEGORY_LABELS = {
  consumer_rights:    "Consumer Rights",
  labour_rights:      "Labour Rights",
  womens_safety:      "Women's Safety",
  educational_rights: "Educational Rights",
  anti_ragging:       "Anti-Ragging",
};

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

import { useFocusTrap } from "../hooks/useFocusTrap";

// ─────────────────────────────────────────────
// Modal confirmation dialog
// ─────────────────────────────────────────────

function ConfirmDialog({ title, message, danger, onConfirm, onCancel, confirmLabel = "Confirm" }) {
  const dialogRef = useFocusTrap(true, onCancel);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
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
        <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl ${danger ? "bg-red-100" : "bg-indigo-100"}`}>
          {danger ? (
            <svg className="h-5 w-5 text-red-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg className="h-5 w-5 text-indigo-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
            </svg>
          )}
        </div>

        <h2 id="confirm-title" className="text-base font-semibold text-slate-900">
          {title}
        </h2>
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
            className={[
              "rounded-xl px-4 py-2.5 text-sm font-semibold text-white focus:outline-none focus:ring-2 transition-all min-h-[44px] cursor-pointer",
              danger
                ? "bg-red-600 hover:bg-red-700 focus:ring-red-500"
                : "btn-teal",
            ].join(" ")}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>

  );
}

// ─────────────────────────────────────────────
// Action button helper variants
// ─────────────────────────────────────────────

function ActionButton({ onClick, disabled, variant = "primary", children, id }) {
  const base = "inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 min-h-[40px] cursor-pointer";

  const styles = {
    primary:  "btn-teal shadow-2xs",
    outline:  "btn-outline-legal",
    success:  "border border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 focus:ring-emerald-400",
    danger:   "btn-danger-legal",
    download: "btn-outline-legal text-teal-800 border-teal-200 bg-teal-50/50 hover:bg-teal-100",
  };

  return (
    <button
      type="button"
      id={id}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${styles[variant] || styles.outline}`}
    >
      {children}
    </button>
  );
}

// ── Shared inline spinner ──
function Spinner() {
  return (
    <span
      className="h-3.5 w-3.5 rounded-full border-2 border-white border-t-transparent animate-spin-smooth"
      aria-hidden="true"
    />
  );
}

// ─────────────────────────────────────────────
// ComplaintWorkspace — right panel
// ─────────────────────────────────────────────

function ComplaintWorkspace({ complaint, onComplaintUpdated, onComplaintDeleted }) {
  const [generating, setGenerating]           = useState(false);
  const [actionError, setActionError]         = useState(null);
  const [exporting, setExporting]             = useState(null);  // "pdf" | "docx" | null
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showFinalizeConfirm, setShowFinalizeConfirm] = useState(false);
  const [deleting, setDeleting]               = useState(false);
  const [finalizing, setFinalizing]           = useState(false);

  const status          = complaint.status;
  const isFinalized     = status === "finalized";
  const canGenerate     = !isFinalized;
  const isAlreadyGenerated = status === "generated" || status === "edited";

  async function handleGenerate() {
    setGenerating(true);
    setActionError(null);
    try {
      const updated = await generateComplaint(complaint.id, { regenerate: isAlreadyGenerated });
      onComplaintUpdated(updated);
    } catch (err) {
      setActionError(getApiErrorMessage(err, "Complaint generation failed. Please try again."));
    } finally {
      setGenerating(false);
    }
  }

  async function handleFinalizeConfirmed() {
    setShowFinalizeConfirm(false);
    setFinalizing(true);
    setActionError(null);
    try {
      const updated = await finalizeComplaint(complaint.id);
      onComplaintUpdated(updated);
    } catch (err) {
      setActionError(getApiErrorMessage(err, "Could not finalize the complaint."));
    } finally {
      setFinalizing(false);
    }
  }

  async function handleExport(format) {
    setExporting(format);
    setActionError(null);
    try {
      const fn = format === "pdf" ? exportComplaintPdf : exportComplaintDocx;
      const { blob, filename } = await fn(complaint.id);
      triggerBlobDownload(blob, filename);
    } catch (err) {
      setActionError(getApiErrorMessage(err, `Could not export the complaint as ${format.toUpperCase()}.`));
    } finally {
      setExporting(null);
    }
  }

  async function handleDeleteConfirmed() {
    setShowDeleteConfirm(false);
    setDeleting(true);
    setActionError(null);
    try {
      await deleteComplaint(complaint.id);
      onComplaintDeleted(complaint.id);
    } catch (err) {
      setActionError(getApiErrorMessage(err, "Could not delete the complaint."));
      setDeleting(false);
    }
  }


  return (
    <div className="flex flex-col min-h-full bg-mesh">
      {/* ── Sticky header ── */}
      <div
        className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur px-6 py-4"
        style={{ boxShadow: "0 1px 0 0 rgb(0 0 0 / 0.05)" }}
      >
        {/* Title row */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate text-lg font-semibold text-slate-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
                {complaint.title}
              </h1>
              <ComplaintStatusBadge status={status} />
            </div>
            <p className="mt-0.5 text-xs text-slate-400">
              <span className="font-medium text-slate-500">
                {CATEGORY_LABELS[complaint.category] || complaint.category}
              </span>
              {" · "}Created {formatDate(complaint.created_at)}
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Generate / Regenerate */}
            {canGenerate && (
              <ActionButton
                variant="primary"
                onClick={handleGenerate}
                disabled={generating || finalizing}
                id="generate-complaint-btn"
              >
                {generating ? (
                  <><Spinner />Generating…</>
                ) : isAlreadyGenerated ? (
                  <>
                    <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clipRule="evenodd" />
                    </svg>
                    Regenerate
                  </>
                ) : (
                  <>
                    <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M10 1a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 1zm4.95 2.55a.75.75 0 010 1.06L13.71 5.85a.75.75 0 11-1.06-1.06l1.24-1.24a.75.75 0 011.06 0zm-9.9 0a.75.75 0 011.06 0l1.24 1.24a.75.75 0 01-1.06 1.06L5.05 4.61a.75.75 0 010-1.06zM10 7a3 3 0 110 6 3 3 0 010-6zm-5.657 3a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5A.75.75 0 014.343 10zm9.065 0a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5a.75.75 0 01-.75-.75zm-7.19 3.89a.75.75 0 010 1.06L4.974 16.19a.75.75 0 11-1.06-1.06l1.242-1.243a.75.75 0 011.06 0zm7.432 0a.75.75 0 011.06 0l1.243 1.243a.75.75 0 11-1.06 1.06l-1.243-1.242a.75.75 0 010-1.06zM10 17.25a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0V18a.75.75 0 01.75-.75z" />
                    </svg>
                    Generate with AI
                  </>
                )}
              </ActionButton>
            )}

            {/* Finalize */}
            {isAlreadyGenerated && !isFinalized && (
              <ActionButton
                variant="success"
                onClick={() => setShowFinalizeConfirm(true)}
                disabled={finalizing || generating}
                id="finalize-complaint-btn"
              >
                {finalizing ? (
                  <><span className="h-3.5 w-3.5 rounded-full border-2 border-emerald-600 border-t-transparent animate-spin-smooth" aria-hidden="true" />Finalizing…</>
                ) : (
                  <>
                    <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
                    </svg>
                    Finalize
                  </>
                )}
              </ActionButton>
            )}

            {/* Export buttons (finalized only) */}
            {isFinalized && (
              <>
                <ActionButton
                  variant="download"
                  onClick={() => handleExport("pdf")}
                  disabled={exporting !== null}
                  id="export-pdf-btn"
                >
                  {exporting === "pdf" ? (
                    <><span className="h-3.5 w-3.5 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin-smooth" aria-hidden="true" />Exporting…</>
                  ) : (
                    <>
                      <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z" />
                        <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
                      </svg>
                      Export PDF
                    </>
                  )}
                </ActionButton>

                <ActionButton
                  variant="download"
                  onClick={() => handleExport("docx")}
                  disabled={exporting !== null}
                  id="export-docx-btn"
                >
                  {exporting === "docx" ? (
                    <><span className="h-3.5 w-3.5 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin-smooth" aria-hidden="true" />Exporting…</>
                  ) : (
                    <>
                      <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0-6a.75.75 0 000 1.5h3a.75.75 0 000-1.5h-3z" clipRule="evenodd" />
                      </svg>
                      Export DOCX
                    </>
                  )}
                </ActionButton>
              </>
            )}

            {/* Delete (non-finalized) */}
            {!isFinalized && (
              <ActionButton
                variant="danger"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={deleting || generating || finalizing}
                id="delete-complaint-btn"
              >
                {deleting ? (
                  <><span className="h-3.5 w-3.5 rounded-full border-2 border-red-500 border-t-transparent animate-spin-smooth" aria-hidden="true" />Deleting…</>
                ) : (
                  <>
                    <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clipRule="evenodd" />
                    </svg>
                    Delete
                  </>
                )}
              </ActionButton>
            )}
          </div>
        </div>

        {/* Lifecycle bar */}
        <div className="mt-4 overflow-x-auto">
          <LifecycleBar status={status} />
        </div>
      </div>

      {/* ── Body ── */}
      <div className="flex-1 px-6 py-6">
        {/* Action error */}
        {actionError && (
          <div
            role="alert"
            className="mb-5 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3.5 text-sm text-red-700"
          >
            <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
            </svg>
            <span className="flex-1">{actionError}</span>
            <button
              type="button"
              className="text-red-400 hover:text-red-600 transition-colors"
              onClick={() => setActionError(null)}
              aria-label="Dismiss"
            >
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
        )}

        {/* Generation in-progress notice */}
        {generating && (
          <div className="mb-5 flex items-center gap-3 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3.5 text-sm text-indigo-800">
            <span
              className="h-4 w-4 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin-smooth flex-shrink-0"
              aria-hidden="true"
            />
            <span>
              Generating your complaint with AI and the legal knowledge base. This may take up to a minute…
            </span>
          </div>
        )}

        {/* Legal disclaimer */}
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-xs leading-5 text-amber-900">
          <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
          <span>
            <strong>Legal information only.</strong> Nyaya AI provides AI-assisted complaint drafting grounded in verified Indian legal sources.
            It does not constitute legal advice and does not replace consultation with a qualified advocate.
          </span>
        </div>

        <div className="space-y-6">
          {/* Structured fields editor */}
          <ComplaintEditor
            complaint={complaint}
            isCreating={false}
            saveHandler={async (fields) => updateComplaint(complaint.id, fields)}
            onSave={onComplaintUpdated}
          />

          {/* Evidence associated with this complaint */}
          <ComplaintEvidenceSection
            complaint={complaint}
            isFinalized={isFinalized}
          />

          {/* AI-generated text */}
          {complaint.generated_text && (
            <ComplaintGeneratedView
              complaint={complaint}
              updateTextHandler={async (text) => updateGeneratedText(complaint.id, text)}
              onTextSaved={onComplaintUpdated}
            />
          )}
        </div>
      </div>

      {/* ── Confirmation dialogs ── */}
      {showDeleteConfirm && (
        <ConfirmDialog
          title="Delete this complaint?"
          message="This complaint will be permanently deleted. This action cannot be undone. Complaints with linked evidence cannot be deleted — remove the evidence links first."
          danger
          confirmLabel="Delete complaint"
          onConfirm={handleDeleteConfirmed}
          onCancel={() => setShowDeleteConfirm(false)}
        />
      )}

      {showFinalizeConfirm && (
        <ConfirmDialog
          title="Finalize this complaint?"
          message="Finalizing is permanent. Once finalized, the complaint text and structured fields can no longer be edited or deleted. You will be able to export it as PDF or DOCX. This action cannot be reversed."
          danger={false}
          confirmLabel="Yes, finalize complaint"
          onConfirm={handleFinalizeConfirmed}
          onCancel={() => setShowFinalizeConfirm(false)}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// Create complaint form wrapper
// ─────────────────────────────────────────────

function CreateComplaintForm({ onCreated, onCancel }) {
  return (
    <div className="min-h-full bg-mesh px-6 py-6">
      {/* Header */}
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-indigo-500">New complaint</p>
        <h2 className="mt-1 text-xl font-bold text-slate-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Draft a new complaint
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Fill in the details below. You can edit everything before generating with AI.
        </p>
      </div>

      {/* Disclaimer */}
      <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">
        <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
        </svg>
        <span>
          <strong>Legal information only.</strong> Nyaya AI provides AI-assisted complaint drafting grounded in verified Indian legal sources.
          It does not constitute legal advice.
        </span>
      </div>

      <ComplaintEditor
        complaint={null}
        isCreating
        saveHandler={createComplaint}
        onSave={onCreated}
        onCancel={onCancel}
      />
    </div>
  );
}

// ─────────────────────────────────────────────
// ComplaintsPage — top-level route component
// ─────────────────────────────────────────────

export default function ComplaintsPage() {
  const { complaintId } = useParams();
  const navigate = useNavigate();

  const [complaints, setComplaints]               = useState([]);
  const [listLoading, setListLoading]             = useState(true);
  const [listError, setListError]                 = useState(null);

  const [activeComplaint, setActiveComplaint]     = useState(null);
  const [workspaceLoading, setWorkspaceLoading]   = useState(false);
  const [workspaceError, setWorkspaceError]       = useState(null);

  const [showCreateForm, setShowCreateForm]       = useState(false);

  // ── Load list ──
  async function fetchAndSetComplaints() {
    setListLoading(true);
    setListError(null);
    try {
      const data = await listComplaints();
      setComplaints([...data].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
    } catch (err) {
      setListError(getApiErrorMessage(err, "Could not load complaints."));
    } finally {
      setListLoading(false);
    }
  }

  useEffect(() => {
    async function loadList() {
      setListLoading(true);
      setListError(null);
      try {
        const data = await listComplaints();
        setComplaints([...data].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
      } catch (err) {
        setListError(getApiErrorMessage(err, "Could not load complaints."));
      } finally {
        setListLoading(false);
      }
    }
    loadList();
  }, []);


  // ── Load workspace when URL param changes ──
  useEffect(() => {
    async function loadWorkspace() {
      if (!complaintId) {
        setActiveComplaint(null);
        setWorkspaceError(null);
        return;
      }
      setWorkspaceLoading(true);
      setWorkspaceError(null);
      setShowCreateForm(false);
      try {
        const data = await getComplaint(complaintId);
        setActiveComplaint(data);
      } catch (err) {
        setWorkspaceError(getApiErrorMessage(err, "Could not load the complaint."));
        setActiveComplaint(null);
      } finally {
        setWorkspaceLoading(false);
      }
    }
    loadWorkspace();
  }, [complaintId]);

  // ── Handlers ──
  function handleSelect(id)    { setShowCreateForm(false); navigate(`/complaints/${id}`); }
  function handleNewComplaint() { setShowCreateForm(true); setActiveComplaint(null); navigate("/complaints"); }

  function handleCreated(complaint) {
    setComplaints((prev) => [complaint, ...prev]);
    setShowCreateForm(false);
    navigate(`/complaints/${complaint.id}`);
  }

  function handleCancelCreate() {
    setShowCreateForm(false);
    if (complaints.length > 0) navigate(`/complaints/${complaints[0].id}`);
    else navigate("/complaints");
  }

  function handleComplaintUpdated(updated) {
    setActiveComplaint(updated);
    setComplaints((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
  }

  function handleComplaintDeleted(id) {
    setComplaints((prev) => prev.filter((c) => c.id !== id));
    setActiveComplaint(null);
    navigate("/complaints");
  }

  const showWorkspace = !showCreateForm && (activeComplaint || workspaceLoading || workspaceError);

  return (
    <div className="flex h-screen flex-col lg:flex-row bg-slate-50">
      {/* ── Left: complaint list panel ── */}
      <div
        className={[
          "flex-shrink-0 overflow-hidden bg-white",
          "lg:w-80 lg:border-r lg:border-slate-100",
          showWorkspace || showCreateForm ? "hidden lg:flex lg:flex-col" : "flex flex-col",
        ].join(" ")}
      >
        {listError ? (
          <div className="p-5 text-sm text-red-600">
            {listError}
            <button type="button" onClick={fetchAndSetComplaints} className="ml-2 underline hover:text-red-800">
              Retry
            </button>
          </div>
        ) : (
          <ComplaintList
            complaints={complaints}
            selectedId={complaintId}
            onSelect={handleSelect}
            onNewComplaint={handleNewComplaint}
            loading={listLoading}
          />
        )}
      </div>

      {/* ── Right: workspace / create form ── */}
      <div className="flex min-w-0 flex-1 flex-col overflow-y-auto">
        {/* Mobile back button */}
        {(showWorkspace || showCreateForm) && (
          <div className="flex items-center border-b border-slate-100 bg-white px-4 py-3 lg:hidden">
            <button
              type="button"
              onClick={() => navigate("/complaints")}
              className="flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
              </svg>
              All complaints
            </button>
          </div>
        )}

        {showCreateForm ? (
          <CreateComplaintForm onCreated={handleCreated} onCancel={handleCancelCreate} />
        ) : workspaceLoading ? (
          <div className="flex flex-1 items-center justify-center py-24">
            <div className="flex flex-col items-center gap-3">
              <div
                className="h-10 w-10 rounded-full border-2 border-t-transparent animate-spin-smooth"
                style={{ borderColor: "#6366f1 transparent transparent transparent" }}
              />
              <p className="text-sm text-slate-400">Loading complaint…</p>
            </div>
          </div>
        ) : workspaceError ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-24 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-50">
              <svg className="h-7 w-7 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
              </svg>
            </div>
            <p className="text-sm font-medium text-red-600">{workspaceError}</p>
            <button
              type="button"
              onClick={() => navigate(`/complaints/${complaintId}`)}
              className="text-sm font-medium text-indigo-600 underline hover:text-indigo-800 transition-colors"
            >
              Try again
            </button>
          </div>
        ) : activeComplaint ? (
          <ComplaintWorkspace
            complaint={activeComplaint}
            onComplaintUpdated={handleComplaintUpdated}
            onComplaintDeleted={handleComplaintDeleted}
          />
        ) : (
          /* Empty selection state — desktop */
          <div className="hidden flex-1 flex-col items-center justify-center gap-5 px-6 py-24 text-center lg:flex">
            <div
              className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl"
              style={{ background: "linear-gradient(135deg, rgb(99 102 241/0.12), rgb(139 92 246/0.08))" }}
            >
              <svg className="h-10 w-10 text-indigo-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <div>
              <p className="text-base font-semibold text-slate-700" style={{ fontFamily: "'Outfit', sans-serif" }}>
                Select a complaint or create a new one
              </p>
              <p className="mt-1.5 text-sm text-slate-400 max-w-xs">
                Choose from the list on the left, or click{" "}
                <strong className="text-slate-600">New</strong> to start drafting your complaint.
              </p>
            </div>
            <button
              type="button"
              onClick={handleNewComplaint}
              className="btn-primary"
            >
              Create your first complaint
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
