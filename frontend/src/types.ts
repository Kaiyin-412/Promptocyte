export type Analysis = { original_prompt: string; normalized_prompt: string; transformation_detected: boolean; transformations: string[]; risk_score: number; category: string; severity: string; decision: string; explanation: string; evidence: string[]; confidence: number; source: 'regex' | 'ml' }
export type HistoryItem = Analysis & { id: number; prompt: string; created_at: string }
export type Stats = { total_analyzed: number; blocked: number; warned: number; allowed: number; security_score: number }
