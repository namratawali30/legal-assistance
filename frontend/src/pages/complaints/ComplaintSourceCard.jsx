export default function ComplaintSourceCard({ source }) {
  return (
    <div className="group rounded-xl border border-indigo-100 bg-gradient-to-r from-indigo-50 to-violet-50 p-4 text-xs transition-shadow hover:shadow-sm">
      <div className="flex items-start justify-between gap-3">
        {/* Citation badge */}
        <span
          className="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-bold text-white flex-shrink-0"
          style={{ background: "linear-gradient(135deg, #6366f1, #7c3aed)" }}
        >
          {source.citation_id}
        </span>
        <span className="text-xs font-semibold text-indigo-500 uppercase tracking-wide">
          LAW
        </span>
      </div>

      <p className="mt-2.5 font-semibold text-slate-800 leading-snug">
        {source.title || "Legal source"}
      </p>

      {source.authority && (
        <p className="mt-1 text-slate-500">{source.authority}</p>
      )}

      {source.provision_number && (
        <p className="mt-1 text-slate-600">
          {source.provision_type ? `${source.provision_type} ` : ""}
          {source.provision_number}
          {source.provision_title ? ` — ${source.provision_title}` : ""}
        </p>
      )}

      {source.landing_page && (
        <a
          href={source.landing_page}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 block truncate text-indigo-500 underline decoration-indigo-200 hover:text-indigo-700 hover:decoration-indigo-400 transition-colors"
        >
          {source.landing_page}
        </a>
      )}
    </div>
  );
}
