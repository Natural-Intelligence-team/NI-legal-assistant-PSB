import {
  useState,
  useRef,
  useEffect,
  useCallback,
  type FormEvent,
  type KeyboardEvent,
  type ChangeEvent,
} from 'react';
import {
  Send,
  RotateCcw,
  FileText,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  CheckCircle2,
  Info,
  X,
  ChevronRight,
  Loader2,
  ArrowDown,
} from 'lucide-react';
import type { ChatStatus, Citation } from '../api/types';
import { mockChatRequest } from '../api/mocks';
import { useMockApi } from '../api/client';
import type { useLegalChat } from '../hooks/useLegalChat';
import { DocumentViewer } from './DocumentViewer';
import { PsbLogo } from './PsbLogo';

type ChatController = ReturnType<typeof useLegalChat>;

interface ChatWindowProps {
  chat: ChatController;
  mode: 'full' | 'widget';
  onCloseWidget?: () => void;
}

const STATUS_META: Record<
  ChatStatus,
  { label: string; className: string; Icon: typeof CheckCircle2 }
> = {
  answered: {
    label: 'Подтверждено базой',
    className: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    Icon: CheckCircle2,
  },
  partial: {
    label: 'Частичный ответ',
    className: 'bg-amber-50 text-amber-800 border-amber-200',
    Icon: Info,
  },
  clarify: {
    label: 'Нужно уточнение',
    className: 'bg-[#F0F0F7] text-[#3E3E59] border-[#8D8DA6]/40',
    Icon: HelpCircle,
  },
  insufficient: {
    label: 'Недостаточно данных',
    className: 'bg-orange-50 text-orange-800 border-orange-200',
    Icon: AlertTriangle,
  },
  refused: {
    label: 'Вне компетенции',
    className: 'bg-[#F0F0F7] text-[#5C5C73] border-[#8D8DA6]/40',
    Icon: ShieldAlert,
  },
};

const exampleQuestion = useMockApi
  ? mockChatRequest.question
  : 'Какая арендная плата по договору с ООО «Северный Склад» и до какого числа её нужно вносить?';

export function ChatWindow({ chat, mode, onCloseWidget }: ChatWindowProps) {
  const [input, setInput] = useState('');
  const [showScrollDown, setShowScrollDown] = useState(false);

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const isWidget = mode === 'widget';

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    bottomRef.current?.scrollIntoView({ behavior });
  }, []);

  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollDown(distanceFromBottom > 120);
  }, []);

  useEffect(() => {
    scrollToBottom('smooth');
  }, [chat.messages, chat.isLoading, chat.error, scrollToBottom]);

  const submitCurrentInput = () => {
    if (!input.trim() || chat.isLoading) return;
    chat.sendMessage(input);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submitCurrentInput();
  };

  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 144)}px`;
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitCurrentInput();
    }
  };

  return (
    <div
      className={
        isWidget
          ? 'psb-card-shadow animate-widget-in relative flex h-[min(580px,calc(100dvh-6rem))] w-[min(400px,calc(100vw-2rem))] flex-col overflow-hidden rounded-xl border border-[#8D8DA6]/30 bg-white text-left'
          : 'psb-card-shadow relative flex h-full w-full flex-col overflow-hidden bg-white text-left md:rounded-xl md:border md:border-[#8D8DA6]/25 lg:flex-row'
      }
    >
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 select-none items-center justify-between gap-2 bg-[#2E2E4D] px-4 text-white">
          <div className="flex min-w-0 items-center gap-3">
            <PsbLogo variant="light" className="h-5 w-auto shrink-0" />
            <div className="h-4 w-px shrink-0 bg-white/20" />
            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold leading-tight text-white">
                Юридический ассистент
              </h2>
              <p className="truncate text-[11px] text-[#C7C7D9]">
                Проверка договоров и регламентов
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={chat.resetChat}
              title="Новый диалог"
              className="rounded-[4px] p-1.5 text-[#C7C7D9] transition hover:bg-white/10 hover:text-white active:scale-95"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
            {isWidget && onCloseWidget && (
              <button
                type="button"
                onClick={onCloseWidget}
                title="Свернуть"
                className="rounded-[4px] p-1.5 text-[#C7C7D9] transition hover:bg-white/10 hover:text-white active:scale-95"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </header>

        <div className="relative min-h-0 flex-1">
          <div
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className="psb-scrollbar h-full overflow-y-auto bg-[#F8F8FC] p-4"
          >
            <div className={`space-y-4 ${isWidget ? '' : 'mx-auto w-full max-w-4xl'}`}>
              {chat.messages.map((msg) => {
                const isUser = msg.role === 'user';
                const statusMeta = !isUser && msg.status ? STATUS_META[msg.status] : null;

                return (
                  <div
                    key={msg.id}
                    className={`animate-msg-in flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                  >
                    <div
                      className={`max-w-[88%] rounded-xl px-4 py-3 text-left text-[14px] leading-[1.45] ${
                        isUser
                          ? 'rounded-br-[4px] bg-[#3E3E59] font-medium text-[#F8F8FC]'
                          : 'psb-card-shadow rounded-bl-[4px] border border-[#E6E6EF] bg-white text-[#3E3E59]'
                      }`}
                    >
                      {statusMeta && (
                        <div
                          className={`mb-2 inline-flex select-none items-center gap-1.5 rounded-[4px] border px-2 py-0.5 text-[11px] font-semibold ${statusMeta.className}`}
                        >
                          <statusMeta.Icon className="h-3 w-3 shrink-0" />
                          <span>{statusMeta.label}</span>
                        </div>
                      )}

                      <p className="select-text break-words whitespace-pre-line">{msg.content}</p>

                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3 select-none space-y-1.5 border-t border-[#F0F0F7] pt-2.5">
                          <div className="text-[11px] font-semibold tracking-wider text-[#8D8DA6] uppercase">
                            Источники:
                          </div>
                          {msg.citations.map((cit: Citation) => {
                            const isSelected = chat.activeCitation === cit;
                            return (
                              <button
                                type="button"
                                key={`${cit.fragment_id}:${cit.quote}`}
                                onClick={() => chat.openCitation(cit)}
                                className={`flex w-full items-center justify-between gap-2 rounded-lg border px-2.5 py-2 text-left text-xs transition active:scale-[0.99] ${
                                  isSelected
                                    ? 'border-[#E86630] bg-[#E86630]/5 text-[#3E3E59]'
                                    : 'border-[#E6E6EF] bg-[#F8F8FC] text-[#3E3E59] hover:border-[#E86630]/60 hover:bg-white'
                                }`}
                              >
                                <span className="flex min-w-0 items-center gap-2">
                                  <FileText className="h-3.5 w-3.5 shrink-0 text-[#E86630]" />
                                  <span className="truncate font-medium">{cit.title}</span>
                                </span>
                                <span className="flex shrink-0 items-center gap-1 text-[11px] text-[#5C5C73]">
                                  {cit.section && <span>п. {cit.section}</span>}
                                  <ChevronRight className="h-3.5 w-3.5 text-[#8D8DA6]" />
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                    <time
                      dateTime={msg.isoTimestamp}
                      title={msg.fullTimestamp}
                      className="mt-1 cursor-default select-none px-1 text-[11px] text-[#8D8DA6]"
                    >
                      {msg.timestamp}
                    </time>
                  </div>
                );
              })}

              {chat.messages.length === 1 && !chat.isLoading && (
                <div className="animate-msg-in flex flex-wrap gap-2 pt-1 select-none">
                  <button
                    type="button"
                    onClick={() => chat.sendMessage(exampleQuestion)}
                    className="inline-flex items-center gap-2 rounded-lg border border-[#E6E6EF] bg-white px-3 py-2 text-left text-xs text-[#3E3E59] transition hover:border-[#E86630] active:scale-[0.98]"
                  >
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#ED885E]" />
                    <span>{exampleQuestion}</span>
                  </button>
                </div>
              )}

              {chat.isLoading && (
                <div className="animate-msg-in flex select-none items-start">
                  <div className="psb-card-shadow flex items-center gap-2.5 rounded-xl rounded-bl-[4px] border border-[#E6E6EF] bg-white px-4 py-3 text-xs font-medium text-[#5C5C73]">
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-[#E86630]" />
                    <span>Поиск по базе и проверка редакций...</span>
                  </div>
                </div>
              )}

              {chat.error && (
                <div className="animate-msg-in flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-left text-xs text-red-800">
                  <span>{chat.error}</span>
                  <button
                    type="button"
                    onClick={chat.retryLast}
                    className="shrink-0 select-none rounded-[4px] bg-[#E86630] px-3 py-1.5 text-[11px] font-semibold tracking-wider text-white uppercase transition hover:bg-[#d15622] active:scale-95"
                  >
                    Повторить
                  </button>
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          </div>

          {showScrollDown && (
            <button
              type="button"
              onClick={() => scrollToBottom('smooth')}
              title="Вниз"
              aria-label="Прокрутить вниз"
              className="psb-card-shadow animate-msg-in absolute right-4 bottom-3 z-10 flex h-8 w-8 select-none items-center justify-center rounded-full border border-[#DCDCE8] bg-white text-[#3E3E59] transition hover:border-[#E86630] hover:text-[#E86630] active:scale-95"
            >
              <ArrowDown className="h-4 w-4" />
            </button>
          )}
        </div>

        <form
          onSubmit={handleSubmit}
          className="shrink-0 border-t border-[#E6E6EF] bg-white p-2.5 sm:p-3"
        >
          <div className={`flex items-end gap-2 ${isWidget ? '' : 'mx-auto w-full max-w-4xl'}`}>
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              enterKeyHint="send"
              placeholder="Введите юридический вопрос..."
              className="psb-scrollbar min-h-10 max-h-36 min-w-0 flex-1 resize-none rounded-[4px] border border-[#8D8DA6]/40 bg-[#F8F8FC] px-3.5 py-[9px] text-sm leading-5 text-[#3E3E59] placeholder:text-[#8D8DA6] transition focus:border-[#E86630] focus:bg-white focus:outline-none"
            />
            <button
              type="submit"
              disabled={!input.trim() || chat.isLoading}
              className="flex h-10 w-10 shrink-0 select-none items-center justify-center rounded-[4px] bg-[#E86630] text-white transition hover:bg-[#d15622] active:scale-95 disabled:opacity-40"
              aria-label="Отправить"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </form>
      </div>

      {chat.activeCitation && (
        <DocumentViewer
          citation={chat.activeCitation}
          document={chat.activeDocument}
          isLoading={chat.isDocLoading}
          error={chat.docError}
          onClose={chat.closeDocument}
          compact={isWidget}
        />
      )}
    </div>
  );
}
