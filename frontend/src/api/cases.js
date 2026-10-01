import api from "./client";

export async function fetchCases() {
  const response = await api.get("/api/v1/cases");
  return response.data;
}

export async function fetchCaseById(caseId) {
  const response = await api.get(`/api/v1/cases/${caseId}`);
  return response.data;
}

export async function createCase(caseData) {
  const response = await api.post("/api/v1/cases", caseData);
  return response.data;
}

export async function updateCase(caseId, updateData) {
  const response = await api.patch(`/api/v1/cases/${caseId}`, updateData);
  return response.data;
}

export async function recordCaseSubmission(caseId, submissionData) {
  const response = await api.post(`/api/v1/cases/${caseId}/submission`, submissionData);
  return response.data;
}

export async function addCaseReminder(caseId, reminderData) {
  const response = await api.post(`/api/v1/cases/${caseId}/reminders`, reminderData);
  return response.data;
}
