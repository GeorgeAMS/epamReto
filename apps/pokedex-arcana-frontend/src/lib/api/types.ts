// Tipos del backend FastAPI Pokédex Arcana
export type PokemonType =
  | "normal" | "fire" | "water" | "electric" | "grass" | "ice"
  | "fighting" | "poison" | "ground" | "flying" | "psychic" | "bug"
  | "rock" | "ghost" | "dragon" | "dark" | "steel" | "fairy";

export interface PokemonStats {
  hp: number; attack: number; defense: number;
  special_attack: number; special_defense: number; speed: number;
}

export interface Pokemon {
  id: number;
  name: string;
  types: PokemonType[];
  generation?: number;
  sprite?: string;
  artwork?: string;
  stats?: PokemonStats;
  height?: number;
  weight?: number;
  abilities?: string[];
}

export interface PokemonListResponse {
  pokemon?: Pokemon[];
  results?: Pokemon[];
  items?: Pokemon[];
  total?: number;
}

export interface ChatSource {
  title?: string;
  url?: string;
  snippet?: string;
  source?: string;
}

export type Confidence = "verified" | "partial" | "contradiction" | "unknown";

export interface DamageData {
  attacker?: string;
  defender?: string;
  move?: string;
  damage?: number;
  damage_range?: [number, number];
  percent?: number;
  percent_range?: [number, number];
  type_effectiveness?: number;
  is_critical?: boolean;
  is_stab?: boolean;
  weather?: string;
  notes?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  intent?: string;
  agent?: string;
  sources?: ChatSource[];
  confidence?: Confidence;
  damage?: DamageData;
  data?: Record<string, unknown>;
  createdAt: number;
  streaming?: boolean;
  error?: string;
}

export interface StreamEvent {
  type: "intent" | "agent" | "token" | "delta" | "sources" | "confidence" | "damage" | "data" | "done" | "error";
  intent?: string;
  agent?: string;
  token?: string;
  delta?: string;
  text?: string;
  content?: string;
  sources?: ChatSource[];
  confidence?: Confidence;
  damage?: DamageData;
  data?: Record<string, unknown>;
  message?: string;
}
