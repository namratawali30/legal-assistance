import api from "./client";

export async function listChats() {
  const response = await api.get(
    "/api/v1/chats"
  );

  return response.data;
}

export async function createChat({
  title,
  category,
}) {
  const response = await api.post(
    "/api/v1/chats",
    {
      title,
      category,
    }
  );

  return response.data;
}

export async function getChat(
  chatId
) {
  const response = await api.get(
    `/api/v1/chats/${chatId}`
  );

  return response.data;
}

export async function updateChat(
  chatId,
  updateData
) {
  const response = await api.patch(
    `/api/v1/chats/${chatId}`,
    updateData
  );

  return response.data;
}

export async function sendChatMessage(
  chatId,
  content,
  answerMode = null
) {
  const payload = { content };
  if (answerMode) payload.answer_mode = answerMode;

  const response = await api.post(
    `/api/v1/chats/${chatId}/messages`,
    payload
  );

  return response.data;
}


export async function retryChatMessage(
  chatId,
  messageId
) {
  const response = await api.post(
    `/api/v1/chats/${chatId}/messages/${messageId}/retry`
  );

  return response.data;
}

export async function deleteChat(
  chatId
) {
  await api.delete(
    `/api/v1/chats/${chatId}`
  );
}