// API Service for CBIE Backend Integration
const API_BASE_URL = '/api/v1';

export interface Behavior {
  id: string;
  text: string;
  credibility: number;
  timestamp: number;
  source: string;
  embedding: { x: number; y: number };
  clusterId: string | null;
  clusterName?: string;
  clusterStability: number;
  epistemicState?: string;
}

export interface ClusterData {
  id: string;
  name: string;
  stability: number;
  size: number;
  isCore: boolean;
  epistemicState?: string;
  confidence?: number;
  clusterStrength?: number;
}

export interface AnalysisResult {
  behaviors: Behavior[];
  clusters: ClusterData[];
  metrics: {
    totalObservations: number;
    coreClusters: number;
    insufficientEvidence: number;
    noiseObservations: number;
    totalClusters?: number;
  };
  archetype?: string;
  generated_at?: number;
}

export interface UserInfo {
  user_id: string;
  prompt_count: number;
  behavior_count: number;
}

export interface LLMContextResponse {
  user_id: string;
  archetype?: string;
  context_string: string;
  primary_behaviors: Array<{
    label: string;
    strength: number;
    confidence: number;
  }>;
  metadata: {
    behavior_count: number;
    min_strength: number;
    min_confidence: number;
  };
}

// Fetch analysis summary with 2D projections
export async function fetchAnalysisData(userId: string): Promise<AnalysisResult> {
  const response = await fetch(`${API_BASE_URL}/profile/${userId}/analysis-summary`);
  if (!response.ok) {
    throw new Error(`Failed to fetch analysis data: ${response.statusText}`);
  }
  return await response.json();
}

// Fetch list of available test users
export async function fetchTestUsers(): Promise<UserInfo[]> {
  const response = await fetch(`${API_BASE_URL}/test-users`);
  if (!response.ok) {
    throw new Error(`Failed to fetch test users: ${response.statusText}`);
  }
  const data = await response.json();
  return data.users || [];
}

// Simulate threshold change
export async function simulateThreshold(
  userId: string,
  stabilityThreshold: number
): Promise<AnalysisResult> {
  const response = await fetch(
    `${API_BASE_URL}/profile/${userId}/simulate-threshold?stability_threshold=${stabilityThreshold}`,
    { method: 'POST' }
  );
  if (!response.ok) {
    throw new Error(`Failed to simulate threshold: ${response.statusText}`);
  }
  return await response.json();
}

// Fetch LLM context for user
export async function fetchLLMContext(
  userId: string,
  minStrength: number = 30.0,
  minConfidence: number = 0.40,
  maxBehaviors: number = 5
): Promise<LLMContextResponse> {
  const params = new URLSearchParams({
    min_strength: minStrength.toString(),
    min_confidence: minConfidence.toString(),
    max_behaviors: maxBehaviors.toString(),
    include_archetype: 'true'
  });
  
  const response = await fetch(`${API_BASE_URL}/profile/${userId}/llm-context?${params}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch LLM context: ${response.statusText}`);
  }
  return await response.json();
}

// Health check
export async function checkHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return await response.json();
}
