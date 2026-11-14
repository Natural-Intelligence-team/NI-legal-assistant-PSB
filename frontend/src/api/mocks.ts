import type {
  ApiErrorResponse,
  ChatRequest,
  ChatResponse,
  ChatStatus,
  Citation,
  DocumentResponse,
} from './types';

export type MockScenario = ChatStatus | 'error';

const paymentClause = 'Оплата производится в течение 30 календарных дней после подписания УПД.';

export const mockDocument: DocumentResponse = {
  source_id: 'contract-demo-v1',
  title: 'Договор поставки № Д-01',
  text: `Договор поставки № Д-01\n\n4. Порядок расчётов\n4.2. ${paymentClause}`,
};

const paymentCitation: Citation = {
  source_id: mockDocument.source_id,
  fragment_id: 'contract-demo-v1-4-2',
  title: mockDocument.title,
  section: '4.2',
  quote: paymentClause,
};

export const mockChatRequest: ChatRequest = {
  question: 'Какой срок оплаты по договору Д-01?',
  history: [],
};

export const mockChatResponses: Record<ChatStatus, ChatResponse> = {
  answered: {
    status: 'answered',
    answer: 'Оплату нужно произвести в течение 30 календарных дней после подписания УПД.',
    citations: [paymentCitation],
  },
  partial: {
    status: 'partial',
    answer:
      'Пункт 4.2 устанавливает срок оплаты. В предоставленном документе нет условий о неустойке.',
    citations: [paymentCitation],
  },
  clarify: {
    status: 'clarify',
    answer: 'На какую дату нужно проверить редакцию договора?',
    citations: [],
  },
  insufficient: {
    status: 'insufficient',
    answer: 'В базе нет нужной редакции договора, чтобы подтвердить срок оплаты на эту дату.',
    citations: [],
  },
  refused: {
    status: 'refused',
    answer:
      'Я отвечаю на вопросы по документам из базы. Укажите договор или правило, которое нужно проверить.',
    citations: [],
  },
};

export const mockApiErrors = {
  emptyQuestion: { error: 'Введите вопрос' },
  unavailable: { error: 'Модель недоступна' },
  documentNotFound: { error: 'Документ не найден' },
} satisfies Record<string, ApiErrorResponse>;

export async function mockSendQuestion(
  request: ChatRequest,
  scenario: MockScenario = 'answered'
): Promise<ChatResponse> {
  await new Promise<void>((resolve) => setTimeout(resolve, 350));

  if (!request.question.trim()) {
    throw new Error(mockApiErrors.emptyQuestion.error);
  }
  if (scenario === 'error') {
    throw new Error(mockApiErrors.unavailable.error);
  }
  return structuredClone(mockChatResponses[scenario]);
}

export async function mockGetDocument(sourceId: string): Promise<DocumentResponse> {
  if (sourceId !== mockDocument.source_id) {
    throw new Error(mockApiErrors.documentNotFound.error);
  }
  return { ...mockDocument };
}
