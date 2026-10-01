import api from "./client";

export async function fetchSessionReadiness(sessionId) {
  const response = await api.get(`/api/v1/readiness/session/${sessionId}`);
  return response.data;
}

export async function fetchComplaintReadiness(complaintId) {
  const response = await api.get(`/api/v1/readiness/complaint/${complaintId}`);
  return response.data;
}
