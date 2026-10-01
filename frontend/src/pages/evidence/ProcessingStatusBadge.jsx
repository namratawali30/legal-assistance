const STATUS_CONFIG = {
  pending: {
    label: "Pending",
    dot: "bg-slate-400",
    className: "bg-slate-100 text-slate-600 border border-slate-200",
    description: "Uploaded — not yet processed.",
  },
  processing: {
    label: "Processing",
    dot: "bg-blue-400",
    className: "bg-blue-50 text-blue-700 border border-blue-200",
    description: "Text extraction in progress.",
    spin: true,
  },
  ready: {
    label: "Ready",
    dot: "bg-emerald-400",
    className: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    description: "Text extracted — available for complaint grounding.",
  },
  no_text: {
    label: "No text",
    dot: "bg-slate-400",
    className: "bg-slate-100 text-slate-500 border border-slate-200",
    description: "No extractable text found in this file.",
  },
  requires_ocr: {
    label: "Requires OCR",
    dot: "bg-amber-400",
    className: "bg-amber-50 text-amber-700 border border-amber-200",
    description: "Image-based content — OCR is not yet supported.",
  },
  failed: {
    label: "Failed",
    dot: "bg-red-400",
    className: "bg-red-50 text-red-700 border border-red-200",
    description: "Processing failed. You can retry.",
  },
};

export default function ProcessingStatusBadge({ status, showDescription = false }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;

  return (
    <span className="inline-flex flex-col gap-1">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${config.className}`}
      >
        {config.spin ? (
          <span
            className="h-2 w-2 animate-spin-smooth rounded-full border-2 border-current border-t-transparent"
            aria-hidden="true"
          />
        ) : (
          <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} aria-hidden="true" />
        )}
        {config.label}
      </span>

      {showDescription && (
        <span className="text-xs text-slate-500">{config.description}</span>
      )}
    </span>
  );
}
