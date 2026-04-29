export interface PnlPoint { timestamp: string; pnl: number; }
export interface CandidateVolumePoint { timestamp: string; candidates: number; executable: number; }
export interface BlockerFrequencyPoint { blocker: string; count: number; }
export interface StrategyHitRatePoint { strategy: string; trades: number; wins: number; losses: number; hitRate: number; }
