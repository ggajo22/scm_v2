import { useState } from 'react'
import { cn } from '@/lib/utils'
import { UnorderedItemsTab } from './tabs/UnorderedItemsTab'
import { VendorFileUploadTab } from './tabs/VendorFileUploadTab'
import { ConfirmOrderTab } from './tabs/ConfirmOrderTab'
import { PurchaseOrderHistoryTab } from './tabs/PurchaseOrderHistoryTab'
import { VendorRulesTab } from './tabs/VendorRulesTab'

type TabValue =
  | 'unordered'
  | 'upload'
  | 'confirm'
  | 'history'
  | 'rules'

interface TabDef {
  value: TabValue
  label: string
}

const TABS: TabDef[] = [
  { value: 'unordered', label: '미발주 현황' },
  { value: 'upload', label: '업체 자료 업로드' },
  { value: 'confirm', label: '발주 확정' },
  { value: 'history', label: '발주 이력' },
  { value: 'rules', label: '발주처 규칙 설정' },
]

// @MX:ANCHOR: [AUTO] Root component for purchase order management — entry point for all sub-tabs
// @MX:REASON: Fan-in >= 3 — router, Sidebar navigation, and all child tabs are rooted here

export function PurchaseOrdersPage() {
  const [activeTab, setActiveTab] = useState<TabValue>('unordered')

  const renderTab = () => {
    switch (activeTab) {
      case 'unordered':
        return <UnorderedItemsTab />
      case 'upload':
        return <VendorFileUploadTab />
      case 'confirm':
        return <ConfirmOrderTab />
      case 'history':
        return <PurchaseOrderHistoryTab />
      case 'rules':
        return <VendorRulesTab />
    }
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">발주 관리</h1>

      {/* State-based tab navigation (no @radix-ui/react-tabs dependency) */}
      <div role="tablist" aria-label="발주 관리 탭" className="border-b">
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

      {/* Tab panel */}
      <div
        role="tabpanel"
        id={`tabpanel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
      >
        {renderTab()}
      </div>
    </div>
  )
}
