import type { ApiErrorResponse, ChatRequest, ChatResponse, DocumentResponse } from './types';
import { mockGetDocument, mockSendQuestion, type MockScenario } from './mocks';

const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '');
export const useMockApi = !API_URL;

export async function sendChatQuestion(
  request: ChatRequest,
  scenario: MockScenario = 'answered',
  signal?: AbortSignal
): Promise<ChatResponse> {
  if (!API_URL) {
    return mockSendQuestion(request, scenario);
  }

  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });

  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as ApiErrorResponse | null;
    throw new Error(err?.error || `Ошибка сервера (${res.status})`);
  }

  return (await res.json()) as ChatResponse;
}

export async function fetchDocumentById(
  sourceId: string,
  signal?: AbortSignal
): Promise<DocumentResponse> {
  if (!API_URL) {
    return mockGetDocument(sourceId);
  }

  const res = await fetch(`${API_URL}/documents/${encodeURIComponent(sourceId)}`, { signal });

  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as ApiErrorResponse | null;
    throw new Error(err?.error || `Не удалось загрузить документ (${res.status})`);
  }

  return (await res.json()) as DocumentResponse;
}
