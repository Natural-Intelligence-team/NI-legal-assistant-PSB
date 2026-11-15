import { useState } from 'react';
import { MessageSquareText } from 'lucide-react';
import { useLegalChat } from '../hooks/useLegalChat';
import { ChatWindow } from './ChatWindow';

type ChatController = ReturnType<typeof useLegalChat>;

interface AssistantWidgetProps {
  externalChat?: ChatController;
}

function WidgetView({ chat }: { chat: ChatController }) {
  const [isOpen, setIsOpen] = useState(true);

  if (!isOpen) {
    return (
      <div className="fixed right-4 bottom-4 z-40 sm:right-5 sm:bottom-5">
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="psb-card-shadow animate-widget-in flex select-none items-center gap-2.5 rounded-full bg-[#2E2E4D] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#3E3E59] active:scale-95"
        >
          <MessageSquareText className="h-5 w-5 text-[#E86630]" />
          <span>Юридический ассистент</span>
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        top: 'calc(var(--app-offset-top, 0px) + 2.25rem)',
        height: 'calc(var(--app-height, 100dvh) - 2.25rem)',
      }}
      className="fixed inset-x-0 z-40 flex flex-col sm:inset-auto sm:top-auto sm:right-5 sm:bottom-5 sm:!h-auto sm:items-end"
    >
      <ChatWindow chat={chat} mode="widget" onCloseWidget={() => setIsOpen(false)} />
    </div>
  );
}

function StandaloneWidget() {
  const chat = useLegalChat();
  return <WidgetView chat={chat} />;
}

export function AssistantWidget({ externalChat }: AssistantWidgetProps) {
  return externalChat ? <WidgetView chat={externalChat} /> : <StandaloneWidget />;
}
