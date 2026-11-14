import { useState } from 'react';
import { useLegalChat, type DevScenario } from './hooks/useLegalChat';
import { ChatWindow } from './components/ChatWindow';
import { AssistantWidget } from './components/AssistantWidget';
import { PortalSkeleton } from './components/PortalSkeleton';

const SCENARIOS: DevScenario[] = [
  'answered',
  'partial',
  'clarify',
  'insufficient',
  'refused',
  'error',
  'loading',
];

export function App() {
  const [viewMode, setViewMode] = useState<'full' | 'widget'>('full');
  const chat = useLegalChat();

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-[#F8F8FC] text-[#3E3E59]">
      <div className="z-50 flex h-9 shrink-0 select-none items-center justify-end gap-2 border-b border-[#E6E6EF] bg-white px-3 text-xs text-[#5C5C73]">
        <select
          aria-label="Сценарий мока"
          value={chat.scenario}
          onChange={(e) => chat.setScenario(e.target.value as DevScenario)}
          className="h-6 rounded-[4px] border border-[#DCDCE8] bg-[#F8F8FC] px-2 font-mono text-[11px] text-[#3E3E59] focus:border-[#E86630] focus:outline-none"
        >
          {SCENARIOS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <div className="inline-flex h-6 rounded-[4px] border border-[#DCDCE8] bg-[#F8F8FC] p-0.5 text-[11px]">
          <button
            type="button"
            onClick={() => setViewMode('full')}
            className={`rounded-[3px] px-2.5 leading-none transition ${
              viewMode === 'full'
                ? 'bg-[#3E3E59] font-medium text-white'
                : 'text-[#5C5C73] hover:text-[#3E3E59]'
            }`}
          >
            App
          </button>
          <button
            type="button"
            onClick={() => setViewMode('widget')}
            className={`rounded-[3px] px-2.5 leading-none transition ${
              viewMode === 'widget'
                ? 'bg-[#3E3E59] font-medium text-white'
                : 'text-[#5C5C73] hover:text-[#3E3E59]'
            }`}
          >
            Widget
          </button>
        </div>
      </div>

      {viewMode === 'full' ? (
        <main className="flex min-h-0 w-full flex-1 p-0 md:p-3">
          <ChatWindow chat={chat} mode="full" />
        </main>
      ) : (
        <div className="relative min-h-0 flex-1 overflow-y-auto">
          <PortalSkeleton />
          <AssistantWidget externalChat={chat} />
        </div>
      )}
    </div>
  );
}

export default App;
