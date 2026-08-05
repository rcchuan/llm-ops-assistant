import type {
  ChatHistoryResponse,
  ChatMessage,
  CurrentChatResponse,
  Feedback,
} from "../types/chat"
import { http } from "./http"

export async function getCurrentChat(): Promise<CurrentChatResponse> {
  const response = await http.get<CurrentChatResponse>("/chat/current")
  return response.data
}

export async function sendChatMessage(question: string, startNew: boolean): Promise<ChatMessage> {
  const response = await http.post<ChatMessage>(
    "/chat/messages",
    { question, start_new: startNew },
    { timeout: 65_000 },
  )
  return response.data
}

export async function startNewChat(): Promise<void> {
  await http.post("/chat/new")
}

export async function getChatHistory(): Promise<ChatMessage[]> {
  const response = await http.get<ChatHistoryResponse>("/chat/history", {
    params: { limit: 50 },
  })
  return response.data.items
}

export async function updateChatFeedback(id: number, feedback: Feedback): Promise<ChatMessage> {
  const response = await http.put<ChatMessage>(`/chat/messages/${id}/feedback`, { feedback })
  return response.data
}
