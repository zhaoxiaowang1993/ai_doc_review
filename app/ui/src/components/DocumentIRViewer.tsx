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

function HighlightedText(props: { text: string, start?: number, end?: number }) {
  const { text, start, end } = props
  if (typeof start !== 'number' || typeof end !== 'number' || start < 0 || end <= start || start >= text.length) {
    return <>{text}</>
  }
  const a = text.slice(0, start)
  const b = text.slice(start, Math.min(end, text.length))
  const c = text.slice(Math.min(end, text.length))
  return (
    <>
      {a}
      <mark style={{ backgroundColor: 'rgba(255, 64, 64, 0.35)' }}>{b}</mark>
      {c}
    </>
  )
}

export function DocumentIRViewer(props: { docId: string, selectedIssue?: Issue }) {
  const { docId, selectedIssue } = props
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
          const isHit = anchor?.nodeId === b.id
          return (
            <p key={b.id} data-ir-node-id={b.id} style={{ margin: '8px 0', lineHeight: 1.6 }}>
              <HighlightedText text={text} start={isHit ? anchor?.start : undefined} end={isHit ? anchor?.end : undefined} />
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
                          const isHit = anchor?.nodeId === p.id
                          return (
                            <p key={p.id} data-ir-node-id={p.id} style={{ margin: 0, lineHeight: 1.6 }}>
                              <HighlightedText text={text} start={isHit ? anchor?.start : undefined} end={isHit ? anchor?.end : undefined} />
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

