export interface IRTextRun {
  id: string
  text: string
}

export interface IRParagraph {
  type: 'paragraph'
  id: string
  runs: IRTextRun[]
}

export interface IRTableCell {
  id: string
  blocks: IRParagraph[]
}

export interface IRTableRow {
  id: string
  cells: IRTableCell[]
}

export interface IRTable {
  type: 'table'
  id: string
  rows: IRTableRow[]
}

export type IRBlock = IRParagraph | IRTable

export interface DocumentIR {
  version: string
  blocks: IRBlock[]
}

