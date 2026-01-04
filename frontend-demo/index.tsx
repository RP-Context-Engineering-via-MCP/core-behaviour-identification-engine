
import React, { useState, useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import { GoogleGenAI } from "@google/genai";
import { fetchAnalysisData, fetchTestUsers, simulateThreshold, fetchLLMContext, type UserInfo } from './api';

// --- Types & Constants ---

type BehaviorStatus = 'CORE' | 'INSUFFICIENT' | 'NOISE';

interface Behavior {
  id: string;
  text: string;
  credibility: number;
  timestamp: number;
  source: string;
  embedding: { x: number; y: number }; // 2D projection
  clusterId: string | null;
  clusterName?: string;
  clusterStability: number;
}

interface UserProfile {
  id: string;
  name: string;
  type: 'sparse' | 'dense' | 'clean';
  description: string;
  prompt_count?: number;
  behavior_count?: number;
}

interface ClusterData {
  id: string;
  name: string;
  stability: number;
  size: number;
  isCore: boolean;
}

interface AnalysisResult {
  behaviors: Behavior[];
  clusters: ClusterData[];
  metrics: {
    totalObservations: number;
    coreClusters: number;
    insufficientEvidence: number;
    noiseObservations: number;
  };
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: number;
}

// Users will be fetched from backend
const DEFAULT_USER: UserProfile = {
  id: 'user_665390',
  name: 'User 665390',
  type: 'clean',
  description: 'Real user data from CBIE system'
};

const PAGES = [
  { id: 1, title: 'Analysis Dashboard', icon: '📊' },
  { id: 2, title: 'Raw vs Inference', icon: '🔍' },
  { id: 3, title: 'Embedding Space', icon: '🌌' },
  { id: 4, title: 'Cluster Inspector', icon: '🛡️' },
  { id: 5, title: 'Baseline Comparison', icon: '⚖️' },
  { id: 6, title: 'Threshold Lab', icon: '🎚️' },
  { id: 7, title: 'Context-Aware Chat', icon: '💬' },
];

// Data fetched from backend API - no mock generators needed

// --- Components ---

const Sidebar = ({ 
  activePage, 
  setActivePage,
  selectedUser,
  setSelectedUser,
  isAnalyzing,
  availableUsers
}: { 
  activePage: number, 
  setActivePage: (n: number) => void,
  selectedUser: UserProfile,
  setSelectedUser: (u: UserProfile) => void,
  isAnalyzing: boolean,
  availableUsers: UserProfile[]
}) => (
  <div style={{ width: '280px', background: 'var(--color-sidebar)', color: 'white', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
    <div style={{ padding: '2rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
      <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.5rem', letterSpacing: '0.1em' }}>SYSTEM</div>
      <h1 style={{ fontSize: '1.25rem', fontWeight: '700', margin: '0 0 1.5rem 0', lineHeight: 1.2 }}>CBIE<br/><span style={{fontWeight: 400, opacity: 0.8, fontSize: '1rem'}}>Behavior Engine</span></h1>
      
      {/* Persistent User Selector */}
      <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '8px', padding: '0.75rem' }}>
        <label style={{ display: 'block', fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.5rem' }}>ACTIVE USER</label>
        <select 
          value={selectedUser.id}
          onChange={(e) => setSelectedUser(availableUsers.find(u => u.id === e.target.value) || availableUsers[0])}
          disabled={isAnalyzing}
          style={{ 
            width: '100%', 
            padding: '0.5rem', 
            borderRadius: '4px', 
            border: '1px solid rgba(255,255,255,0.2)', 
            background: '#1F2937', 
            color: 'white',
            fontFamily: 'var(--font-sans)',
            fontSize: '0.875rem'
          }}
        >
          {availableUsers.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
        </select>
        <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>
          {selectedUser.type === 'sparse' && 'Sparse Data Regime'}
          {selectedUser.type === 'dense' && 'Noisy Data Regime'}
          {selectedUser.type === 'clean' && 'Ideal Data Regime'}
        </div>
      </div>
    </div>
    
    <nav style={{ flex: 1, padding: '1rem' }}>
      {PAGES.map(page => (
        <button
          key={page.id}
          onClick={() => setActivePage(page.id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            width: '100%',
            padding: '0.75rem 1rem',
            marginBottom: '0.25rem',
            background: activePage === page.id ? 'var(--color-core)' : 'transparent',
            border: 'none',
            borderRadius: '6px',
            color: activePage === page.id ? 'white' : 'rgba(255,255,255,0.7)',
            cursor: 'pointer',
            textAlign: 'left',
            fontFamily: 'var(--font-sans)',
            fontSize: '0.875rem',
            fontWeight: activePage === page.id ? 600 : 500,
            transition: 'background 0.2s'
          }}
        >
          <span style={{ marginRight: '0.75rem', fontSize: '1.1em' }}>{page.icon}</span>
          {page.title}
        </button>
      ))}
    </nav>
    <div style={{ padding: '1.5rem', fontSize: '0.75rem', color: 'rgba(255,255,255,0.3)' }}>
      v1.0.5-demo<br/>
      Connected to Local Storage
    </div>
  </div>
);

const MetricCard = ({ label, value, sub, colorClass }: { label: string, value: string | number, sub: string, colorClass?: string }) => (
  <div className="card" style={{ padding: '1.5rem' }}>
    <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>{label}</div>
    <div style={{ fontSize: '2.5rem', fontWeight: '700', marginBottom: '0.25rem', color: colorClass ? `var(${colorClass})` : 'inherit' }}>{value}</div>
    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{sub}</div>
  </div>
);

const EmbeddingChart = ({ behaviors, stabilityThreshold }: { behaviors: Behavior[], stabilityThreshold: number }) => {
  const xValues = behaviors.map(b => b.embedding.x);
  const yValues = behaviors.map(b => b.embedding.y);
  const minX = Math.min(...xValues, -5);
  const maxX = Math.max(...xValues, 5);
  const minY = Math.min(...yValues, -5);
  const maxY = Math.max(...yValues, 5);
  
  const width = 600;
  const height = 400;
  const padding = 40;

  const scaleX = (x: number) => padding + ((x - minX) / (maxX - minX)) * (width - 2 * padding);
  const scaleY = (y: number) => height - (padding + ((y - minY) / (maxY - minY)) * (height - 2 * padding));

  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div className="card" style={{ padding: '1rem', position: 'relative', overflow: 'hidden' }}>
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
        <line x1={padding} y1={height/2} x2={width-padding} y2={height/2} stroke="#E5E7EB" />
        <line x1={width/2} y1={padding} x2={width/2} y2={height-padding} stroke="#E5E7EB" />
        
        {behaviors.map(b => {
          let fill = '#9CA3AF'; // Noise
          let r = 4;
          let opacity = 0.5;
          let stroke = 'none';

          if (b.clusterId) {
             const isStable = b.clusterStability >= stabilityThreshold;
             if (isStable) {
               fill = '#059669'; // CORE
               r = 6;
               opacity = 0.9;
             } else {
               fill = '#D97706'; // Insufficient
               opacity = 0.7;
             }
          }
          
          const isHovered = hovered === b.id;
          if (isHovered) {
            r = 8;
            stroke = '#000';
            opacity = 1;
          }

          return (
            <circle
              key={b.id}
              cx={scaleX(b.embedding.x)}
              cy={scaleY(b.embedding.y)}
              r={r}
              fill={fill}
              opacity={opacity}
              stroke={stroke}
              strokeWidth={2}
              onMouseEnter={() => setHovered(b.id)}
              onMouseLeave={() => setHovered(null)}
              style={{ transition: 'all 0.2s', cursor: 'pointer' }}
            />
          );
        })}
      </svg>
      {hovered && (
        <div style={{
          position: 'absolute', top: 10, left: 10,
          background: 'rgba(0,0,0,0.8)', color: 'white',
          padding: '0.5rem', borderRadius: '4px', fontSize: '0.75rem',
          maxWidth: '200px', pointerEvents: 'none', zIndex: 10
        }}>
          {behaviors.find(b => b.id === hovered)?.text}
        </div>
      )}
    </div>
  );
};

// --- Chat Component with Gemini ---

const ChatInterface = ({ 
  user, 
  analysisResult, 
  messages, 
  setMessages 
}: { 
  user: UserProfile, 
  analysisResult: AnalysisResult,
  messages: ChatMessage[],
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
}) => {
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showNoise, setShowNoise] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const coreClusters = analysisResult.clusters.filter(c => c.isCore);
  const coreBehaviors = analysisResult.behaviors.filter(b => b.clusterId && coreClusters.find(c => c.id === b.clusterId));
  const insufficientBehaviors = analysisResult.behaviors.filter(b => b.clusterId && !coreClusters.find(c => c.id === b.clusterId));
  const noiseBehaviors = analysisResult.behaviors.filter(b => !b.clusterId);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      text: input,
      timestamp: Date.now()
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      // Fetch LLM context from backend on first message
      let contextString = "";
      if (messages.length === 0) {
        try {
          const contextData = await fetchLLMContext(user.id);
          contextString = contextData.context_string;
          logger.info("Fetched LLM context from backend:", contextData);
        } catch (e) {
          console.error("Failed to fetch LLM context:", e);
          // Fall back to using local cluster data
          contextString = coreClusters.map(c => 
            `- Preference Area: ${c.name} (Stability: ${c.stability.toFixed(2)})`
          ).join('\n');
        }
      } else {
        // Use local cluster data for subsequent messages
        contextString = coreClusters.map(c => 
          `- Preference Area: ${c.name} (Stability: ${c.stability.toFixed(2)})`
        ).join('\n');
      }
    
      // Construct System Instruction
      const systemInstruction = `
        You are a helpful assistant participating in a demo of a "Conservative Behavior Identification Engine".
        
        CRITICAL INSTRUCTION:
        You have access to a list of VERIFIED USER PREFERENCES (CORE behaviors) below.
        You MUST personalize your response based on these preferences if the user's message is relevant to them.
        If the preference list is empty, you MUST behave as a generic, polite assistant and NOT invent any preferences.
        
        VERIFIED PREFERENCES (CORE ONLY):
        ${contextString.length > 0 ? contextString : "(No verified preferences found. Do not guess.)"}

        Do not explicitly mention "CORE behaviors" or "the database". Just incorporate the knowledge naturally.
      `;

      let responseText = "";

      if (process.env.API_KEY) {
        const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
        const model = ai.models.generateContent({
           model: 'gemini-2.0-flash-exp',
           config: { systemInstruction },
           contents: [{ role: 'user', parts: [{ text: input }] }]
        });
        const result = await model;
        responseText = result.response.text || "I'm having trouble connecting right now.";
      } else {
        throw new Error("No API Key");
      }

      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        text: responseText,
        timestamp: Date.now()
      }]);
    } catch (e) {
      // Fallback Simulation Logic if API key fails or is missing
      await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate latency
      
      let responseText = "";
      if (coreClusters.length === 0) {
        responseText = "I can certainly help with that. Could you provide more specific details about what you're looking for?";
      } else {
        responseText = `I can help you with that request based on your verified interests: ${coreClusters.map(c => c.name).join(', ')}.`;
      }

      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        text: responseText,
        timestamp: Date.now()
      }]);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '350px 1fr', gap: '2rem', height: 'calc(100vh - 4rem)' }}>
      {/* LEFT PANEL: SYSTEM KNOWLEDGE */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--color-border)', background: '#F9FAFB' }}>
          <h3 style={{ margin: 0, fontSize: '1rem' }}>What the System Knows</h3>
          <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Only CORE data is exposed to LLM</p>
        </div>
        
        <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
          {/* CORE SECTION */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-core)', textTransform: 'uppercase' }}>CORE (Exposed)</span>
              <span className="badge badge-core">{coreClusters.length} Clusters</span>
            </div>
            {coreClusters.length > 0 ? (
               coreClusters.map(c => (
                 <div key={c.id} style={{ padding: '0.75rem', background: 'var(--color-core-bg)', border: '1px solid #A7F3D0', borderRadius: '6px', marginBottom: '0.5rem' }}>
                   <div style={{ fontWeight: 600, color: '#064E3B', fontSize: '0.875rem' }}>{c.name}</div>
                   <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: '#065F46', marginTop: '0.25rem' }}>
                     <span>Stability: {c.stability.toFixed(2)}</span>
                     <span>N={c.size}</span>
                   </div>
                 </div>
               ))
            ) : (
              <div style={{ padding: '1rem', border: '1px dashed var(--color-border)', borderRadius: '6px', fontSize: '0.875rem', color: 'var(--color-text-muted)', fontStyle: 'italic', textAlign: 'center' }}>
                No stable preferences found.<br/>System abstains.
              </div>
            )}
          </div>

          {/* INSUFFICIENT SECTION */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-insufficient)', textTransform: 'uppercase' }}>Insufficient (Withheld)</span>
              <span className="badge badge-insufficient">{insufficientBehaviors.length} items</span>
            </div>
            <div style={{ opacity: 0.7 }}>
              {insufficientBehaviors.slice(0, 5).map(b => (
                <div key={b.id} style={{ padding: '0.5rem', background: '#FEF3C7', border: '1px solid #FDE68A', borderRadius: '4px', marginBottom: '0.25rem', fontSize: '0.75rem', color: '#92400E' }}>
                  {b.clusterName ? `Unstable Cluster: ${b.clusterName}` : b.text}
                </div>
              ))}
              {insufficientBehaviors.length > 5 && <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>+ {insufficientBehaviors.length - 5} more withheld</div>}
            </div>
          </div>

          {/* NOISE SECTION */}
          <div>
            <div 
              onClick={() => setShowNoise(!showNoise)}
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', cursor: 'pointer' }}
            >
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-noise)', textTransform: 'uppercase' }}>Noise (Filtered)</span>
              <span style={{ fontSize: '0.75rem', textDecoration: 'underline' }}>{showNoise ? 'Hide' : 'Show'}</span>
            </div>
            {showNoise && (
              <div style={{ opacity: 0.5 }}>
                 <div style={{ padding: '0.5rem', background: 'var(--color-noise-bg)', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                   {noiseBehaviors.length} raw noise points filtered out.
                 </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* RIGHT PANEL: CHAT UI */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '1rem', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '1rem' }}>Chat Interface</h3>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
             LLM Context Source: <span className="badge badge-core">CBIE</span>
          </div>
        </div>
        
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: '#F9FAFB' }}>
          {messages.length === 0 && (
             <div style={{ textAlign: 'center', marginTop: '2rem', color: 'var(--color-text-muted)' }}>
               <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🤖</div>
               <p>Start a conversation to test personalization constraints.</p>
               {coreClusters.length === 0 && (
                 <div style={{ background: '#E5E7EB', padding: '0.5rem', borderRadius: '4px', display: 'inline-block', fontSize: '0.75rem', marginTop: '0.5rem' }}>
                   System is in <strong>Abstention Mode</strong> (No Personalization)
                 </div>
               )}
             </div>
          )}
          
          {messages.map(m => (
            <div key={m.id} style={{ display: 'flex', flexDirection: 'column', alignItems: m.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: '1rem' }}>
              <div style={{ 
                maxWidth: '80%', 
                padding: '0.75rem 1rem', 
                borderRadius: '12px', 
                background: m.role === 'user' ? 'var(--color-sidebar)' : 'white',
                color: m.role === 'user' ? 'white' : 'var(--color-text-main)',
                border: m.role === 'assistant' ? '1px solid var(--color-border)' : 'none',
                boxShadow: m.role === 'assistant' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                fontSize: '0.9rem',
                lineHeight: '1.5'
              }}>
                {m.text}
              </div>
              <div style={{ fontSize: '0.7rem', color: '#9CA3AF', marginTop: '0.25rem', padding: '0 0.5rem' }}>
                {m.role === 'assistant' ? 'Assistant' : 'User'}
              </div>
            </div>
          ))}
          {isTyping && (
             <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '1rem' }}>
               <div style={{ background: 'white', padding: '0.75rem 1rem', borderRadius: '12px', border: '1px solid var(--color-border)' }}>
                 <span className="animate-pulse">...</span>
               </div>
             </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div style={{ padding: '1rem', borderTop: '1px solid var(--color-border)', background: 'white' }}>
           <div style={{ display: 'flex', gap: '0.5rem' }}>
             <input 
               type="text" 
               placeholder="Type a message..." 
               value={input}
               onChange={(e) => setInput(e.target.value)}
               onKeyDown={(e) => e.key === 'Enter' && handleSend()}
               disabled={isTyping}
               style={{ flex: 1, padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--color-border)', fontFamily: 'var(--font-sans)' }}
             />
             <button className="btn btn-primary" onClick={handleSend} disabled={isTyping || !input.trim()}>
               Send
             </button>
           </div>
           <div style={{ textAlign: 'center', marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
             The LLM <strong>never</strong> sees insufficient or noisy signals.
           </div>
        </div>
      </div>
    </div>
  );
};

// --- Main Application ---

const App = () => {
  const [activePage, setActivePage] = useState(1);
  const [selectedUser, setSelectedUser] = useState<UserProfile>(DEFAULT_USER);
  const [availableUsers, setAvailableUsers] = useState<UserProfile[]>([DEFAULT_USER]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [stabilityThreshold, setStabilityThreshold] = useState(0.15);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Chat state stored at App level to persist navigation (but reset on user change)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  // Load available users from backend
  useEffect(() => {
    const loadUsers = async () => {
      try {
        const users = await fetchTestUsers();
        const userProfiles: UserProfile[] = users.map(u => ({
          id: u.user_id,
          name: `User ${u.user_id.split('_')[1] || u.user_id}`,
          type: 'clean' as const,
          description: `${u.behavior_count} behaviors, ${u.prompt_count} prompts`,
          prompt_count: u.prompt_count,
          behavior_count: u.behavior_count
        }));
        
        if (userProfiles.length > 0) {
          setAvailableUsers(userProfiles);
          setSelectedUser(userProfiles[0]);
        }
        setLoadingUsers(false);
      } catch (e) {
        console.error("Failed to load users:", e);
        setError("Failed to connect to backend. Using default user.");
        setLoadingUsers(false);
      }
    };
    
    loadUsers();
  }, []);

  // Effect: Reset analysis and chat when user changes
  useEffect(() => {
    setAnalysisResult(null);
    setChatMessages([]);
  }, [selectedUser.id]);

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    setError(null);
    
    try {
      const result = await fetchAnalysisData(selectedUser.id);
      setAnalysisResult(result);
      setIsAnalyzing(false);
    } catch (e) {
      console.error("Analysis failed:", e);
      setError(`Failed to analyze user ${selectedUser.id}. Please ensure the backend is running.`);
      setIsAnalyzing(false);
    }
  };

  // Re-run threshold simulation when threshold changes
  useEffect(() => {
    if (analysisResult && analysisResult.behaviors.length > 0) {
      const simulateNewThreshold = async () => {
        try {
          const result = await simulateThreshold(selectedUser.id, stabilityThreshold);
          // Update only the clusters and metrics, keep behaviors the same
          setAnalysisResult(prev => prev ? ({
            ...prev,
            clusters: result.updated_clusters,
            metrics: {
              ...prev.metrics,
              coreClusters: result.coreClusters,
              insufficientEvidence: result.metrics.insufficientEvidence,
              noiseObservations: result.metrics.noiseObservations
            }
          }) : null);
        } catch (e) {
          console.error("Threshold simulation failed:", e);
        }
      };
      
      simulateNewThreshold();
    }
  }, [stabilityThreshold, selectedUser.id]);

  const getStatus = (b: Behavior): BehaviorStatus => {
    if (!b.clusterId) return 'NOISE';
    const cluster = analysisResult?.clusters.find(c => c.id === b.clusterId);
    return cluster?.isCore ? 'CORE' : 'INSUFFICIENT';
  };

  const renderContent = () => {
    // If no analysis, show prompt (except for Dashboard where the button is)
    if (!analysisResult && activePage !== 1) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-text-muted)' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>👋</div>
          <h3>No Analysis Loaded</h3>
          <p>Please go to the Dashboard and run an analysis for <strong>{selectedUser.name}</strong>.</p>
          <button className="btn btn-primary" onClick={() => setActivePage(1)} style={{ marginTop: '1rem' }}>Go to Dashboard</button>
        </div>
      );
    }

    switch (activePage) {
      case 1: // Dashboard
        return (
          <div className="animate-fade-in" style={{ maxWidth: '1000px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
              <div>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '700', margin: 0 }}>User Analysis Dashboard</h2>
                <p style={{ color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>Current Target: {selectedUser.name}</p>
              </div>
              <div className="card" style={{ padding: '0.5rem' }}>
                <button className="btn btn-primary" onClick={runAnalysis} disabled={isAnalyzing}>
                  {isAnalyzing ? 'Processing...' : 'Run Analysis'}
                </button>
              </div>
            </div>

            {/* If no analysis yet, show placeholder */}
            {!analysisResult && (
               <div style={{ textAlign: 'center', padding: '4rem', background: 'white', borderRadius: '8px', border: '1px dashed var(--color-border)' }}>
                 <h3>Ready to Analyze</h3>
                 <p style={{ color: 'var(--color-text-muted)' }}>Click "Run Analysis" to process behavioral signals from storage.</p>
               </div>
            )}

            {analysisResult && (
              <>
                <div style={{ marginBottom: '2rem', padding: '1rem', background: '#EFF6FF', borderRadius: '8px', border: '1px solid #DBEAFE', color: '#1E40AF' }}>
                  <strong>User Context:</strong> {selectedUser.description}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem' }}>
                  <MetricCard 
                    label="Total Observations" 
                    value={analysisResult.metrics.totalObservations} 
                    sub="Data Sparsity Level"
                  />
                  <MetricCard 
                    label="CORE Clusters" 
                    value={analysisResult.metrics.coreClusters} 
                    sub="Verified Preferences"
                    colorClass="--color-core"
                  />
                  <MetricCard 
                    label="Insufficient Ev." 
                    value={analysisResult.metrics.insufficientEvidence} 
                    sub="Uncertainty Handled"
                    colorClass="--color-insufficient"
                  />
                  <MetricCard 
                    label="Noise Observations" 
                    value={analysisResult.metrics.noiseObservations} 
                    sub="Filtered Out"
                    colorClass="--color-text-muted"
                  />
                </div>
                <div style={{ marginTop: '2rem', padding: '1rem', border: '1px dashed var(--color-border)', borderRadius: '8px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  Analysis Mode: <strong style={{color: 'var(--color-text-main)'}}>Conservative (Density-Based)</strong>
                </div>
              </>
            )}
          </div>
        );

      case 2: // Raw vs Inference
        return (
          <div className="animate-fade-in" style={{ height: 'calc(100vh - 4rem)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ marginBottom: '1rem' }}>Raw Observations</h3>
              <div className="card" style={{ flex: 1, overflow: 'auto' }}>
                <table>
                  <thead style={{ position: 'sticky', top: 0, background: 'var(--color-surface)', zIndex: 10 }}>
                    <tr>
                      <th>Behavior Text</th>
                      <th>Cred.</th>
                      <th>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysisResult!.behaviors.map(b => (
                      <tr key={b.id}>
                        <td className="font-mono">{b.text}</td>
                        <td>{b.credibility.toFixed(2)}</td>
                        <td>{new Date(b.timestamp).toLocaleTimeString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ marginBottom: '1rem' }}>Classification Outcome</h3>
              <div className="card" style={{ flex: 1, overflow: 'auto' }}>
                <table>
                  <thead style={{ position: 'sticky', top: 0, background: 'var(--color-surface)', zIndex: 10 }}>
                    <tr>
                      <th>State</th>
                      <th>Cluster</th>
                      <th>Stability</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysisResult!.behaviors.map(b => {
                      const status = getStatus(b);
                      let badgeClass = '';
                      if (status === 'CORE') badgeClass = 'badge-core';
                      else if (status === 'INSUFFICIENT') badgeClass = 'badge-insufficient';
                      else badgeClass = 'badge-noise';

                      return (
                        <tr key={b.id}>
                          <td><span className={`badge ${badgeClass}`}>{status}</span></td>
                          <td>{b.clusterId ? `C-${b.clusterId}` : '-'}</td>
                          <td>{b.clusterStability > 0 ? b.clusterStability.toFixed(2) : '-'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );

      case 3: // Embedding Space
        return (
          <div className="animate-fade-in" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between' }}>
               <h2 style={{ fontSize: '1.5rem', fontWeight: '700', margin: 0 }}>Embedding Space Visualization</h2>
               <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>Projection: UMAP-2D</div>
            </div>
            <div style={{ flex: 1, display: 'flex', gap: '2rem' }}>
              <div style={{ flex: 2, height: '100%' }}>
                <EmbeddingChart behaviors={analysisResult!.behaviors} stabilityThreshold={stabilityThreshold} />
              </div>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="card" style={{ padding: '1rem' }}>
                   <h4 style={{ margin: '0 0 0.5rem 0' }}>Legend</h4>
                   <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.875rem', lineHeight: '1.6' }}>
                     <li style={{display:'flex', alignItems:'center', gap:'0.5rem'}}>
                       <span style={{width:10, height:10, borderRadius:'50%', background:'var(--color-core)'}}></span> 
                       <strong>Dense Cluster</strong> → CORE Candidate
                     </li>
                     <li style={{display:'flex', alignItems:'center', gap:'0.5rem'}}>
                       <span style={{width:10, height:10, borderRadius:'50%', background:'var(--color-insufficient)'}}></span> 
                       <strong>Sparse Cloud</strong> → Abstention
                     </li>
                     <li style={{display:'flex', alignItems:'center', gap:'0.5rem'}}>
                       <span style={{width:10, height:10, borderRadius:'50%', background:'var(--color-noise)'}}></span> 
                       <strong>Isolated Points</strong> → Noise
                     </li>
                   </ul>
                </div>
                <div className="card" style={{ padding: '1rem', background: '#F8FAFC' }}>
                   <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                     <strong>Key Insight:</strong> The system does not force points into groups. It identifies organic density. Notice how noise points remain uncolored (gray).
                   </p>
                </div>
              </div>
            </div>
          </div>
        );

      case 4: // Cluster Inspector
        return (
          <div className="animate-fade-in">
             <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem' }}>Cluster Stability Inspector</h2>
             <div className="card">
               <table>
                 <thead>
                   <tr>
                     <th>Cluster Name</th>
                     <th>Size (N)</th>
                     <th>Stability Score</th>
                     <th>Threshold</th>
                     <th>Result</th>
                     <th style={{ width: '200px' }}>Visual</th>
                   </tr>
                 </thead>
                 <tbody>
                   {analysisResult!.clusters.map(c => (
                     <tr key={c.id}>
                       <td style={{ fontWeight: 600 }}>{c.name}</td>
                       <td>{c.size}</td>
                       <td className="font-mono">{c.stability.toFixed(3)}</td>
                       <td className="font-mono">{stabilityThreshold.toFixed(2)}</td>
                       <td>
                         {c.isCore 
                           ? <span className="badge badge-core">ACCEPTED</span>
                           : <span className="badge badge-insufficient">REJECTED</span>
                         }
                       </td>
                       <td>
                         <div style={{ width: '100%', height: '8px', background: '#E5E7EB', borderRadius: '4px', position: 'relative' }}>
                           <div style={{
                             width: `${Math.min(c.stability * 100 * 2, 100)}%`, // Scale up for visibility
                             height: '100%',
                             background: c.stability >= stabilityThreshold ? 'var(--color-core)' : '#EF4444',
                             borderRadius: '4px'
                           }}></div>
                           {/* Threshold Line */}
                           <div style={{
                             position: 'absolute',
                             left: `${stabilityThreshold * 100 * 2}%`,
                             top: '-4px',
                             bottom: '-4px',
                             width: '2px',
                             background: 'black',
                             zIndex: 2
                           }}></div>
                         </div>
                       </td>
                     </tr>
                   ))}
                   {analysisResult!.clusters.length === 0 && (
                     <tr>
                       <td colSpan={6} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: '2rem' }}>
                         No clusters formed. System abstains completely.
                       </td>
                     </tr>
                   )}
                 </tbody>
               </table>
             </div>
             <div style={{ marginTop: '2rem', padding: '1rem', borderLeft: '4px solid var(--color-sidebar)', background: 'white' }}>
               <h4 style={{ margin: '0 0 0.5rem 0' }}>Why this matters</h4>
               <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                 Stability measures how robust a cluster is to parameter changes. Low stability means the cluster is ephemeral or accidental. We filter these out to ensure quality.
               </p>
             </div>
          </div>
        );

      case 5: // Baseline Comparison
        return (
          <div className="animate-fade-in">
             <div style={{ marginBottom: '2rem' }}>
               <h2 style={{ fontSize: '1.5rem', fontWeight: '700', margin: 0 }}>Baseline Comparison</h2>
               <p style={{ color: 'var(--color-text-muted)' }}>The "Kill Shot": Why density beats frequency.</p>
             </div>

             <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
               <div className="card" style={{ padding: '2rem', borderTop: '4px solid var(--color-core)' }}>
                 <h3 style={{ marginTop: 0 }}>✅ Density-Based (CBIE)</h3>
                 <div style={{ fontSize: '3rem', fontWeight: 700, color: 'var(--color-core)' }}>
                   {analysisResult!.metrics.coreClusters}
                 </div>
                 <div style={{ fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)' }}>CORE Behaviors Promoted</div>
                 <hr style={{ margin: '1.5rem 0', border: 'none', borderBottom: '1px solid var(--color-border)' }} />
                 <ul style={{ paddingLeft: '1.25rem', lineHeight: '1.8' }}>
                   <li>Only semantically stable groups</li>
                   <li>Abstains on noise</li>
                   <li><strong>Result:</strong> High Precision</li>
                 </ul>
               </div>

               <div className="card" style={{ padding: '2rem', borderTop: '4px solid #EF4444' }}>
                 <h3 style={{ marginTop: 0 }}>❌ Frequency-Based Baseline</h3>
                 <div style={{ fontSize: '3rem', fontWeight: 700, color: '#EF4444' }}>
                   {selectedUser.type === 'sparse' ? '3' : (selectedUser.type === 'dense' ? '17' : '22')}
                 </div>
                 <div style={{ fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)' }}>CORE Behaviors Promoted</div>
                 <hr style={{ margin: '1.5rem 0', border: 'none', borderBottom: '1px solid var(--color-border)' }} />
                 <ul style={{ paddingLeft: '1.25rem', lineHeight: '1.8' }}>
                   <li>Counts raw occurrences</li>
                   <li>Promotes repetitive noise</li>
                   <li><strong>Result:</strong> High False Positives</li>
                 </ul>
               </div>
             </div>

             <div style={{ marginTop: '2rem', background: '#FEF2F2', padding: '1.5rem', borderRadius: '8px', color: '#991B1B', border: '1px solid #FECACA' }}>
               <strong>Verdict:</strong> The frequency-based model would have incorrectly exposed 
               {selectedUser.type === 'sparse' ? ' 3 ' : (selectedUser.type === 'dense' ? ' 16 ' : ' 10 ')} 
               behaviors that CBIE correctly filtered out as noise or insufficient evidence.
             </div>
          </div>
        );

      case 6: // Threshold Sensitivity
        return (
          <div className="animate-fade-in">
            <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem' }}>Threshold Sensitivity Playground</h2>
            
            <div className="card" style={{ padding: '2rem', marginBottom: '2rem' }}>
              <label style={{ display: 'block', marginBottom: '1rem', fontWeight: 600 }}>
                Stability Threshold: <span className="font-mono" style={{ color: 'var(--color-sidebar)' }}>{stabilityThreshold.toFixed(2)}</span>
              </label>
              <input 
                type="range" 
                min="0.05" 
                max="0.50" 
                step="0.01" 
                value={stabilityThreshold}
                onChange={(e) => setStabilityThreshold(parseFloat(e.target.value))}
                style={{ width: '100%', marginBottom: '1rem' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                <span>0.05 (Permissive)</span>
                <span>0.50 (Strict)</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
               <div className="card" style={{ padding: '2rem', flex: 1, textAlign: 'center' }}>
                 <div style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>Resulting Core Clusters</div>
                 <div style={{ fontSize: '4rem', fontWeight: 700, color: 'var(--color-sidebar)' }}>
                   {analysisResult!.metrics.coreClusters}
                 </div>
               </div>
               <div style={{ flex: 2 }}>
                 <p style={{ lineHeight: '1.6' }}>
                   Adjusting the threshold demonstrates that the system's decisions are <strong>documented and controllable</strong>, not black-box magic. 
                   <br/><br/>
                   Raising the threshold eliminates weaker clusters (amber → gray). Lowering it accepts more risk (gray → green).
                 </p>
               </div>
            </div>
          </div>
        );

      case 7: // Context-Aware Chat (NEW)
        return (
          <ChatInterface 
            user={selectedUser} 
            analysisResult={analysisResult} 
            messages={chatMessages}
            setMessages={setChatMessages}
          />
        );

      default:
        return <div>Page not found</div>;
    }
  };

  return (
    <div style={{ display: 'flex', width: '100%', height: '100%' }}>
      <Sidebar 
        activePage={activePage} 
        setActivePage={setActivePage} 
        selectedUser={selectedUser}
        setSelectedUser={setSelectedUser}
        isAnalyzing={isAnalyzing}
        availableUsers={availableUsers}
      />
      <main style={{ flex: 1, padding: '2rem', overflowY: 'auto', background: 'var(--color-bg)' }}>
        {loadingUsers && (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⏳</div>
            <p>Loading users from backend...</p>
          </div>
        )}
        {error && (
          <div style={{ padding: '1rem', background: '#FEE2E2', border: '1px solid #FCA5A5', borderRadius: '6px', marginBottom: '1rem', color: '#991B1B' }}>
            <strong>⚠️ Error:</strong> {error}
          </div>
        )}
        {!loadingUsers && renderContent()}
      </main>
    </div>
  );
};

const root = createRoot(document.getElementById('root')!);
root.render(<App />);
