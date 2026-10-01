export default function ComplaintEvidenceRefs({ evidenceReferences }) {
  if (!evidenceReferences || evidenceReferences.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-500">
        <svg className="h-3.5 w-3.5 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
        </svg>
        Evidence used in this complaint
      </h4>
      <div className="flex flex-col gap-2">
        {evidenceReferences.map((ref) => (
          <div
            key={ref.citation_id}
            className="rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50 p-4 text-xs"
          >
            <div className="flex items-start justify-between gap-3">
              <span
                className="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-bold text-white flex-shrink-0"
                style={{ background: "linear-gradient(135deg, #f59e0b, #d97706)" }}
              >
                {ref.citation_id}
              </span>
              <span className="text-xs font-semibold text-amber-600 uppercase tracking-wide">
                EVIDENCE
              </span>
            </div>

            <p className="mt-2.5 font-semibold text-slate-800 leading-snug">
              {ref.title || ref.original_filename || "Uploaded evidence"}
            </p>

            <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-slate-500">
              {ref.original_filename && (
                <span className="font-mono">{ref.original_filename}</span>
              )}
              {ref.evidence_type && (
                <span className="capitalize rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 font-medium">
                  {ref.evidence_type}
                </span>
              )}
              {ref.media_type && (
                <span className="text-slate-400">{ref.media_type}</span>
              )}
              {ref.included_characters > 0 && (
                <span className="text-slate-500">
                  {ref.included_characters.toLocaleString()} chars
                  {ref.truncated && " (truncated)"}
                </span>
              )}
              {ref.extracted_page_count && (
                <span>{ref.extracted_page_count} pages</span>
              )}
            </div>

            {ref.sha256 && (
              <p
                className="mt-2 truncate font-mono text-slate-400"
                title={`SHA-256: ${ref.sha256}`}
              >
                <span className="font-semibold text-slate-500">SHA-256: </span>
                {ref.sha256.slice(0, 24)}…
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
