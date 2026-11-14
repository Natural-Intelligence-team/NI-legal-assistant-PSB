import { useState, useCallback } from 'react';
import type { ChatMessage, ChatStatus, Citation, DocumentResponse } from '../api/types';
import type { MockScenario } from '../api/mocks';
import { fetchDocumentById, sendChatQuestion } from '../api/client';

export type DevScenario = MockScenario | 'loading';

export interface UiMessage extends ChatMessage {
  id: string;
  status?: ChatStatus;
  citations?: Citation[];
  timestamp: string;
  fullTimestamp: string;
  isoTimestamp: string;
}

const createTimestamps = () => {
  const now = new Date();
  return {
    timestamp: now.toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    fullTimestamp: new Intl.DateTimeFormat('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(now),
    isoTimestamp: now.toISOString(),
  };
};

const createWelcomeMessage = (): UiMessage => ({
  id: 'welcome',
  role: 'assistant',
  content:
    'Здравствуйте! Я юридический ИИ-ассистент ПСБ. Задайте вопрос по договорам, регламентам или нормативным актам — я приведу ответ со ссылками на подтверждающие фрагменты.',
  ...createTimestamps(),
});

export function useLegalChat() {
  const [messages, setMessages] = useState<UiMessage[]>(() => [createWelcomeMessage()]);
  const [scenario, setScenario] = useState<DevScenario>('answered');
  const [isRequestLoading, setIsRequestLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [activeDocument, setActiveDocument] = useState<DocumentResponse | null>(null);
  const [isDocLoading, setIsDocLoading] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);

  const isLoading = isRequestLoading || scenario === 'loading';

  const requestAnswer = useCallback(
    async (question: string, currentMessages: UiMessage[]) => {
      setError(null);
      setIsRequestLoading(true);

      const history: ChatMessage[] = currentMessages
        .filter((m) => m.id !== 'welcome')
        .map(({ role, content }) => ({ role, content }));

      try {
        const mockMode: MockScenario = scenario === 'loading' ? 'answered' : scenario;
        const res = await sendChatQuestion({ question, history }, mockMode);

        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: res.answer,
            status: res.status,
            citations: res.citations,
            ...createTimestamps(),
          },
        ]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
      } finally {
        setIsRequestLoading(false);
      }
    },
    [scenario]
  );

  const sendMessage = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed || isLoading) return;

      const userMsg: UiMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: trimmed,
        ...createTimestamps(),
      };

      setMessages((prev) => [...prev, userMsg]);
      await requestAnswer(trimmed, messages);
    },
    [isLoading, messages, requestAnswer]
  );

  const retryLast = useCallback(() => {
    const lastUserIndex = [...messages].reverse().findIndex((m) => m.role === 'user');
    if (lastUserIndex === -1 || isLoading) return;

    const actualIndex = messages.length - 1 - lastUserIndex;
    const lastUserMsg = messages[actualIndex];
    const priorMessages = messages.slice(0, actualIndex);

    requestAnswer(lastUserMsg.content, priorMessages);
  }, [isLoading, messages, requestAnswer]);

  const openCitation = useCallback(async (citation: Citation) => {
    setActiveCitation(citation);
    setActiveDocument(null);
    setDocError(null);
    setIsDocLoading(true);

    try {
      const doc = await fetchDocumentById(citation.source_id);
      setActiveDocument(doc);
    } catch (err) {
      setDocError(err instanceof Error ? err.message : 'Документ не найден');
    } finally {
      setIsDocLoading(false);
    }
  }, []);

  const closeDocument = useCallback(() => {
    setActiveCitation(null);
    setActiveDocument(null);
    setDocError(null);
  }, []);

  const resetChat = useCallback(() => {
    setMessages([createWelcomeMessage()]);
    setError(null);
    setIsRequestLoading(false);
    if (scenario === 'loading') setScenario('answered');
    closeDocument();
  }, [closeDocument, scenario]);

  return {
    messages,
    scenario,
    setScenario,
    isLoading,
    error,
    sendMessage,
    retryLast,
    resetChat,
    activeCitation,
    activeDocument,
    isDocLoading,
    docError,
    openCitation,
    closeDocument,
  };
}
