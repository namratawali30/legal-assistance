import ComplaintStatusBadge from "./ComplaintStatusBadge";

const CATEGORY_LABELS = {
  consumer_rights:    "Consumer Rights",
  labour_rights:      "Labour Rights",
  womens_safety:      "Women's Safety",
  educational_rights: "Educational Rights",
  anti_ragging:       "Anti-Ragging",
};

const CATEGORY_COLORS = {
  consumer_rights:    "text-blue-700 bg-blue-50 border border-blue-200",
  labour_rights:      "text-purple-700 bg-purple-50 border border-purple-200",
  womens_safety:      "text-rose-700 bg-rose-50 border border-rose-200",
  educational_rights: "text-emerald-700 bg-emerald-50 border border-emerald-200",
  anti_ragging:       "text-amber-800 bg-amber-50 border border-amber-200",
};

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function SkeletonItem() {
  return (
    <div className="px-4 py-4 border-b border-slate-100 animate-pulse">
      <div className="flex justify-between items-start gap-2">
        <div className="h-4 bg-slate-200 rounded w-3/5" />
        <div className="h-5 bg-slate-100 rounded-full w-16" />
      </div>
      <div className="mt-2 h-3 bg-slate-100 rounded w-2/5" />
    </div>
  );
}

export default function ComplaintList({
  complaints,
  selectedId,
  onSelect,
  onNewComplaint,
  loading,
}) {
  return (
    <div className="flex h-full flex-col bg-white border-r border-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-slate-200 bg-slate-50/60">
        <div>
          <h2 className="text-sm font-bold text-slate-900 font-heading">My Complaints</h2>
          {!loading && complaints.length > 0 && (
            <p className="mt-0.5 text-xs text-indigo-600 font-semibold">
              {complaints.length} complaint{complaints.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>

        <button
          type="button"
          id="new-complaint-btn"
          onClick={onNewComplaint}
          className="btn-primary py-2 px-3 text-xs font-bold shadow-sm flex items-center gap-1.5"
          aria-label="Create new complaint"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
          </svg>
          New
        </button>
      </div>

      {/* List body */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div>
            {[1, 2, 3].map((i) => <SkeletonItem key={i} />)}
          </div>
        ) : complaints.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center px-5 py-14 text-center">
            <div
              className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 border border-indigo-100"
            >
              <svg className="h-7 w-7 text-indigo-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <p className="text-sm font-bold text-slate-900 font-heading">No complaints yet</p>
            <p className="mt-1.5 text-xs text-slate-500 max-w-[200px]">
              Create your first complaint to begin drafting with AI assistance.
            </p>
            <button
              type="button"
              onClick={onNewComplaint}
              className="mt-5 btn-primary py-2 px-4 text-xs font-bold shadow-sm"
            >
              Create complaint
            </button>
          </div>
        ) : (
          <ul role="list" className="divide-y divide-slate-100">
            {complaints.map((complaint) => {
              const isSelected = selectedId === complaint.id;
              const catColor = CATEGORY_COLORS[complaint.category] || "text-slate-700 bg-slate-100 border border-slate-200";

              return (
                <li key={complaint.id}>
                  <button
                    type="button"
                    id={`complaint-item-${complaint.id}`}
                    onClick={() => onSelect(complaint.id)}
                    className={[
                      "w-full px-4 py-4 text-left transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-amber-400",
                      isSelected
                        ? "bg-indigo-50/80 border-l-4 border-indigo-600 shadow-2xs"
                        : "hover:bg-slate-50 border-l-4 border-transparent",
                    ].join(" ")}
                    aria-current={isSelected ? "page" : undefined}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p
                        className={[
                          "line-clamp-2 text-sm font-bold leading-snug font-heading",
                          isSelected ? "text-indigo-950" : "text-slate-900",
                        ].join(" ")}
                      >
                        {complaint.title}
                      </p>
                      <ComplaintStatusBadge status={complaint.status} />
                    </div>

                    <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${catColor}`}>
                        {CATEGORY_LABELS[complaint.category] || complaint.category}
                      </span>
                      <span className="text-xs text-slate-400">·</span>
                      <time dateTime={complaint.created_at} className="text-xs text-slate-500 font-medium">
                        {formatDate(complaint.created_at)}
                      </time>
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
