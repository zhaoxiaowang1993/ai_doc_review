export type IssueLocation =
  | {
      type?: 'pdf_quadpoints'
      source_sentence?: string
      page_num?: number
      bounding_box?: number[]
      anchors?: Array<{
        page_num: number
        bounding_box: number[]
        source_text?: string
      }>
      para_index?: number
    }
  | {
      type: 'ir_anchor'
      source_sentence?: string
      para_index?: number
      node_id?: string
      path?: string[]
      start_offset?: number
      end_offset?: number
    }

export interface Issue {
  id: string
  doc_id: string
  type: string
  text: string
  status: IssueStatus
  explanation: string
  suggested_fix: string
  risk_level?: string | null  // 风险等级：高/中/低
  location?: IssueLocation | null
  review_initiated_by: string
  review_initiated_at_UTC: string
  resolved_by: string
  resolved_at_UTC: string
  modified_fields: ModifiedFields
  dismissal_feedback: DismissalFeedback
}

export enum IssueStatus {
  NotReviewed = 'not_reviewed',
  Accepted = 'accepted',
  Dismissed = 'dismissed'
}

export interface ModifiedFields {
  suggested_fix?: string
  explanation?: string
}

export interface DismissalFeedback {
  reason?: string
}
