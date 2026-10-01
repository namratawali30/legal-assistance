const STATUS_CONFIG = {
  draft: {
    label: "Draft",
    dot: "bg-slate-400",
    className: "bg-slate-100 text-slate-600 border border-slate-200",
  },
  generated: {
    label: "Generated",
    dot: "bg-blue-400",
    className: "bg-blue-50 text-blue-700 border border-blue-200",
  },
  edited: {
    label: "Edited",
    dot: "bg-amber-400",
    className: "bg-amber-50 text-amber-700 border border-amber-200",
  },
  finalized: {
    label: "Finalized",
    dot: "bg-emerald-400",
    className: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  },
};

export default function ComplaintStatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.draft;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${config.className}`}
    >
      {status === "finalized" ? (
        <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path
            fillRule="evenodd"
            d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
            clipRule="evenodd"
          />
        </svg>
      ) : (
        <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} aria-hidden="true" />
      )}
      {config.label}
    </span>
  );
}
