import { useState } from "react";

export default function FingerprintBadge({ hash, verified = false, verifiedLabel = "Verified SHA-256" }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!hash) return null;

  const shortHash = hash.length > 16 ? `${hash.slice(0, 10)}...${hash.slice(-8)}` : hash;

  async function handleCopy(e) {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(hash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  }

  return (
    <div className="inline-flex flex-col gap-1 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs font-mono text-slate-700 shadow-2xs">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 font-sans font-semibold text-[11px] text-slate-600">
          <svg className="h-3.5 w-3.5 text-teal-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
          </svg>
          <span>SHA-256 Fingerprint</span>
        </div>

        {verified && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-sans font-semibold text-emerald-800">
            <svg className="h-3 w-3 text-emerald-600" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
            </svg>
            {verifiedLabel}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between gap-2 mt-0.5">
        <span className="break-all select-all font-mono text-[11px] text-slate-800">
          {expanded ? hash : shortHash}
        </span>

        <div className="flex items-center gap-1 font-sans flex-shrink-0">
          <button
            type="button"
            onClick={handleCopy}
            className="rounded px-1.5 py-0.5 text-[10px] font-semibold text-teal-700 hover:bg-teal-50 transition-colors cursor-pointer"
            title="Copy full SHA-256 hash"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
          {hash.length > 16 && (
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="rounded px-1.5 py-0.5 text-[10px] font-semibold text-slate-500 hover:bg-slate-200 transition-colors cursor-pointer"
            >
              {expanded ? "Collapse" : "Expand"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
