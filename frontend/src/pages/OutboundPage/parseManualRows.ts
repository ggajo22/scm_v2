import type { OutboundRowInput } from '@/services/outboundApi'

// SPEC-ORDER-015 REQ-OUTBOUND-016: bulk manual entry is a paste target —
// users copy the Name / Lineitem sku / Total columns straight out of a
// spreadsheet, which arrives tab-separated. Commas are accepted too so a
// hand-typed or CSV-ish line works without a second UI. Columns past the
// third are ignored, so a wider paste still parses.
//
// Lives in its own module rather than OutboundPage/index.tsx so that file
// only exports components (react-refresh/only-export-components).
export function parseManualRows(text: string): OutboundRowInput[] {
  const rows: OutboundRowInput[] = []

  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue

    const columns = line.split(/[\t,]/).map((column) => column.trim())
    if (columns.length < 3) continue

    const [name, sku, total] = columns
    if (!name || !sku) continue

    // A non-numeric total becomes 0 rather than NaN — the backend judges a
    // 0-quantity row harmlessly instead of receiving null and 400-ing.
    const parsedTotal = Number.parseInt(total, 10)
    rows.push({ name, sku, total: Number.isNaN(parsedTotal) ? 0 : parsedTotal })
  }

  return rows
}
