import type { ApiErrorResponse, ChatRequest, ChatResponse, DocumentResponse } from './types';
import { mockGetDocument, mockSendQuestion, type MockScenario } from './mocks';

const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '');

export async function sendChatQuestion(
  request: ChatRequest,
  scenario: MockScenario = 'answered'
): Promise<ChatResponse> {
  if (!API_URL) {
    return mockSendQuestion(request, scenario);
  }

  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as ApiErrorResponse | null;
    throw new Error(err?.error || `Ошибка сервера (${res.status})`);
  }

  return (await res.json()) as ChatResponse;
}

export async function fetchDocumentById(sourceId: string): Promise<DocumentResponse> {
  if (!API_URL) {
    return mockGetDocument(sourceId);
  }

  const res = await fetch(`${API_URL}/documents/${encodeURIComponent(sourceId)}`);

  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as ApiErrorResponse | null;
    throw new Error(err?.error);
  }

  return (await res.json()) as DocumentResponse;
}
