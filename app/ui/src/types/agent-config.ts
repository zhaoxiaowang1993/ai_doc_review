export interface Agent {
  color: 'informative' | 'brand' | 'danger' | 'important' | undefined,
  description: string
}

export interface AgentConfig {
  [key: string]: Agent
}
