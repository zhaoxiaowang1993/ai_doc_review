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

export function DocumentIRViewer(props: { docId: string, issues?: Issue[], selectedIssue?: Issue }) {
  const { docId, issues, selectedIssue } = props
  const [ir, setIr] = useState<DocumentIR>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>()

  const anchor = useMemo(() => {
    const loc = selectedIssue?.location
    if (!loc || typeof loc !== 'object') return null
    if ((loc as any).type !== 'ir_anchor') return null
    return {
      nodeId: (loc as any).node_id as string | undefined,
      start: (loc as any).start_offset as number | undefined,
      end: (loc as any).end_offset as number | undefined,
    }
  }, [selectedIssue])

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
  }, [docId])

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
