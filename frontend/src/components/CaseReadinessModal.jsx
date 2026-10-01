import { useFocusTrap } from "../hooks/useFocusTrap";

export default function CaseReadinessModal({ isOpen, onClose, readiness, loading, error }) {
  const modalRef = useFocusTrap(isOpen, onClose);

  if (!isOpen) return null;

  const stateColors = {
    NEEDS_INFORMATION: "bg-amber-100 text-amber-800 border-amber-300",
    NEEDS_EVIDENCE: "bg-blue-100 text-blue-800 border-blue-300",
    READY_FOR_NEXT_STEP: "bg-emerald-100 text-emerald-800 border-emerald-300",
  };

  const stateLabels = {
    NEEDS_INFORMATION: "Information Needed",
    NEEDS_EVIDENCE: "Evidence Needed",
    READY_FOR_NEXT_STEP: "Ready for Next Step",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-3 sm:p-4 backdrop-blur-xs animate-fade-in"
      onClick={onClose}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="case-readiness-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-5 sm:p-6 shadow-2xl border border-slate-200 outline-none"
      >
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <h2 id="case-readiness-title" className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
              <span aria-hidden="true">📋</span> Case Readiness Assessment
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Factual completeness and evidence audit (No win predictions or merit scoring)
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Close Case Readiness modal"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center text-sm text-slate-500 flex items-center justify-center gap-2">
            <span className="h-4 w-4 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin-smooth" />
            Evaluating case readiness...
          </div>
        ) : error ? (
          <div role="alert" className="py-8 text-center text-sm text-red-600 font-medium">
            {error}
          </div>
        ) : readiness ? (
          <div className="mt-5 space-y-5">
            {/* Status & Next Step Banner */}
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Current Readiness State</span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold border ${stateColors[readiness.readiness_state] || 'bg-slate-100'}`}>
                  {stateLabels[readiness.readiness_state] || readiness.readiness_state}
                </span>
              </div>
              <div className="mt-3 pt-3 border-t border-slate-200/60">
                <div className="text-xs font-bold text-indigo-900 flex items-center gap-1.5">
                  <span aria-hidden="true">➡️</span> Primary Next Step:
                </div>
                <p className="mt-1 text-sm font-medium text-slate-800 break-words-custom">
                  {readiness.next_step}
                </p>
              </div>
            </div>

            {/* Facts Established */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                ✓ Facts Established ({readiness.facts_established.length})
              </h3>
              {readiness.facts_established.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No facts formally established yet.</p>
              ) : (
                <ul className="space-y-1.5">
                  {readiness.facts_established.map((fact, idx) => (
                    <li key={idx} className="flex items-center gap-2 rounded-lg bg-emerald-50/70 border border-emerald-200/60 px-3 py-2 text-xs font-medium text-emerald-900 break-words-custom">
                      <span className="text-emerald-600 font-bold" aria-hidden="true">✓</span>
                      {fact.label}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Still Needed / Missing Facts */}
            {readiness.facts_missing.length > 0 && (
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-700 mb-2">
                  ⚠ Facts Still Needed ({readiness.facts_missing.length})
                </h3>
                <ul className="space-y-1.5">
                  {readiness.facts_missing.map((fact, idx) => (
                    <li key={idx} className="rounded-lg bg-amber-50/80 border border-amber-200 px-3 py-2 text-xs text-amber-950">
                      <div className="font-semibold text-amber-900 flex items-center gap-1.5 break-words-custom">
                        <span aria-hidden="true">⚠</span> {fact.label}
                      </div>
                      {fact.reason && (
                        <p className="mt-0.5 text-[11px] text-amber-700 break-words-custom">{fact.reason}</p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Evidence Available */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                📁 Evidence Vault Records ({readiness.evidence_available.length})
              </h3>
              {readiness.evidence_available.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No evidence files attached yet.</p>
              ) : (
                <ul className="space-y-1.5">
                  {readiness.evidence_available.map((ev, idx) => (
                    <li key={idx} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs">
                      <span className="font-medium text-slate-800 break-words-custom">{ev.title}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold flex-shrink-0 ${
                        ev.status === 'ready' ? 'bg-emerald-100 text-emerald-800' :
                        ev.status === 'requires_ocr' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {ev.status}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Possible Authority */}
            {readiness.possible_authority && (
              <div className="rounded-lg bg-indigo-50/60 border border-indigo-200 px-3 py-2.5 text-xs text-indigo-950 break-words-custom">
                <span className="font-bold text-indigo-900">🏛 Possible Authority / Forum: </span>
                {readiness.possible_authority}
              </div>
            )}
          </div>
        ) : null}

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl bg-slate-900 px-5 py-2.5 text-xs font-semibold text-white hover:bg-slate-800 min-h-[44px]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

