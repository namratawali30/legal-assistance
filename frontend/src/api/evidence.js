import api from "./client";
export { triggerBlobDownload } from "./downloadUtils";

// ─────────────────────────────────────────────
// LIST
// Optional complaint_id filter: GET /api/v1/evidence?complaint_id=xxx
// ─────────────────────────────────────────────

export async function listEvidence({ complaintId } = {}) {
  const params = complaintId
    ? { complaint_id: complaintId }
    : {};
  const response = await api.get("/api/v1/evidence", { params });
  return response.data;
}

// ─────────────────────────────────────────────
// GET SINGLE
// ─────────────────────────────────────────────

export async function getEvidence(evidenceId) {
  const response = await api.get(
    `/api/v1/evidence/${evidenceId}`
  );
  return response.data;
}

// ─────────────────────────────────────────────
// UPLOAD  (multipart/form-data)
//
// The backend expects: file, complaint_id?, title?, description?
// We use FormData — axios sets Content-Type automatically.
// ─────────────────────────────────────────────

export async function uploadEvidence({
  file,
  complaintId,
  title,
  description,
  onUploadProgress,
}) {
  const form = new FormData();
  form.append("file", file);

  if (complaintId) form.append("complaint_id", complaintId);
  if (title) form.append("title", title);
  if (description) form.append("description", description);

  const response = await api.post("/api/v1/evidence", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
  return response.data;
}

// ─────────────────────────────────────────────
// UPDATE METADATA (title / description)
// ─────────────────────────────────────────────

export async function updateEvidence(evidenceId, { title, description }) {
  const payload = {};
  if (title !== undefined) payload.title = title;
  if (description !== undefined) payload.description = description;

  const response = await api.patch(
    `/api/v1/evidence/${evidenceId}`,
    payload
  );
  return response.data;
}

// ─────────────────────────────────────────────
// PROCESS / RETRY
// retry=false → initial processing (fails if already processed)
// retry=true  → re-process (use for failed / requires_ocr)
// ─────────────────────────────────────────────

export async function processEvidence(evidenceId, { retry = false } = {}) {
  const response = await api.post(
    `/api/v1/evidence/${evidenceId}/process`,
    { retry }
  );
  return response.data;
}

// ─────────────────────────────────────────────
// DOWNLOAD  — authenticated via axios blob fetch
// JWT is sent in Authorization header, never in URL.
// Returns { blob, filename }
// ─────────────────────────────────────────────

export async function downloadEvidence(evidenceId, originalFilename) {
  const response = await api.get(
    `/api/v1/evidence/${evidenceId}/download`,
    { responseType: "blob" }
  );

  const disposition =
    response.headers["content-disposition"] || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match
    ? match[1]
    : originalFilename || `evidence-${evidenceId}`;

  return { blob: response.data, filename };
}

// ─────────────────────────────────────────────
// DELETE
// ─────────────────────────────────────────────

export async function deleteEvidence(evidenceId) {
  await api.delete(`/api/v1/evidence/${evidenceId}`);
}
