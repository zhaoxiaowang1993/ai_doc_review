import { EventSourceMessage, fetchEventSource } from '@microsoft/fetch-event-source'
import { FatalError, RetriableError } from '../types/error'
import type {
  ReviewRule, CreateRuleRequest, UpdateRuleRequest,
  DocumentTypeWithSubtypes, Document
} from '../types/rule'

function normalizeApiOrigin(value: unknown): string {
  if (!value || typeof value !== 'string') return ''
  const trimmed = value.trim()
  if (!trimmed) return ''
  try {
    return new URL(trimmed).origin
  } catch {
    return trimmed.replace(/\/+$/, '')
  }
}

const apiOrigin = normalizeApiOrigin(import.meta.env.VITE_API_ORIGIN)
const apiBaseUrl = `${apiOrigin}/api/v1/review/`
const rulesApiUrl = `${apiOrigin}/api/v1/rules`
const filesApiUrl = `${apiOrigin}/api/v1/files`
const documentsApiUrl = `${apiOrigin}/api/v1/documents`
const documentTypesApiUrl = `${apiOrigin}/api/v1/document-types`
const unknownError = '发生未知错误，请稍后重试。'

class AbortedError extends Error { }

async function getErrorMessage(response: Response): Promise<string> {
  let message = `接口错误（${response.statusText}）：`

  const errorText = await response.text()
  if (errorText) {
    let errorJson
    try {
      errorJson = JSON.parse(errorText)
      if (errorJson?.detail) {
        if (typeof errorJson.detail === 'string') {
          message += errorJson.detail
        } else {
          message += JSON.stringify(errorJson.detail)
        }
      } else if (errorJson?.message) {
        message += errorJson.message
      } else {
        message += unknownError
      }
    } catch {
      message += unknownError
    }
  } else {
    message += unknownError
  }

  return message
}

export async function callApi(path: string, method = 'GET', body?: object) {
  const response = await fetch(apiBaseUrl + path, {
    headers: { 'Content-Type': 'application/json' },
    method,
    body: body ? JSON.stringify(body) : null
  })

  if (!response.ok) {
    const message = await getErrorMessage(response)
    if (response.status === 503) {
      throw new RetriableError(message)
    } else {
      throw new FatalError(message)
    }
  }

  return response
}

export async function streamApi(
  path: string,
  messageHandler: (msg: EventSourceMessage) => void,
  fatalErrorHandler: (err: Error) => void,
  abortControllerRef: AbortController,
  maxRetries = 3
) {
  let retries = 0

  async function startStream() {
    fetchEventSource(apiBaseUrl + path, {
      signal: abortControllerRef.signal,
      async onopen(response) {
        if (abortControllerRef.signal.aborted) {
          console.log('Stream aborted before open')
          throw new AbortedError()
        }
        console.log('Stream opened', response)
        if (!response.ok) {
          const message = await getErrorMessage(response)
          if (response.status === 503) {
            throw new RetriableError(message)
          } else {
            throw new FatalError(message)
          }
        }
      },
      onmessage(msg) {
        console.log('Message:', msg)
        messageHandler(msg)
      },
      onclose() {
        console.log('Stream closed')
      },
      onerror(err) {
        console.error('Stream error', err)
        if (err instanceof RetriableError && retries < maxRetries) {
          retries++
          console.log(`Retrying stream... (${retries}/${maxRetries})`)
          startStream()
        } else {
          throw err
        }
      }
    }).catch(fatalErrorHandler)
  }

  startStream()
}

// ========== Rules API ==========

export async function getRules(): Promise<ReviewRule[]> {
  const response = await fetch(rulesApiUrl, {
    headers: { 'Content-Type': 'application/json' },
    method: 'GET'
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
  return response.json()
}

export async function createRule(data: CreateRuleRequest): Promise<ReviewRule> {
  const response = await fetch(rulesApiUrl, {
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
    body: JSON.stringify(data)
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
  return response.json()
}

export async function updateRule(ruleId: string, data: UpdateRuleRequest): Promise<ReviewRule> {
  const response = await fetch(`${rulesApiUrl}/${ruleId}`, {
    headers: { 'Content-Type': 'application/json' },
    method: 'PATCH',
    body: JSON.stringify(data)
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
  return response.json()
}

export async function deleteRule(ruleId: string): Promise<void> {
  const response = await fetch(`${rulesApiUrl}/${ruleId}`, {
    headers: { 'Content-Type': 'application/json' },
    method: 'DELETE'
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
}

export async function getRulesForReview(subtypeId: string): Promise<ReviewRule[]> {
  const response = await fetch(`${rulesApiUrl}/for-review/${subtypeId}`, {
    headers: { 'Content-Type': 'application/json' },
    method: 'GET'
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
  return response.json()
}

// ========== Document Types API ==========

export async function getDocumentTypes(): Promise<DocumentTypeWithSubtypes[]> {
  const response = await fetch(documentTypesApiUrl, {
    headers: { 'Content-Type': 'application/json' },
    method: 'GET'
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
  return response.json()
}

export async function getRulesBySubtype(subtypeId: string, includeUniversal = true): Promise<ReviewRule[]> {
  const url = `${rulesApiUrl}/by-subtype/${subtypeId}?include_universal=${includeUniversal}`
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    method: 'GET'
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
  return response.json()
}

// ========== Documents API ==========

export async function getDocument(docId: string): Promise<Document> {
  const response = await fetch(`${documentsApiUrl}/${docId}`, {
    headers: { 'Content-Type': 'application/json' },
    method: 'GET'
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
  return response.json()
}

export interface UploadFileResponse {
  filename: string
  doc_id: string | null
  subtype_id: string | null
}

export async function uploadFile(file: File, subtypeId?: string): Promise<UploadFileResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (subtypeId) {
    formData.append('subtype_id', subtypeId)
  }

  const response = await fetch(`${filesApiUrl}/upload`, {
    method: 'POST',
    body: formData
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
  return response.json()
}

export async function getFiles(): Promise<string[]> {
  const response = await fetch(filesApiUrl, {
    headers: { 'Content-Type': 'application/json' },
    method: 'GET'
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
  return response.json()
}

export async function deleteFile(filename: string): Promise<void> {
  const response = await fetch(`${filesApiUrl}/${filename}`, {
    method: 'DELETE'
  })
  if (!response.ok) {
    const message = await getErrorMessage(response)
    throw new FatalError(message)
  }
}

