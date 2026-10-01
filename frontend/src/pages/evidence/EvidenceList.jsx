import ProcessingStatusBadge from "./ProcessingStatusBadge";

const TYPE_ICON_CONFIG = {
  document: { bg: "bg-indigo-50", icon: "text-indigo-500" },
  image:    { bg: "bg-emerald-50", icon: "text-emerald-500" },
  text:     { bg: "bg-amber-50",   icon: "text-amber-500"  },
  other:    { bg: "bg-slate-100",  icon: "text-slate-400"  },
};

function TypeIcon({ type }) {
  const config = TYPE_ICON_CONFIG[type] || TYPE_ICON_CONFIG.other;
  return (
    <span className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl ${config.bg}`}>
      {type === "document" && (
        <svg className={`h-4.5 w-4.5 ${config.icon}`} style={{ height: "1.125rem", width: "1.125rem" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.75} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
      )}
      {type === "image" && (
        <svg className={`h-4.5 w-4.5 ${config.icon}`} style={{ height: "1.125rem", width: "1.125rem" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.75} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
        </svg>
      )}
      {type === "text" && (
        <svg className={`h-4.5 w-4.5 ${config.icon}`} style={{ height: "1.125rem", width: "1.125rem" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.75} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12" />
        </svg>
      )}
      {(!type || type === "other") && (
        <svg className={`h-4.5 w-4.5 ${config.icon}`} style={{ height: "1.125rem", width: "1.125rem" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.75} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
        </svg>
      )}
    </span>
  );
}

function formatBytes(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
  });
}

function SkeletonItem() {
  return (
    <div className="px-4 py-4 border-b border-slate-100 animate-pulse">
      <div className="flex items-start gap-2.5">
        <div className="h-9 w-9 rounded-xl bg-slate-200 flex-shrink-0" />
        <div className="flex-1 space-y-2 pt-0.5">
          <div className="h-3.5 bg-slate-200 rounded w-4/5" />
          <div className="h-3 bg-slate-100 rounded w-2/5" />
          <div className="h-4 bg-slate-100 rounded-full w-20" />
        </div>
      </div>
    </div>
  );
}

export default function EvidenceList({
  evidence,
  selectedId,
  onSelect,
  onUpload,
  loading,
  filterComplaintId,
  onFilterChange,
  complaints,
}) {
  return (
    <div className="flex h-full flex-col bg-white border-r border-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-slate-100">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">Evidence Vault</h2>
          {!loading && evidence.length > 0 && (
            <p className="mt-0.5 text-xs text-slate-400">
              {evidence.length} file{evidence.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>

        <button
          type="button"
          id="upload-evidence-btn"
          onClick={onUpload}
          className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          style={{ background: "linear-gradient(135deg, #6366f1, #4f46e5)" }}
          aria-label="Upload evidence"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M9.25 13.25a.75.75 0 001.5 0V4.636l2.955 3.129a.75.75 0 001.09-1.03l-4.25-4.5a.75.75 0 00-1.09 0l-4.25 4.5a.75.75 0 101.09 1.03L9.25 4.636v8.614z" />
            <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
          </svg>
          Upload
        </button>
      </div>

      {/* Complaint filter */}
      {complaints && complaints.length > 0 && (
        <div className="border-b border-slate-100 px-4 py-3 bg-slate-50/50">
          <label className="block text-xs font-medium text-slate-500 mb-1.5">
            Filter by complaint
          </label>
          <select
            value={filterComplaintId || ""}
            onChange={(e) => onFilterChange(e.target.value || null)}
            className="block w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 transition-colors"
          >
            <option value="">All evidence</option>
            {complaints.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title.length > 40 ? c.title.slice(0, 40) + "…" : c.title}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* List body */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div>
            {[1, 2, 3].map((i) => <SkeletonItem key={i} />)}
          </div>
        ) : evidence.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-5 py-14 text-center">
            <div
              className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl"
              style={{ background: "linear-gradient(135deg, rgb(99 102 241 / 0.12), rgb(139 92 246 / 0.08))" }}
            >
              <svg className="h-7 w-7 text-indigo-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 7.5h-.75A2.25 2.25 0 004.5 9.75v7.5a2.25 2.25 0 002.25 2.25h7.5a2.25 2.25 0 002.25-2.25v-7.5a2.25 2.25 0 00-2.25-2.25h-.75m0-3l-3-3m0 0l-3 3m3-3v11.25m6-2.25h.75a2.25 2.25 0 012.25 2.25v7.5a2.25 2.25 0 01-2.25 2.25h-7.5a2.25 2.25 0 01-2.25-2.25v-.75" />
              </svg>
            </div>
            <p className="text-sm font-semibold text-slate-700">
              {filterComplaintId ? "No evidence linked to this complaint" : "No evidence yet"}
            </p>
            <p className="mt-1.5 text-xs text-slate-500 max-w-[200px]">
              {filterComplaintId
                ? "Upload evidence and link it to the complaint."
                : "Upload documents, images, or text files to support your complaints."}
            </p>
            <button
              type="button"
              onClick={onUpload}
              className="mt-5 rounded-xl px-4 py-2 text-xs font-semibold text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              style={{ background: "linear-gradient(135deg, #6366f1, #4f46e5)" }}
            >
              Upload evidence
            </button>
          </div>
        ) : (
          <ul role="list" className="divide-y divide-slate-50">
            {evidence.map((item) => {
              const isSelected = selectedId === item.id;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    id={`evidence-item-${item.id}`}
                    onClick={() => onSelect(item.id)}
                    className={[
                      "w-full px-4 py-4 text-left transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-400",
                      isSelected
                        ? "bg-indigo-50 border-l-2 border-indigo-500"
                        : "hover:bg-slate-50 border-l-2 border-transparent",
                    ].join(" ")}
                    aria-current={isSelected ? "page" : undefined}
                  >
                    <div className="flex items-start gap-2.5">
                      <TypeIcon type={item.evidence_type} />

                      <div className="min-w-0 flex-1">
                        <p
                          className={[
                            "truncate text-sm font-medium leading-snug",
                            isSelected ? "text-indigo-800" : "text-slate-800",
                          ].join(" ")}
                        >
                          {item.title || item.original_filename}
                        </p>

                        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-slate-400">
                          {item.file_extension && (
                            <span className="font-mono uppercase text-slate-500">
                              {item.file_extension}
                            </span>
                          )}
                          <span aria-hidden="true">·</span>
                          <span>{formatBytes(item.size_bytes)}</span>
                          <span aria-hidden="true">·</span>
                          <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
                        </div>

                        <div className="mt-1.5">
                          <ProcessingStatusBadge status={item.processing_status} />
                        </div>
                      </div>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
