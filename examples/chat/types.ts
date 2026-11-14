export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  question: string;
  history: ChatMessage[];
}

export type ChatStatus = "answered" | "partial" | "clarify" | "insufficient" | "refused";

export interface Citation {
  source_id: string;
  fragment_id: string;
  title: string;
  section: string | null;
  quote: string;
}

export interface ChatResponse {
  status: ChatStatus;
  answer: string;
  citations: Citation[];
}

export interface DocumentResponse {
  source_id: string;
  title: string;
  text: string;
}

export interface ApiErrorResponse {
  error: string;
}
