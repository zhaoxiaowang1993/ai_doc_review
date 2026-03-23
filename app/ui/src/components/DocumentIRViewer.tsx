import { Alert, Spin } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { getDocumentIR } from '../services/api'
import type { DocumentIR, IRBlock, IRParagraph, IRTable } from '../types/document-ir'
import type { Issue } from '../types/issue'

function isParagraph(b: IRBlock): b is IRParagraph {
  return b.type === 'paragraph'
}

function isTable(b: IRBlock): b is IRTable {
  return b.type === 'table'
}

function paragraphText(p: IRParagraph): string {
  return (p.runs ?? []).map(r => r.text ?? '').join('')
}

type TextRange = { start: number, end: number, tone: 'yellow' | 'red', priority: number }

function findNodeTextById(ir: DocumentIR | undefined, nodeId: string): string | null {
  if (!ir) return null
  for (const block of ir.blocks ?? []) {
    if (isParagraph(block) && block.id === nodeId) {
      return paragraphText(block)
    }
    if (isTable(block)) {
      for (const row of block.rows ?? []) {
        for (const cell of row.cells ?? []) {
          for (const para of cell.blocks ?? []) {
            if (para.id === nodeId) {
              return paragraphText(para)
            }
          }
        }
      }
    }
  }
  return null
}

function pickOccurrence(text: string, keyword: string, preferredStart?: number): number {
  if (!keyword) return -1
  if (typeof preferredStart !== 'number' || preferredStart < 0) return text.indexOf(keyword)
  const all: number[] = []
  let from = 0
  while (from <= text.length - keyword.length) {
    const idx = text.indexOf(keyword, from)
    if (idx === -1) break
    all.push(idx)
    from = idx + 1
  }
  if (!all.length) return -1
  let best = all[0]
  let bestDist = Math.abs(best - preferredStart)
  for (const idx of all.slice(1)) {
    const dist = Math.abs(idx - preferredStart)
    if (dist < bestDist) {
      best = idx
      bestDist = dist
    }
  }
  return best
}

function clampRange(r: { start: number, end: number }, len: number): { start: number, end: number } | null {
  const start = Math.max(0, Math.min(len, r.start))
  const end = Math.max(0, Math.min(len, r.end))
  if (end <= start) return null
  return { start, end }
}

function rangeColor(tone: TextRange['tone']): string {
  if (tone === 'red') return 'rgba(255, 64, 64, 0.35)'
  return 'rgba(255, 255, 0, 0.35)'
}

function renderHighlightedText(text: string, ranges: TextRange[]): JSX.Element {
  if (!text) return <></>
  if (!ranges.length) return <>{text}</>

  const normalized: TextRange[] = []
  for (const r of ranges) {
    const cr = clampRange(r, text.length)
    if (!cr) continue
    normalized.push({ ...r, start: cr.start, end: cr.end })
  }
  if (!normalized.length) return <>{text}</>

  const points = new Set<number>([0, text.length])
  for (const r of normalized) {
    points.add(r.start)
    points.add(r.end)
  }
  const sorted = Array.from(points).sort((a, b) => a - b)

  const out: Array<string | JSX.Element> = []
  for (let i = 0; i < sorted.length - 1; i++) {
    const a = sorted[i]
    const b = sorted[i + 1]
    if (b <= a) continue
    const seg = text.slice(a, b)
    let best: TextRange | undefined
    for (const r of normalized) {
      if (r.start <= a && r.end >= b) {
        if (!best || r.priority > best.priority) best = r
      }
    }
    if (!best) {
      out.push(seg)
    } else {
      out.push(<mark key={`${a}-${b}-${best.tone}`} style={{ backgroundColor: rangeColor(best.tone) }}>{seg}</mark>)
    }
  }

  return <>{out}</>
}

export function DocumentIRViewer(props: { docId: string, issues?: Issue[], selectedIssue?: Issue, reloadToken?: number }) {
  const { docId, issues, selectedIssue, reloadToken } = props
  const [ir, setIr] = useState<DocumentIR>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>()

  const anchor = useMemo(() => {
    const loc = selectedIssue?.location
    if (!loc || typeof loc !== 'object') return null
    if ((loc as any).type !== 'ir_anchor') return null
    const nodeId = (loc as any).node_id as string | undefined
    const start = (loc as any).start_offset as number | undefined
    const end = (loc as any).end_offset as number | undefined
    const status = selectedIssue?.status
    const modifiedFix = selectedIssue?.modified_fields?.suggested_fix?.trim()
    const suggestedFix = selectedIssue?.suggested_fix?.trim()
    const preferredFix = modifiedFix || suggestedFix || ''
    if (status === 'accepted' && nodeId && preferredFix) {
      const nodeText = findNodeTextById(ir, nodeId)
      if (nodeText) {
        const idx = pickOccurrence(nodeText, preferredFix, start)
        if (idx >= 0) {
          return {
            nodeId,
            start: idx,
            end: idx + preferredFix.length,
          }
        }
      }
    }
    if (status === 'accepted' && nodeId) {
      const nodeText = findNodeTextById(ir, nodeId)
      if (nodeText && typeof start === 'number' && typeof end === 'number') {
        const oldSpan = nodeText.slice(Math.max(0, start), Math.max(0, end))
        const issueText = (selectedIssue?.text ?? '').trim()
        if (issueText && oldSpan && oldSpan.includes(issueText)) {
          return { nodeId, start, end }
        }
      }
      return null
    }
    return {
      nodeId,
      start,
      end,
    }
  }, [selectedIssue, ir])

  const rangesByNodeId = useMemo(() => {
    const map = new Map<string, TextRange[]>()
    for (const issue of issues ?? []) {
      const loc = issue.location
      if (!loc || typeof loc !== 'object') continue
      if ((loc as any).type !== 'ir_anchor') continue
      const nodeId = (loc as any).node_id as string | undefined
      const start = (loc as any).start_offset as number | undefined
      const end = (loc as any).end_offset as number | undefined
      if (!nodeId || typeof start !== 'number' || typeof end !== 'number') continue
      const arr = map.get(nodeId) ?? []
      arr.push({ start, end, tone: 'yellow', priority: 0 })
      map.set(nodeId, arr)
    }
    if (anchor?.nodeId && typeof anchor.start === 'number' && typeof anchor.end === 'number') {
      const arr = map.get(anchor.nodeId) ?? []
      arr.push({ start: anchor.start, end: anchor.end, tone: 'red', priority: 1 })
      map.set(anchor.nodeId, arr)
    }
    return map
  }, [anchor, issues])

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (!docId) return
      setLoading(true)
      setError(undefined)
      try {
        const data = await getDocumentIR(docId)
        if (cancelled) return
        setIr(data)
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [docId, reloadToken])

  useEffect(() => {
    if (!anchor?.nodeId) return
    const el = document.querySelector(`[data-ir-node-id="${CSS.escape(anchor.nodeId)}"]`)
    if (!el) return
    ;(el as HTMLElement).scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [anchor?.nodeId])

  if (loading) return <div style={{ padding: 16 }}><Spin /></div>
  if (error) return <div style={{ padding: 16 }}><Alert type="error" message={error} /></div>
  if (!ir) return <div style={{ padding: 16 }}><Alert type="info" message="IR 未加载" /></div>

  return (
    <div style={{ padding: 16, overflow: 'auto', height: '100%' }}>
      {(ir.blocks ?? []).map((b) => {
        if (isParagraph(b)) {
          const text = paragraphText(b)
          return (
            <p key={b.id} data-ir-node-id={b.id} style={{ margin: '8px 0', lineHeight: 1.6 }}>
              {renderHighlightedText(text, rangesByNodeId.get(b.id) ?? [])}
            </p>
          )
        }
        if (isTable(b)) {
          return (
            <table key={b.id} style={{ width: '100%', borderCollapse: 'collapse', margin: '12px 0' }}>
              <tbody>
                {(b.rows ?? []).map((r) => (
                  <tr key={r.id}>
                    {(r.cells ?? []).map((c) => (
                      <td key={c.id} style={{ border: '1px solid #e5e7eb', verticalAlign: 'top', padding: 8 }}>
                        {(c.blocks ?? []).map((p) => {
                          const text = paragraphText(p)
                          return (
                            <p key={p.id} data-ir-node-id={p.id} style={{ margin: 0, lineHeight: 1.6 }}>
                              {renderHighlightedText(text, rangesByNodeId.get(p.id) ?? [])}
                            </p>
                          )
                        })}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )
        }
        return null
      })}
    </div>
  )
}
