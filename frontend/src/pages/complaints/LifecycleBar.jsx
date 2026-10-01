const STEPS = [
  { key: "draft",     label: "Draft",     desc: "Filling in details" },
  { key: "generated", label: "Generated", desc: "AI drafted" },
  { key: "edited",    label: "Edited",    desc: "Reviewed & edited" },
  { key: "finalized", label: "Finalized", desc: "Ready to export" },
];

const ORDER = { draft: 0, generated: 1, edited: 2, finalized: 3 };

export default function LifecycleBar({ status }) {
  const currentIndex = ORDER[status] ?? 0;

  return (
    <nav aria-label="Complaint lifecycle" className="flex items-center">
      {STEPS.map((step, index) => {
        const isDone   = index < currentIndex;
        const isActive = index === currentIndex;
        const isLast   = index === STEPS.length - 1;

        return (
          <div key={step.key} className="flex items-center">
            {/* Step node */}
            <div className="flex flex-col items-center">
              <div
                className={[
                  "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all duration-300",
                  isDone
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-200"
                    : isActive
                    ? "ring-2 ring-indigo-500 ring-offset-2 bg-white text-indigo-600"
                    : "bg-slate-100 text-slate-400",
                ].join(" ")}
                aria-current={isActive ? "step" : undefined}
              >
                {isDone ? (
                  <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                  </svg>
                ) : (
                  index + 1
                )}
              </div>

              {/* Step label (hidden on very small screens) */}
              <div className="mt-1.5 hidden items-center flex-col sm:flex">
                <span
                  className={[
                    "text-xs font-semibold leading-none",
                    isActive ? "text-indigo-700" : isDone ? "text-slate-600" : "text-slate-400",
                  ].join(" ")}
                >
                  {step.label}
                </span>
                <span className={["text-xs leading-none mt-0.5", isActive ? "text-indigo-500" : "text-slate-400"].join(" ")}>
                  {step.desc}
                </span>
              </div>
            </div>

            {/* Connector */}
            {!isLast && (
              <div
                className={[
                  "mx-1.5 mb-5 h-0.5 flex-shrink-0 transition-colors duration-300 sm:mx-3",
                  "w-8 sm:w-14",
                  index < currentIndex ? "bg-indigo-500" : "bg-slate-200",
                ].join(" ")}
                aria-hidden="true"
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
