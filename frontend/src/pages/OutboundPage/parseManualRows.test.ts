import { describe, it, expect } from 'vitest'
import { parseManualRows } from './parseManualRows'

describe('parseManualRows — SPEC-ORDER-015 REQ-OUTBOUND-016', () => {
  it('parses tab-separated name/sku/total lines into row objects', () => {
    expect(parseManualRows('#37349\tISBN001\t4')).toEqual([
      { name: '#37349', sku: 'ISBN001', total: 4 },
    ])
  })

  it('parses multiple lines at once (bulk entry)', () => {
    expect(parseManualRows('#37349\tISBN001\t4\n#37350\tISBN002\t1')).toEqual([
      { name: '#37349', sku: 'ISBN001', total: 4 },
      { name: '#37350', sku: 'ISBN002', total: 1 },
    ])
  })

  it('handles CRLF line endings from a Windows spreadsheet paste', () => {
    expect(parseManualRows('#37349\tISBN001\t4\r\n#37350\tISBN002\t1')).toEqual([
      { name: '#37349', sku: 'ISBN001', total: 4 },
      { name: '#37350', sku: 'ISBN002', total: 1 },
    ])
  })

  it('ignores blank lines and trims surrounding whitespace', () => {
    expect(parseManualRows('\n  #37349 \t ISBN001 \t 4 \n\n')).toEqual([
      { name: '#37349', sku: 'ISBN001', total: 4 },
    ])
  })

  it('accepts comma-separated lines as well as tab-separated', () => {
    expect(parseManualRows('#37349,ISBN001,4')).toEqual([
      { name: '#37349', sku: 'ISBN001', total: 4 },
    ])
  })

  it('ignores columns past the third, so a wider paste still parses', () => {
    expect(parseManualRows('#37349\tISBN001\t4\t무시되는열')).toEqual([
      { name: '#37349', sku: 'ISBN001', total: 4 },
    ])
  })

  it('skips lines that do not have all three columns', () => {
    expect(parseManualRows('#37349\tISBN001\n#37350\tISBN002\t2')).toEqual([
      { name: '#37350', sku: 'ISBN002', total: 2 },
    ])
  })

  it('skips a line whose name or sku column is empty', () => {
    expect(parseManualRows('\tISBN001\t4\n#37350\t\t2')).toEqual([])
  })

  it('treats a non-numeric total as 0 rather than NaN', () => {
    expect(parseManualRows('#37349\tISBN001\tabc')).toEqual([
      { name: '#37349', sku: 'ISBN001', total: 0 },
    ])
  })

  it('returns an empty list for empty or whitespace-only input', () => {
    expect(parseManualRows('')).toEqual([])
    expect(parseManualRows('   \n\n  ')).toEqual([])
  })
})
