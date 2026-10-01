import { useFocusTrap } from "../hooks/useFocusTrap";

export default function SourceDetailsModal({ isOpen, onClose, source }) {
  const modalRef = useFocusTrap(isOpen, onClose);

  if (!isOpen || !source) return null;

  const isIndiaCode =
    source.source_provider === "India Code" ||
    source.source_mode === "live" ||
    source.source_mode === "cached_live";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-3 sm:p-4 backdrop-blur-xs animate-fade-in"
      onClick={onClose}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-details-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-5 sm:p-6 shadow-2xl border border-slate-200 outline-none"
      >
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-bold text-indigo-800">
                {source.citation_id || "SOURCE_1"}
              </span>
              <h2 id="source-details-title" className="text-base sm:text-lg font-bold text-slate-900">
                Legal Source Details
              </h2>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Verified legal authority grounding this response
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Close legal source details modal"
          >
            ✕
          </button>
        </div>

        <div className="mt-5 space-y-4 text-xs">
          {/* Source Status & Freshness Badge */}
          <div className="flex items-center justify-between rounded-xl bg-emerald-50 border border-emerald-200 p-3 text-emerald-900">
            <div className="flex items-center gap-2 font-semibold">
              <svg className="h-4 w-4 text-emerald-600 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
              </svg>
              <span className="truncate">{isIndiaCode ? "Official Source · India Code" : "Verified Local Knowledge Base"}</span>
            </div>
            {source.fetched_at && (
              <span className="text-[10px] text-emerald-700 flex-shrink-0 ml-2">
                Last checked: {new Date(source.fetched_at).toLocaleDateString()}
              </span>
            )}
          </div>

          {/* WHAT LAW IS THIS? */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5">
            <div className="font-bold text-slate-500 uppercase tracking-wider text-[10px]">
              What Law is This?
            </div>
            <div className="mt-1 text-sm font-bold text-slate-900 break-words-custom">
              {source.title || "Indian Legal Provision"}
            </div>
          </div>

          {/* WHICH PROVISION? */}
          {source.provision_number && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5">
              <div className="font-bold text-slate-500 uppercase tracking-wider text-[10px]">
                Which Provision?
              </div>
              <div className="mt-1 text-sm font-semibold text-slate-800 break-words-custom">
                {source.provision_type ? `${source.provision_type.charAt(0).toUpperCase() + source.provision_type.slice(1)} ` : "Section "}
                {source.provision_number}
                {source.provision_title ? ` — ${source.provision_title}` : ""}
              </div>
            </div>
          )}

          {/* WHY THIS SOURCE MATTERS */}
          <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5">
            <div className="font-bold text-slate-500 uppercase tracking-wider text-[10px]">
              Why This Source Matters
            </div>
            <p className="mt-1 text-xs leading-relaxed text-slate-700">
              Supports the complaint procedure and legal remedies mentioned in the answer.
            </p>
          </div>

          {/* AUTHORITY & JURISDICTION */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {source.authority && (
              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <div className="font-bold text-slate-500 uppercase tracking-wider text-[10px]">
                  Authority
                </div>
                <div className="mt-1 text-xs font-semibold text-slate-800 break-words-custom">
                  {source.authority}
                </div>
              </div>
            )}

            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
              <div className="font-bold text-slate-500 uppercase tracking-wider text-[10px]">
                Official Source
              </div>
              <div className="mt-1 text-xs font-semibold text-slate-800">
                {isIndiaCode ? "India Code" : "Verified Knowledge Repository"}
              </div>
            </div>
          </div>

          {/* OFFICIAL LINK BUTTON */}
          {(source.official_url || source.landing_page) && (
            <div className="pt-2">
              <a
                href={source.official_url || source.landing_page}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3 px-4 text-xs font-semibold text-white hover:bg-indigo-700 transition-colors shadow-2xs min-h-[44px]"
              >
                View official source →
              </a>
            </div>
          )}
        </div>

        <div className="mt-5 flex justify-end">
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

