import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import {
  deleteEvidence,
  downloadEvidence,
  getEvidence,
  listEvidence,
  processEvidence,
  triggerBlobDownload,
  uploadEvidence,
} from "../api/evidence";
import { listComplaints } from "../api/complaints";
import { getApiErrorMessage } from "../api/client";

import EvidenceList from "./evidence/EvidenceList";
import EvidenceUploadForm from "./evidence/EvidenceUploadForm";
import EvidenceDetailPanel from "./evidence/EvidenceDetailPanel";

// ─────────────────────────────────────────────
// EvidencePage
// ─────────────────────────────────────────────

export default function EvidencePage() {
  const { evidenceId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // ── Evidence list state ──
  const [evidence, setEvidence] = useState([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState(null);
  // Initialise filter from ?complaint= URL param if present
  const [filterComplaintId, setFilterComplaintId] = useState(
    () => searchParams.get("complaint") || null
  );

  // ── Complaint list (for filter + upload form) ──
  const [complaints, setComplaints] = useState([]);

  // ── Detail panel state ──
  const [activeEvidence, setActiveEvidence] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  // ── View mode — open upload form immediately if ?upload=1 ──
  const [showUploadForm, setShowUploadForm] = useState(
    () => searchParams.get("upload") === "1"
  );

  // Consume search params once on mount so the URL stays clean
  useEffect(() => {
    if (searchParams.has("complaint") || searchParams.has("upload")) {
      setSearchParams({}, { replace: true });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─────────────────────────────────────────────
  // Load evidence list
  // ─────────────────────────────────────────────

  async function fetchEvidence(complaintIdFilter) {
    setListLoading(true);
    setListError(null);
    try {
      const data = await listEvidence(
        complaintIdFilter
          ? { complaintId: complaintIdFilter }
          : {}
      );
      // Newest first
      setEvidence(
        [...data].sort(
          (a, b) =>
            new Date(b.created_at) - new Date(a.created_at)
        )
      );
    } catch (err) {
      setListError(
        getApiErrorMessage(err, "Could not load evidence.")
      );
    } finally {
      setListLoading(false);
    }
  }

  useEffect(() => {
    async function loadEvidence() {
      setListLoading(true);
      setListError(null);
      try {
        const data = await listEvidence(
          filterComplaintId
            ? { complaintId: filterComplaintId }
            : {}
        );
        setEvidence(
          [...data].sort(
            (a, b) =>
              new Date(b.created_at) - new Date(a.created_at)
          )
        );
      } catch (err) {
        setListError(
          getApiErrorMessage(err, "Could not load evidence.")
        );
      } finally {
        setListLoading(false);
      }
    }

    loadEvidence();
  }, [filterComplaintId]);

  // Load complaints list for filter + upload
  useEffect(() => {
    async function loadComplaints() {
      try {
        const data = await listComplaints();
        setComplaints(data);
      } catch {
        // Non-critical — complaint selector will just be empty
      }
    }

    loadComplaints();
  }, []);

  // ─────────────────────────────────────────────
  // Load detail when URL param changes
  // ─────────────────────────────────────────────

  useEffect(() => {
    async function loadDetail() {
      if (!evidenceId) {
        setActiveEvidence(null);
        setDetailError(null);
        return;
      }

      setDetailLoading(true);
      setDetailError(null);
      setShowUploadForm(false);

      try {
        const data = await getEvidence(evidenceId);
        setActiveEvidence(data);
      } catch (err) {
        setDetailError(
          getApiErrorMessage(
            err,
            "Could not load evidence details."
          )
        );
        setActiveEvidence(null);
      } finally {
        setDetailLoading(false);
      }
    }

    loadDetail();
  }, [evidenceId]);

  // ─────────────────────────────────────────────
  // Handlers
  // ─────────────────────────────────────────────

  function handleSelect(id) {
    setShowUploadForm(false);
    navigate(`/evidence/${id}`);
  }

  function handleUploadClick() {
    setShowUploadForm(true);
    setActiveEvidence(null);
    navigate("/evidence");
  }

  function handleCancelUpload() {
    setShowUploadForm(false);
    if (evidence.length > 0) {
      navigate(`/evidence/${evidence[0].id}`);
    } else {
      navigate("/evidence");
    }
  }

  function handleUploaded(newEvidence) {
    setEvidence((prev) => [newEvidence, ...prev]);
    setShowUploadForm(false);
    navigate(`/evidence/${newEvidence.id}`);
  }

  function handleEvidenceUpdated(updated) {
    setActiveEvidence(updated);
    setEvidence((prev) =>
      prev.map((e) => (e.id === updated.id ? updated : e))
    );
  }

  function handleEvidenceDeleted(id) {
    setEvidence((prev) => prev.filter((e) => e.id !== id));
    setActiveEvidence(null);
    navigate("/evidence");
  }

  function handleFilterChange(complaintId) {
    setFilterComplaintId(complaintId || null);
    navigate("/evidence");
  }

  // ── Download wrapper — fetches blob then triggers save ──
  async function handleDownload(id, originalFilename) {
    const { blob, filename } = await downloadEvidence(
      id,
      originalFilename
    );
    triggerBlobDownload(blob, filename);
  }

  // ── Find linked complaint for detail panel ──
  const linkedComplaint = activeEvidence?.complaint_id
    ? complaints.find(
        (c) => c.id === activeEvidence.complaint_id
      ) || null
    : null;

  // ─────────────────────────────────────────────
  // Determine what to show in right panel
  // ─────────────────────────────────────────────

  const showDetail =
    !showUploadForm &&
    (activeEvidence || detailLoading || detailError);

  // ─────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────

  return (
    <div className="flex h-screen flex-col lg:flex-row">
      {/* ── Left panel: evidence list ── */}
      <div
        className={[
          "flex-shrink-0 overflow-hidden",
          "lg:w-80 lg:border-r lg:border-slate-200",
          showDetail || showUploadForm
            ? "hidden lg:flex lg:flex-col"
            : "flex flex-col",
        ].join(" ")}
      >
        {listError ? (
          <div className="p-4 text-sm text-red-600">
            {listError}
            <button
              type="button"
              onClick={() =>
                fetchEvidence(filterComplaintId)
              }
              className="ml-2 underline"
            >
              Retry
            </button>
          </div>
        ) : (
          <EvidenceList
            evidence={evidence}
            selectedId={evidenceId}
            onSelect={handleSelect}
            onUpload={handleUploadClick}
            loading={listLoading}
            filterComplaintId={filterComplaintId}
            onFilterChange={handleFilterChange}
            complaints={complaints}
          />
        )}
      </div>

      {/* ── Right panel ── */}
      <div className="flex min-w-0 flex-1 flex-col overflow-y-auto">
        {/* Mobile back button */}
        {(showDetail || showUploadForm) && (
          <div className="flex items-center border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
            <button
              type="button"
              onClick={() => navigate("/evidence")}
              className="flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-800"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"
                />
              </svg>
              All evidence
            </button>
          </div>
        )}

        {/* Upload form */}
        {showUploadForm ? (
          <EvidenceUploadForm
            uploadHandler={uploadEvidence}
            onUploaded={handleUploaded}
            onCancel={handleCancelUpload}
            complaints={complaints}
            defaultComplaintId={filterComplaintId}
          />
        ) : detailLoading ? (
          <div className="flex flex-1 items-center justify-center py-24">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          </div>
        ) : detailError ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-24 text-center">
            <p className="text-sm text-red-600">{detailError}</p>
            <button
              type="button"
              onClick={() =>
                navigate(`/evidence/${evidenceId}`)
              }
              className="text-sm text-indigo-600 underline hover:text-indigo-800"
            >
              Try again
            </button>
          </div>
        ) : activeEvidence ? (
          <EvidenceDetailPanel
            evidence={activeEvidence}
            onUpdated={handleEvidenceUpdated}
            onDeleted={handleEvidenceDeleted}
            processHandler={processEvidence}
            downloadHandler={handleDownload}
            deleteHandler={deleteEvidence}
            linkedComplaint={linkedComplaint}
          />
        ) : (
          /* Empty-selection state — desktop only */
          <div className="hidden flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center lg:flex">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-indigo-50">
              <svg
                className="h-8 w-8 text-indigo-400"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M7.5 7.5h-.75A2.25 2.25 0 004.5 9.75v7.5a2.25 2.25 0 002.25 2.25h7.5a2.25 2.25 0 002.25-2.25v-7.5a2.25 2.25 0 00-2.25-2.25h-.75m0-3l-3-3m0 0l-3 3m3-3v11.25m6-2.25h.75a2.25 2.25 0 012.25 2.25v7.5a2.25 2.25 0 01-2.25 2.25h-7.5a2.25 2.25 0 01-2.25-2.25v-.75"
                />
              </svg>
            </div>
            <div>
              <p className="text-base font-semibold text-slate-700">
                Select evidence or upload a file
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Choose from the list on the left, or click{" "}
                <strong>Upload</strong> to add new evidence.
              </p>
            </div>
            <button
              type="button"
              onClick={handleUploadClick}
              className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              Upload evidence
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
