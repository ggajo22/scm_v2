import { useState } from 'react'
import { cn } from '@/lib/utils'
import { SearchTab } from './tabs/SearchTab'
import { SummaryTab } from './tabs/SummaryTab'

type TabValue = 'search' | 'summary'

interface TabDef {
  value: TabValue
  label: string
}

const TABS: TabDef[] = [
  { value: 'search', label: '주문 검색' },
  { value: 'summary', label: '렉번호 요약' },
]

// SPEC-ORDER-014: tab shell for /rack-number — Tab1 "주문 검색" (SearchTab,
// SPEC-ORDER-013 flow, unchanged) + Tab2 "렉번호 요약" (SummaryTab, new
// read-only cross-order aggregate). Same state-based tab-switcher pattern as
// PurchaseOrders/index.tsx (role="tablist"/role="tabpanel", no
// @radix-ui/react-tabs dependency).
// @MX:ANCHOR: [AUTO] RackNumberPage — entry point for the /rack-number route
// @MX:REASON: Lazy-loaded from router via named export destructure
// (`const { RackNumberPage } = await import('@/pages/RackNumberPage')`) —
// this export name and the folder+index.tsx module resolution must not
// change without also updating router/index.tsx.
// @MX:NOTE: [AUTO] Default active tab MUST stay 'search' — SPEC-ORDER-013's
// existing SearchTab test suite assumes Tab1 content renders with no tab
// click required (REQ-RACKSUM-009b).
export function RackNumberPage() {
  const [activeTab, setActiveTab] = useState<TabValue>('search')

  const renderTab = () => {
    switch (activeTab) {
      case 'search':
        return <SearchTab />
      case 'summary':
        return <SummaryTab />
    }
  }

  return (
    <div className="space-y-4">
      <div role="tablist" aria-label="렉번호 관리 탭" className="border-b px-6 pt-4">
        <div className="flex gap-0 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.value}
              role="tab"
              aria-selected={activeTab === tab.value}
              aria-controls={`tabpanel-${tab.value}`}
              id={`tab-${tab.value}`}
              type="button"
              onClick={() => setActiveTab(tab.value)}
              className={cn(
                'px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
                activeTab === tab.value
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/40'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div role="tabpanel" id={`tabpanel-${activeTab}`} aria-labelledby={`tab-${activeTab}`}>
        {renderTab()}
      </div>
    </div>
  )
}
