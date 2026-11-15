import { FileText, Search } from 'lucide-react';
import { PsbLogo } from './PsbLogo';

export function PortalSkeleton() {
  return (
    <div className="min-h-full select-none bg-[#F8F8FC] text-left">
      <div className="psb-banner-gradient text-white">
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-8">
          <div className="hidden items-center justify-between border-b border-white/20 pb-3 text-xs text-white/70 md:flex">
            <div className="flex items-center gap-6">
              <span className="border-b border-[#E86630] pb-1 font-semibold tracking-wider text-white uppercase">
                Корпоративный портал
              </span>
              <span>Нормативная база</span>
              <span>Регламенты</span>
              <span>Договорная работа</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2.5 w-24 rounded-full bg-white/20" />
              <div className="h-2.5 w-16 rounded-full bg-white/20" />
            </div>
          </div>

          <div className="flex items-center justify-between pt-3">
            <div className="flex items-center gap-8">
              <PsbLogo variant="light" className="h-6 w-auto" />
              <div className="hidden items-center gap-5 lg:flex">
                <div className="h-3 w-20 rounded-full bg-white/25" />
                <div className="h-3 w-28 rounded-full bg-white/25" />
                <div className="h-3 w-24 rounded-full bg-white/25" />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-[4px] border border-white/25">
                <Search className="h-4 w-4 text-white/80" />
              </div>
              <div className="hidden rounded-[4px] border border-white/30 px-4 py-2 text-[11px] font-semibold tracking-wider uppercase sm:block">
                СЭД ПСБ
              </div>
            </div>
          </div>

          <div className="py-10 sm:py-12">
            <div className="mb-3 flex items-center gap-2 text-xs text-[#C7C7D9]">
              <span>Главная</span>
              <span>/</span>
              <span>Правовой департамент</span>
              <span>/</span>
              <span className="text-white">Документация и регламенты</span>
            </div>
            <h1 className="text-2xl font-semibold sm:text-4xl">
              Документация и внутренние регламенты
            </h1>
            <p className="mt-2 max-w-xl text-sm text-[#C7C7D9]">
              Единый реестр типовых договоров, дополнительных соглашений и локальных нормативных
              актов банка.
            </p>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-6xl space-y-5 px-4 py-8 sm:px-8">
        <div className="psb-card-shadow max-w-2xl rounded-xl border border-[#E86630]/30 bg-white p-6">
          <div className="text-[11px] font-semibold tracking-wider text-[#E86630] uppercase">
            Режим встраиваемого виджета
          </div>
          <h2 className="mt-1.5 text-lg font-semibold text-[#3E3E59]">
            Интеграция в портал или карточку договора СЭД
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-[#5C5C73]">
            Так будет выглядеть интеграция компонента{' '}
            <code className="rounded bg-[#F0F0F7] px-1.5 py-0.5 font-mono text-xs text-[#3E3E59]">
              &lt;AssistantWidget /&gt;
            </code>{' '}
            поверх рабочих страниц банка. Сотрудник может уточнить условия договора, проверить
            редакцию на дату и открыть подтверждающий пункт документа, не покидая текущую вкладку.
          </p>
        </div>

        <div className="psb-card-shadow max-w-2xl space-y-3 rounded-xl border border-[#E6E6EF] bg-white p-6">
          <div className="h-5 w-56 rounded-md bg-[#E6E6EF]" />
          {[1, 2, 3].map((item) => (
            <div
              key={item}
              className="flex items-center justify-between rounded-lg border border-[#F0F0F7] bg-[#F8F8FC] px-4 py-3.5"
            >
              <div className="flex items-center gap-3">
                <FileText className="h-4 w-4 text-[#8D8DA6]" />
                <div className="space-y-1.5">
                  <div className="h-3 w-48 rounded bg-[#DCDCE8] sm:w-72" />
                  <div className="h-2.5 w-32 rounded bg-[#E9E9F2]" />
                </div>
              </div>
              <div className="h-3 w-12 rounded bg-[#E6E6EF]" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
