import { useEffect, useRef } from 'react';
import { FileText, X, AlertCircle, Loader2 } from 'lucide-react';
import type { Citation, DocumentResponse } from '../api/types';

interface DocumentViewerProps {
  citation: Citation;
  document: DocumentResponse | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
  compact?: boolean;
}

export function DocumentViewer({
  citation,
  document,
  isLoading,
  error,
  onClose,
  compact = false,
}: DocumentViewerProps) {
  const markRef = useRef<HTMLElement | null>(null);

  const matchIndex = document && citation.quote ? document.text.indexOf(citation.quote) : -1;
  const hasExactMatch = matchIndex !== -1;

  useEffect(() => {
    if (document && hasExactMatch) {
      markRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  }, [document, hasExactMatch, citation.fragment_id, citation.quote]);

  return (
    <aside
      className={
        compact
          ? 'animate-panel-in absolute inset-0 z-20 flex flex-col bg-white text-left'
          : 'animate-panel-in absolute inset-0 z-20 flex flex-col bg-white text-left lg:static lg:z-auto lg:h-full lg:w-[440px] lg:shrink-0 lg:border-l lg:border-[#E6E6EF]'
      }
    >
      <div className="flex h-14 shrink-0 select-none items-center justify-between gap-3 border-b border-[#E6E6EF] bg-[#F8F8FC] px-4">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-[10px] font-semibold tracking-wider text-[#585892] uppercase">
            <FileText className="h-3 w-3 shrink-0 text-[#E86630]" />
            <span>Источник {citation.section ? `· п. ${citation.section}` : ''}</span>
          </div>
          <h3
            className="truncate text-sm font-semibold leading-tight text-[#3E3E59]"
            title={citation.title}
          >
            {citation.title}
          </h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-[4px] p-1.5 text-[#8D8DA6] transition hover:bg-[#F0F0F7] hover:text-[#3E3E59] active:scale-95"
          aria-label="Закрыть документ"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="psb-scrollbar min-h-0 flex-1 overflow-y-auto p-4">
        {isLoading && (
          <div className="flex select-none items-center gap-2.5 text-sm text-[#5C5C73]">
            <Loader2 className="h-4 w-4 animate-spin text-[#E86630]" />
            <span>Загрузка текста документа...</span>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-800">
            <div className="flex select-none items-center gap-1.5 font-semibold">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>Не удалось открыть полный текст</span>
            </div>
            <p className="mt-1 text-xs text-red-700">{error}</p>
            <div className="mt-3 rounded-lg border border-red-200/70 bg-white p-2.5 text-[#3E3E59]">
              <div className="select-none text-[11px] font-medium text-[#8D8DA6]">Цитата:</div>
              <p className="mt-1 select-text text-xs italic">«{citation.quote}»</p>
            </div>
          </div>
        )}

        {document && (
          <div className="space-y-3">
            {!hasExactMatch && citation.quote && (
              <div className="rounded-lg border border-[#ED885E]/40 bg-[#ED885E]/10 p-3 text-xs leading-relaxed text-[#3E3E59]">
                <span className="select-none font-semibold text-[#E86630]">Цитата: </span>
                <span className="select-text">«{citation.quote}»</span>
              </div>
            )}

            <div className="rounded-xl border border-[#E6E6EF] bg-[#F8F8FC] p-4">
              {hasExactMatch ? (
                <p className="select-text whitespace-pre-line text-sm leading-relaxed text-[#3E3E59]">
                  {document.text.slice(0, matchIndex)}
                  <mark
                    ref={markRef}
                    className="rounded-[4px] bg-[#ED885E]/30 px-1 py-0.5 font-medium text-[#2E2E4D]"
                  >
                    {document.text.slice(matchIndex, matchIndex + citation.quote.length)}
                  </mark>
                  {document.text.slice(matchIndex + citation.quote.length)}
                </p>
              ) : (
                <p className="select-text whitespace-pre-line text-sm leading-relaxed text-[#3E3E59]">
                  {document.text}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
