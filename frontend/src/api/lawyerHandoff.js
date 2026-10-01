import api from "./client";
import { triggerBlobDownload } from "./downloadUtils";


export async function fetchSessionLawyerHandoff(sessionId) {
  const response = await api.get(`/api/v1/lawyer-handoff/session/${sessionId}`);
  return response.data;
}

export async function downloadHandoffPdf(sessionId) {
  const response = await api.get(`/api/v1/lawyer-handoff/session/${sessionId}/export/pdf`, {
    responseType: "blob",
  });
  triggerBlobDownload(response.data, `lawyer_handoff_${sessionId}.pdf`);
}

export async function downloadHandoffDocx(sessionId) {
  const response = await api.get(`/api/v1/lawyer-handoff/session/${sessionId}/export/docx`, {
    responseType: "blob",
  });
  triggerBlobDownload(response.data, `lawyer_handoff_${sessionId}.docx`);
}
