export type Feedback = "helpful" | "unhelpful"

export interface ChatSource {
  document_name: string
  content: string
}

export interface ChatMessage {
  id: number | null
  question: string
  answer: string
  resources: ChatSource[]
  feedback: Feedback | null
  created_at: string
  persisted: boolean | null
  conversation_locked: boolean
}

export interface CurrentChatResponse {
  conversation_id: number | null
  messages: ChatMessage[]
}

export interface ChatHistoryResponse {
  items: ChatMessage[]
}
