import { useFocusTrap } from "../hooks/useFocusTrap";

export default function ActionPlanModal({ isOpen, onClose, plan, loading, error }) {
  const modalRef = useFocusTrap(isOpen, onClose);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-3 sm:p-4 backdrop-blur-xs animate-fade-in"
      onClick={onClose}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="action-plan-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-5 sm:p-6 shadow-2xl border border-slate-200 outline-none"
      >
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <h2 id="action-plan-title" className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
              <span aria-hidden="true">🎯</span> YOUR ACTION PLAN
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Ordered practical next steps grounded in verified law and evidence
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Close Action Plan modal"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center text-sm text-slate-500 flex items-center justify-center gap-2">
            <span className="h-4 w-4 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin-smooth" />
            Generating action plan...
          </div>
        ) : error ? (
          <div role="alert" className="py-8 text-center text-sm text-red-600 font-medium">
            {error}
          </div>
        ) : plan ? (
          <div className="mt-5 space-y-5">
            {/* Caution Banner if present */}
            {plan.important_caution && (
              <div className="rounded-xl bg-amber-50 border border-amber-200 p-3.5 text-xs text-amber-900 flex items-start gap-2">
                <span className="text-amber-600 font-bold" aria-hidden="true">⚠️</span>
                <div className="break-words-custom">
                  <span className="font-bold">Important Caution: </span>
                  {plan.important_caution}
                </div>
              </div>
            )}

            {/* Primary Next Step Banner */}
            <div className="rounded-xl bg-indigo-50 border border-indigo-200 p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-indigo-900 flex items-center gap-1.5">
                <span aria-hidden="true">➡️</span> Primary Next Step
              </div>
              <p className="mt-1.5 text-sm font-semibold text-slate-900 break-words-custom">
                {plan.primary_next_step}
              </p>
            </div>

            {/* Ordered Steps List */}
            <div className="space-y-3.5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Recommended Action Sequence ({plan.steps.length} Steps)
              </h3>

              {plan.steps.map((step) => (
                <div
                  key={step.order}
                  className="rounded-xl border border-slate-200 bg-white p-3.5 sm:p-4 shadow-2xs transition-all hover:border-slate-300"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white shadow-2xs flex-shrink-0">
                        {step.order}
                      </span>
                      <h4 className="text-sm font-bold text-slate-900 break-words-custom">
                        {step.title}
                      </h4>
                    </div>
                    {step.state === "DONE" && (
                      <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200 flex-shrink-0">
                        ✓ Completed
                      </span>
                    )}
                  </div>

                  <p className="mt-2.5 text-xs leading-relaxed text-slate-700 sm:pl-9 break-words-custom">
                    {step.instruction}
                  </p>

                  {step.reason && (
                    <p className="mt-1.5 text-[11px] text-slate-500 italic sm:pl-9 break-words-custom">
                      Why: {step.reason}
                    </p>
                  )}

                  {/* Citations Row */}
                  {(step.source_citations.length > 0 || step.evidence_citations.length > 0) && (
                    <div className="mt-3 flex flex-wrap items-center gap-1.5 sm:pl-9 pt-2 border-t border-slate-100">
                      {step.source_citations.map((cite) => (
                        <span key={cite} className="rounded bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 border border-indigo-200">
                          {cite} (Legal Basis)
                        </span>
                      ))}
                      {step.evidence_citations.map((ev) => (
                        <span key={ev} className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200">
                          {ev} (User Evidence)
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="mt-6 flex justify-end gap-2 pt-4 border-t border-slate-100">
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

