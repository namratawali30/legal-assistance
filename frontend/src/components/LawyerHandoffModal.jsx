import { downloadHandoffDocx, downloadHandoffPdf } from "../api/lawyerHandoff";
import { useFocusTrap } from "../hooks/useFocusTrap";

export default function LawyerHandoffModal({ isOpen, onClose, handoff, loading, error, sessionId }) {
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
        aria-labelledby="lawyer-handoff-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-5 sm:p-6 shadow-2xl border border-slate-200 outline-none"
      >
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <h2 id="lawyer-handoff-title" className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
              <span aria-hidden="true">💼</span> LAWYER HANDOFF PACK
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Concise professional case briefing organized for legal review
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Close Lawyer Handoff modal"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center text-sm text-slate-500 flex items-center justify-center gap-2">
            <span className="h-4 w-4 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin-smooth" />
            Assembling lawyer handoff pack...
          </div>
        ) : error ? (
          <div role="alert" className="py-8 text-center text-sm text-red-600 font-medium">
            {error}
          </div>
        ) : handoff ? (
          <div className="mt-5 space-y-6 text-xs text-slate-700">
            {/* Disclaimer Banner */}
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-3.5 italic text-slate-600 leading-relaxed break-words-custom">
              "This pack was organized by Nyaya AI from information and evidence provided in this workspace and verified legal sources. It is intended to help a legal professional review the matter and is not a substitute for professional legal advice."
            </div>

            {/* Case Summary */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">1. Case Summary</h3>
              <p className="text-sm leading-relaxed text-slate-800 font-medium break-words-custom">
                {handoff.case_summary}
              </p>
            </div>

            {/* Objective & Parties */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">2. User Objective</h3>
                <p className="mt-1.5 text-xs font-semibold text-slate-800 break-words-custom">
                  {handoff.user_objective}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">3. Parties Involved</h3>
                <div className="mt-1.5 space-y-1">
                  {handoff.parties.map((p, idx) => (
                    <div key={idx} className="flex justify-between gap-2">
                      <span className="font-semibold text-slate-900 flex-shrink-0">{p.role}:</span>
                      <span className="text-slate-700 break-words-custom text-right">{p.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Established Facts & Open Questions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl border border-slate-200 bg-emerald-50/40 p-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-800">4. Established Facts ({handoff.established_facts.length})</h3>
                <ul className="mt-2 space-y-1.5 list-disc pl-4 text-emerald-950">
                  {handoff.established_facts.map((f, idx) => (
                    <li key={idx} className="break-words-custom">{f.label}</li>
                  ))}
                </ul>
              </div>

              <div className="rounded-xl border border-slate-200 bg-amber-50/40 p-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-800">5. Open Questions ({handoff.unresolved_questions.length})</h3>
                <ul className="mt-2 space-y-1.5 list-disc pl-4 text-amber-950">
                  {handoff.unresolved_questions.map((q, idx) => (
                    <li key={idx} className="break-words-custom">{q.label}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Evidence Index */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">6. Evidence Index ({handoff.evidence_index.length} Items)</h3>
              <div className="space-y-2">
                {handoff.evidence_index.map((ev) => (
                  <div key={ev.citation_id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50 p-2.5">
                    <div className="min-w-0">
                      <span className="font-bold text-indigo-700 mr-2">[{ev.citation_id}]</span>
                      <span className="font-semibold text-slate-900 break-words-custom">{ev.title}</span>
                      <span className="ml-2 text-[10px] uppercase font-bold text-slate-400 flex-shrink-0">({ev.evidence_type})</span>
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono flex-shrink-0">
                      SHA-256: {ev.sha256.substring(0, 16)}...
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Legal Sources & Current Next Step */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">7. Verified Legal Basis & Next Step</h3>
              {handoff.legal_sources.map((src) => (
                <div key={src.citation_id} className="text-xs break-words-custom">
                  <span className="font-bold text-indigo-700 mr-1.5">[{src.citation_id}]</span>
                  <span className="font-semibold text-slate-900">{src.title}</span>
                </div>
              ))}
              <div className="pt-2 border-t border-slate-100 font-medium text-slate-900 break-words-custom">
                <span className="font-bold text-indigo-900">Next Recommended Action: </span>
                {handoff.current_next_step}
              </div>
            </div>
          </div>
        ) : null}

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-100">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => downloadHandoffPdf(sessionId)}
              className="rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-700 flex items-center gap-1.5 shadow-2xs min-h-[44px]"
            >
              📄 Download PDF
            </button>
            <button
              type="button"
              onClick={() => downloadHandoffDocx(sessionId)}
              className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 flex items-center gap-1.5 shadow-2xs min-h-[44px]"
            >
              📝 Download DOCX
            </button>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-300 px-4 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 min-h-[44px]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

