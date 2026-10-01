import api from "./client";

export async function fetchSessionActionPlan(sessionId) {
  const response = await api.get(`/api/v1/action-plan/session/${sessionId}`);
  return response.data;
}

export async function fetchComplaintActionPlan(complaintId) {
  const response = await api.get(`/api/v1/action-plan/complaint/${complaintId}`);
  return response.data;
}
