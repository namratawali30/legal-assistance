import { useState } from "react";
import { getApiErrorMessage } from "../../api/client";
import ComplaintSourceCard from "./ComplaintSourceCard";
import ComplaintEvidenceRefs from "./ComplaintEvidenceRefs";

// ─────────────────────────────────────────────
// ComplaintGeneratedView
//
// Shows the AI-generated complaint text.
// AI text NEVER rendered as raw HTML — plain text only.
// ─────────────────────────────────────────────

export default function ComplaintGeneratedView({
  complaint,
  onTextSaved,
  updateTextHandler,
}) {
  const isFinalized     = complaint?.status === "finalized";
  const hasGeneratedText = Boolean(complaint?.generated_text);

  const [editing,   setEditing]   = useState(false);
  const [editValue, setEditValue] = useState("");
  const [saving,    setSaving]    = useState(false);
  const [error,     setError]     = useState(null);

  function startEditing() {
    setEditValue(complaint?.generated_text ?? "");
    setEditing(true);
    setError(null);
  }

  async function handleSave() {
    if (editValue.trim().length < 20) {
      setError("Complaint text must be at least 20 characters.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const updated = await updateTextHandler(editValue);
      setEditing(false);
      onTextSaved(updated);
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not save the edited complaint text."));
    } finally {
      setSaving(false);
    }
  }

  function handleCancel() {
    setEditValue(complaint?.generated_text ?? "");
    setEditing(false);
    setError(null);
  }

  if (!hasGeneratedText) return null;

  const sources       = complaint?.sources          ?? [];
  const evidenceRefs  = complaint?.evidence_references ?? [];

  return (
    <div className="space-y-5 animate-fade-up">
      {/* ── Section header ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-lg"
            style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}
          >
            <svg className="h-4 w-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-slate-700">
            AI-Generated Complaint Text
          </h3>
        </div>

        {!isFinalized && !editing && (
          <button
            type="button"
            onClick={startEditing}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-400 transition-colors"
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
            </svg>
            Edit text
          </button>
        )}
      </div>

      {/* ── Editing mode ── */}
      {editing ? (
        <div className="space-y-3">
          <div className="card overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5 bg-amber-50">
              <span className="text-xs font-semibold text-amber-700">
                ✏️ Editing generated text
              </span>
              <span className="text-xs text-amber-600">
                {editValue.length.toLocaleString()} / 30,000
              </span>
            </div>
            <textarea
              value={editValue}
              onChange={(e) => {
                setEditValue(e.target.value);
                setError(null);
              }}
              rows={22}
              maxLength={30000}
              disabled={saving}
              className="block w-full px-5 py-4 font-mono text-sm leading-7 text-slate-800 resize-none focus:outline-none disabled:bg-slate-50 disabled:text-slate-500"
              aria-label="Edit complaint text"
              placeholder="Edit the complaint text here…"
            />
          </div>

          {error && (
            <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="btn-primary"
            >
              {saving ? (
                <>
                  <span className="h-3.5 w-3.5 rounded-full border-2 border-white border-t-transparent animate-spin-smooth" />
                  Saving…
                </>
              ) : (
                "Save edits"
              )}
            </button>

            <button
              type="button"
              onClick={handleCancel}
              disabled={saving}
              className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-300 focus:ring-offset-2 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        /* ── Read / display mode ──
           AI text is rendered as PLAIN TEXT only.
           No dangerouslySetInnerHTML. No innerHTML.
           whitespace-pre-wrap preserves paragraph breaks. */
        <div className="card overflow-hidden">
          {isFinalized && (
            <div className="flex items-center gap-2 border-b border-emerald-100 bg-emerald-50 px-5 py-2.5">
              <svg className="h-4 w-4 text-emerald-500 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
              </svg>
              <span className="text-xs font-semibold text-emerald-700">
                Finalized — read only
              </span>
            </div>
          )}
          <div className="px-6 py-5">
            <pre
              className="whitespace-pre-wrap font-sans text-sm leading-7 text-slate-700"
              aria-label="Generated complaint text"
            >
              {complaint.generated_text}
            </pre>
          </div>
        </div>
      )}

      {/* ── Legal sources [SOURCE_n] ── */}
      {sources.length > 0 && (
        <div>
          <h4 className="mb-3 section-label flex items-center gap-1.5">
            <svg className="h-3.5 w-3.5 text-indigo-400" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10.75 16.82A7.462 7.462 0 0115 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0018 15.06v-11a.75.75 0 00-.546-.721A9.006 9.006 0 0015 3a8.963 8.963 0 00-4.25 1.065V16.82zM9.25 4.065A8.963 8.963 0 005 3c-.85 0-1.673.118-2.454.339A.75.75 0 002 4.06v11a.75.75 0 00.954.721A7.506 7.506 0 015 15.5c1.579 0 3.042.487 4.25 1.32V4.065z" />
            </svg>
            Legal sources cited
          </h4>
          <div className="flex flex-col gap-2.5">
            {sources.map((source) => (
              <ComplaintSourceCard key={source.citation_id} source={source} />
            ))}
          </div>
        </div>
      )}

      {/* ── Evidence grounding [EVIDENCE_n] ── */}
      <ComplaintEvidenceRefs evidenceReferences={evidenceRefs} />

      {/* ── Timestamps ── */}
      {complaint.generated_at && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
          <span>Generated {new Date(complaint.generated_at).toLocaleString("en-IN")}</span>
          {complaint.status === "edited" && (
            <span>· Edited {new Date(complaint.updated_at).toLocaleString("en-IN")}</span>
          )}
          {complaint.status === "finalized" && complaint.finalized_at && (
            <span>· Finalized {new Date(complaint.finalized_at).toLocaleString("en-IN")}</span>
          )}
        </div>
      )}
    </div>
  );
}
