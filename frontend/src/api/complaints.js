import api from "./client";
export { triggerBlobDownload } from "./downloadUtils";

// ─────────────────────────────────────────────
// LIST
// ─────────────────────────────────────────────

export async function listComplaints() {
  const response = await api.get("/api/v1/complaints");
  return response.data;
}

// ─────────────────────────────────────────────
// GET
// ─────────────────────────────────────────────

export async function getComplaint(complaintId) {
  const response = await api.get(
    `/api/v1/complaints/${complaintId}`
  );
  return response.data;
}

// ─────────────────────────────────────────────
// CREATE
// ─────────────────────────────────────────────

export async function createComplaint({
  title,
  category,
  complainant_name,
  complainant_address,
  complainant_contact,
  respondent_name,
  respondent_address,
  incident_date,
  incident_location,
  facts,
  relief_requested,
}) {
  const payload = {
    title,
    category,
    complainant_name,
    complainant_address: complainant_address || null,
    complainant_contact: complainant_contact || null,
    respondent_name,
    respondent_address: respondent_address || null,
    incident_date: incident_date || null,
    incident_location: incident_location || null,
    facts,
    relief_requested: relief_requested || null,
    additional_details: {},
  };

  const response = await api.post(
    "/api/v1/complaints",
    payload
  );
  return response.data;
}

// ─────────────────────────────────────────────
// UPDATE DRAFT FIELDS
// ─────────────────────────────────────────────

export async function updateComplaint(complaintId, fields) {
  const response = await api.patch(
    `/api/v1/complaints/${complaintId}`,
    fields
  );
  return response.data;
}

// ─────────────────────────────────────────────
// DELETE
// ─────────────────────────────────────────────

export async function deleteComplaint(complaintId) {
  await api.delete(
    `/api/v1/complaints/${complaintId}`
  );
}

// ─────────────────────────────────────────────
// GENERATE / REGENERATE
// ─────────────────────────────────────────────

export async function generateComplaint(
  complaintId,
  { regenerate = false } = {}
) {
  const response = await api.post(
    `/api/v1/complaints/${complaintId}/generate`,
    { regenerate }
  );
  return response.data;
}

// ─────────────────────────────────────────────
// EDIT GENERATED TEXT
// ─────────────────────────────────────────────

export async function updateGeneratedText(
  complaintId,
  generated_text
) {
  const response = await api.patch(
    `/api/v1/complaints/${complaintId}/generated-text`,
    { generated_text }
  );
  return response.data;
}

// ─────────────────────────────────────────────
// FINALIZE
// ─────────────────────────────────────────────

export async function finalizeComplaint(complaintId) {
  const response = await api.post(
    `/api/v1/complaints/${complaintId}/finalize`,
    { confirm: true }
  );
  return response.data;
}

// ─────────────────────────────────────────────
// EXPORT — returns { blob, filename }
// Fetched via axios so JWT is sent in the
// Authorization header, never in a query param.
// ─────────────────────────────────────────────

async function downloadExport(url) {
  const response = await api.get(url, {
    responseType: "blob",
  });

  // Extract filename from Content-Disposition if present
  const disposition =
    response.headers["content-disposition"] || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match
    ? match[1]
    : url.split("/").pop() + "-export";

  return { blob: response.data, filename };
}

export async function exportComplaintPdf(complaintId) {
  return downloadExport(
    `/api/v1/complaints/${complaintId}/export/pdf`
  );
}

export async function exportComplaintDocx(complaintId) {
  return downloadExport(
    `/api/v1/complaints/${complaintId}/export/docx`
  );
}

