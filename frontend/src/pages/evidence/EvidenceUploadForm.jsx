import { useRef, useState } from "react";
import { getApiErrorMessage } from "../../api/client";

const ACCEPTED_TYPES = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/jpeg",
  "image/png",
  "image/webp",
  "audio/mpeg",
  "audio/wav",
  "audio/x-wav",
  "audio/mp4",
  "audio/m4a",
  "audio/x-m4a",
  "video/mp4",
  "video/webm",
];

const ACCEPTED_EXTENSIONS = ".pdf,.txt,.docx,.jpg,.jpeg,.png,.webp,.mp3,.wav,.m4a,.mp4,.webm";
const MAX_SIZE_MB    = 50;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

const FORMAT_ICONS = {
  pdf:  { icon: "📄", color: "text-red-600",   bg: "bg-red-50"   },
  txt:  { icon: "📝", color: "text-slate-600", bg: "bg-slate-100"},
  docx: { icon: "📋", color: "text-blue-600",  bg: "bg-blue-50"  },
  jpg:  { icon: "🖼️",  color: "text-emerald-600", bg: "bg-emerald-50" },
  jpeg: { icon: "🖼️",  color: "text-emerald-600", bg: "bg-emerald-50" },
  png:  { icon: "🖼️",  color: "text-emerald-600", bg: "bg-emerald-50" },
  webp: { icon: "🖼️",  color: "text-emerald-600", bg: "bg-emerald-50" },
  mp3:  { icon: "🎵", color: "text-purple-600", bg: "bg-purple-50" },
  wav:  { icon: "🎵", color: "text-purple-600", bg: "bg-purple-50" },
  m4a:  { icon: "🎵", color: "text-purple-600", bg: "bg-purple-50" },
  mp4:  { icon: "🎬", color: "text-indigo-600", bg: "bg-indigo-50" },
  webm: { icon: "🎬", color: "text-indigo-600", bg: "bg-indigo-50" },
};

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function EvidenceUploadForm({
  onUploaded,
  onCancel,
  uploadHandler,
  complaints,
  defaultComplaintId,
}) {
  const [file,        setFile]        = useState(null);
  const [title,       setTitle]       = useState("");
  const [description, setDescription] = useState("");
  const [complaintId, setComplaintId] = useState(defaultComplaintId || "");
  const [uploading,   setUploading]   = useState(false);
  const [progress,    setProgress]    = useState(0);
  const [error,       setError]       = useState(null);
  const [dragOver,    setDragOver]    = useState(false);

  const fileInputRef = useRef(null);

  function validateFile(f) {
    if (!f) return "Please select a file.";
    if (f.size > MAX_SIZE_BYTES)
      return `File is too large. Maximum size is ${MAX_SIZE_MB} MB (this file is ${formatBytes(f.size)}).`;
    if (!ACCEPTED_TYPES.includes(f.type) && f.type !== "")
      return `Unsupported file type: ${f.type}. Accepted: PDF, TXT, DOCX, JPG, PNG, WEBP, MP3, WAV, MP4.`;
    return null;
  }

  function handleFileChange(f) {
    const err = validateFile(f);
    if (err) {
      setError(err);
      setFile(null);
    } else {
      setError(null);
      setFile(f);
      if (!title) {
        const name = f.name.replace(/\.[^/.]+$/, "");
        setTitle(name.slice(0, 200));
      }
    }
  }

  function handleInputChange(e) {
    const f = e.target.files?.[0];
    if (f) handleFileChange(f);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFileChange(f);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const err = validateFile(file);
    if (err) { setError(err); return; }

    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      const result = await uploadHandler({
        file,
        complaintId: complaintId || null,
        title: title.trim() || null,
        description: description.trim() || null,
        onUploadProgress: (evt) => {
          if (evt.total) setProgress(Math.round((evt.loaded * 100) / evt.total));
        },
      });
      onUploaded(result);
    } catch (err) {
      setError(getApiErrorMessage(err, "Upload failed. Please try again."));
    } finally {
      setUploading(false);
      setProgress(0);
    }
  }

  const fileExt = file?.name.split(".").pop()?.toLowerCase();
  const fileDisplay = FORMAT_ICONS[fileExt] || { icon: "📁", color: "text-slate-500", bg: "bg-slate-100" };

  return (
    <div className="min-h-full bg-mesh px-6 py-6">
      {/* Header */}
      <div className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-amber-600">Secure Evidence Vault</p>
        <h2 className="mt-1 text-2xl font-bold text-slate-900 font-heading">
          Upload Evidence File
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Supported: PDF, TXT, DOCX, JPG, PNG, WEBP, MP3, WAV, MP4 — max {MAX_SIZE_MB} MB
        </p>
      </div>

      {/* Security notice */}
      <div className="mb-6 flex items-start gap-3 rounded-2xl border border-indigo-200 bg-indigo-50/80 px-4 py-3.5 text-xs leading-5 text-indigo-950 shadow-2xs">
        <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-indigo-600" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
        </svg>
        <span>
          <strong className="text-indigo-900 font-bold">SHA-256 Vault Protection.</strong>{" "}
          Files are fingerprint-hashed upon upload to guarantee immutable evidence integrity. Access is strictly private to your authenticated account.
        </span>
      </div>

      <form onSubmit={handleSubmit} noValidate>
        <div className="space-y-5 max-w-xl">
          {/* ── Drop zone ── */}
          <div>
            <label className="block text-sm font-bold text-slate-800 mb-1.5 font-heading">
              Select Evidence File <span className="text-red-500" aria-hidden="true">*</span>
            </label>

            <div
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
              }}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={[
                "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-all duration-200 shadow-sm",
                dragOver
                  ? "border-amber-400 bg-amber-50 scale-[1.01]"
                  : file
                  ? "border-emerald-400 bg-emerald-50/70"
                  : "border-slate-300 bg-white hover:border-indigo-400 hover:bg-indigo-50/40",
              ].join(" ")}
              aria-label="File upload area — click or drag a file here"
            >
              {file ? (
                <>
                  <div className={`flex h-14 w-14 items-center justify-center rounded-2xl text-2xl ${fileDisplay.bg} shadow-sm`}>
                    {fileDisplay.icon}
                  </div>
                  <p className="mt-3 text-sm font-bold text-slate-900 font-heading">{file.name}</p>
                  <p className="mt-0.5 text-xs text-slate-500 font-mono">{formatBytes(file.size)}</p>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                      setError(null);
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }}
                    className="mt-3 text-xs font-bold text-red-600 hover:text-red-800 transition-colors"
                  >
                    Remove file
                  </button>
                </>
              ) : (
                <>
                  <div
                    className="flex h-14 w-14 items-center justify-center rounded-2xl"
                    style={{ background: dragOver ? "rgba(217, 119, 6, 0.15)" : "#f8fafc" }}
                  >
                    <svg className={`h-7 w-7 ${dragOver ? "text-amber-600" : "text-indigo-500"} transition-colors`} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                    </svg>
                  </div>
                  <p className="mt-3 text-sm font-bold text-slate-900 font-heading">
                    {dragOver ? "Drop file to upload" : "Click to select file or drag & drop"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    PDF, TXT, DOCX, JPG, PNG, WEBP, MP3, WAV, MP4 — max {MAX_SIZE_MB} MB
                  </p>
                </>
              )}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS}
              onChange={handleInputChange}
              disabled={uploading}
              className="sr-only"
              aria-hidden="true"
              tabIndex={-1}
            />
          </div>

          {/* ── Title ── */}
          <div>
            <label htmlFor="ev-title" className="block text-sm font-bold text-slate-800 mb-1.5 font-heading">
              Evidence Title <span className="text-slate-400 font-normal text-xs">(optional)</span>
            </label>
            <input
              id="ev-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={uploading}
              maxLength={200}
              placeholder="e.g. Purchase invoice or email record"
              className="form-input"
            />
          </div>

          {/* ── Description ── */}
          <div>
            <label htmlFor="ev-desc" className="block text-sm font-bold text-slate-800 mb-1.5 font-heading">
              Description <span className="text-slate-400 font-normal text-xs">(optional)</span>
            </label>
            <textarea
              id="ev-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={uploading}
              maxLength={2000}
              rows={3}
              placeholder="What does this evidence prove? Mention key dates or transactions..."
              className="form-input resize-none"
            />
          </div>

          {/* ── Link to complaint ── */}
          <div>
            <label htmlFor="ev-complaint" className="block text-sm font-bold text-slate-800 mb-1.5 font-heading">
              Link to Legal Complaint <span className="text-slate-400 font-normal text-xs">(optional)</span>
            </label>
            <select
              id="ev-complaint"
              value={complaintId}
              onChange={(e) => setComplaintId(e.target.value)}
              disabled={uploading}
              className="form-input bg-white"
            >
              <option value="">Unlinked Evidence Vault Item</option>
              {complaints.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title.length > 60 ? c.title.slice(0, 60) + "…" : c.title}
                </option>
              ))}
            </select>
            <p className="mt-1.5 text-xs text-slate-500">
              Linked evidence is automatically referenced in AI-drafted complaints with SHA-256 verified badges.
            </p>
          </div>

          {/* ── Upload progress ── */}
          {uploading && (
            <div>
              <div className="mb-1.5 flex justify-between text-xs font-bold text-slate-700">
                <span className="flex items-center gap-1.5">
                  <span className="h-3.5 w-3.5 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin-smooth" />
                  Hashing & Uploading Evidence…
                </span>
                <span className="text-indigo-600">{progress}%</span>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${progress}%`,
                    background: "linear-gradient(90deg, #4f46e5, #d97706)",
                  }}
                  role="progressbar"
                  aria-valuenow={progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
            </div>
          )}

          {/* ── Error ── */}
          {error && (
            <div role="alert" className="flex items-start gap-2.5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
              <svg className="h-4 w-4 flex-shrink-0 mt-0.5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
              </svg>
              {error}
            </div>
          )}

          {/* ── Actions ── */}
          <div className="flex items-center gap-3">
            <button
              type="submit"
              id="upload-submit-btn"
              disabled={uploading || !file}
              className="btn-primary py-2.5 px-6 font-bold text-sm shadow-md"
            >
              {uploading ? (
                <>
                  <span className="h-3.5 w-3.5 rounded-full border-2 border-white border-t-transparent animate-spin-smooth" />
                  Uploading…
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M9.25 13.25a.75.75 0 001.5 0V4.636l2.955 3.129a.75.75 0 001.09-1.03l-4.25-4.5a.75.75 0 00-1.09 0l-4.25 4.5a.75.75 0 101.09 1.03L9.25 4.636v8.614z" />
                    <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
                  </svg>
                  Upload File to Vault
                </>
              )}
            </button>

            <button
              type="button"
              onClick={onCancel}
              disabled={uploading}
              className="rounded-xl border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-300 disabled:opacity-50 transition-colors min-h-[44px]"
            >
              Cancel
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
