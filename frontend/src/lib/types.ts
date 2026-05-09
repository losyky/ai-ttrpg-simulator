export interface LLMConfig {
  api_key: string;
  model: string;
  base_url: string;
}

export interface CharacterSummary {
  name: string;
  ancestry: string;
  character_class: string;
  level: number;
  hp: number;
  max_hp: number;
  conditions: string[];
}

export type GamePhase = "exploration" | "combat" | "social" | "downtime";

export interface SessionState {
  session_id: string;
  system_id: string;
  label: string;
  created_at: string;
  phase: GamePhase;
  round_number: number;
  player: CharacterSummary | null;
  teammates: CharacterSummary[];
  world_summary: string;
  recent_events: string[];
}

export interface SessionListItem {
  session_id: string;
  system_id: string;
  label: string;
  created_at: string;
  phase: string;
  round_number: number;
  player_name: string;
  player_class: string;
  player_level: number;
  teammate_count: number;
  teammate_names: string[];
  message_count: number;
}

export interface DiceResult {
  expression: string;
  rolls: number[];
  total: number;
  detail: string;
  success_level?: string; // "critical_success" | "success" | "failure" | "critical_failure"
  dc?: number;
  label?: string;
  // Daggerheart duality dice
  duality_outcome?: string; // "with_hope" | "with_fear" | "critical_success"
  hope_die?: number;
  fear_die?: number;
  // SWADE raises
  raises?: number;
  // Flexible extras
  system_info?: Record<string, unknown>;
}

export interface ChoiceOption {
  id: string;
  label: string;
  description?: string;
  icon?: string;
}

export interface InteractiveElement {
  element_type: "choices" | "dice_request" | "input_prompt" | "duality_dice_request" | "token_update";
  id: string;
  prompt: string;
  // choices
  options?: ChoiceOption[];
  allow_multiple?: boolean;
  // dice_request / duality_dice_request
  expression?: string;
  dc?: number;
  skill_name?: string;
  modifier?: number;
  // duality_dice_request (Daggerheart)
  trait_name?: string;
  experience_bonus?: boolean;
  // token_update (Daggerheart Hope/Fear)
  token_type?: string; // "hope" | "fear"
  token_change?: number;
  token_total?: number;
  token_reason?: string;
  // input_prompt
  placeholder?: string;
  input_type?: string;
  // resolved state — persisted so controls survive tab switches & save/load
  resolved?: boolean;
  resolved_value?: string;   // selected choice label, dice result text, or input value
  resolved_dice?: DiceResult; // full dice result for dice_request / duality_dice_request
}

export interface ChatResponseChunk {
  type: "text" | "dice" | "interactive" | "state_update" | "error" | "done" | "thinking";
  content: string;
  dice: DiceResult | null;
  state: SessionState | null;
  interactive: InteractiveElement | null;
  thinking_step?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "narrator" | "referee" | "teammate" | "system";
  content: string;
  dice?: DiceResult;
  interactive?: InteractiveElement[];
  timestamp: number;
}

export interface DocumentInfo {
  doc_id: string;
  filename: string;
  doc_type: string;
  chunk_count: number;
}

// ── Character Builder Types ──

export interface PF2eAncestry {
  id: string;
  name: string;
  slug: string;
  hp: number;
  size: string;
  speed: number;
  vision: string;
  boosts: Record<string, { value: string[] }>;
  flaws: Record<string, { value: string[] }>;
  languages: string[];
  traits: string[];
  description: string;
  name_cn: string;
  description_cn: string;
  display_name?: string;
  description_rendered?: string;
}

export interface PF2eHeritage {
  id: string;
  name: string;
  slug: string;
  ancestry_slug: string | null;
  traits: string[];
  rules_summary: string;
  description: string;
  name_cn: string;
  description_cn: string;
  display_name?: string;
}

export interface PF2eBackground {
  id: string;
  name: string;
  slug: string;
  boosts: Record<string, { value: string[] }>;
  trained_skills: string[];
  lore: string[];
  granted_feat_names: string[];
  description: string;
  name_cn: string;
  description_cn: string;
  display_name?: string;
  description_rendered?: string;
}

export interface PF2eClass {
  id: string;
  name: string;
  slug: string;
  hp_per_level: number;
  key_ability: string[];
  perception_rank: number;
  saves: Record<string, number>;
  attacks: Record<string, unknown>;
  defenses: Record<string, unknown>;
  trained_skills: string[];
  additional_skill_count: number;
  spellcasting: number;
  ancestry_feat_levels: number[];
  class_feat_levels: number[];
  general_feat_levels: number[];
  skill_feat_levels: number[];
  skill_increase_levels: number[];
  class_features: { name: string; level: number; uuid: string }[];
  description: string;
  name_cn: string;
  description_cn: string;
  display_name?: string;
  description_rendered?: string;
}

export interface PF2eFeat {
  id: string;
  name: string;
  slug: string;
  level: number;
  category: string;
  action_type: string;
  traits: string[];
  prerequisites: string[];
  class_slug: string;
  ancestry_slug: string;
  description: string;
  name_cn: string;
  description_cn: string;
  display_name?: string;
}

export interface PF2eSpell {
  id: string;
  name: string;
  slug: string;
  rank: number;
  traditions: string[];
  traits: string[];
  action_cost: string;
  range: string;
  area: string;
  target: string;
  duration: string;
  defense: string;
  description: string;
  name_cn: string;
  description_cn: string;
  display_name?: string;
}

export interface PF2eEquipment {
  id: string;
  name: string;
  slug: string;
  item_type: string;
  category: string;
  price_cp: number;
  bulk: string;
  traits: string[];
  damage: string;
  ac_bonus: number;
  dex_cap: number;
  description: string;
  name_cn: string;
  description_cn: string;
  display_name?: string;
}

export interface PF2eSkill {
  slug: string;
  name: string;
  name_cn: string;
  attribute: string;
}

export interface CharacterBuild {
  level: number;
  name: string;
  ancestry: { slug: string; name: string; boosts: Record<string, string>; flaws: Record<string, string> } | null;
  heritage: { slug: string; name: string } | null;
  background: { slug: string; name: string; boosts: Record<string, string> } | null;
  class_: { slug: string; name: string; keyAbility: string } | null;
  freeBoosts: string[];
  levelBoosts: Record<number, string[]>;
  voluntaryFlaws: string[];
  trainedSkills: string[];
  skillIncreases: Record<number, string>;
  feats: { slotType: string; level: number; slug: string; name: string }[];
  spells: { rank: number; slug: string; name: string }[];
  equipment: { slug: string; name: string; quantity: number }[];
  details: { deity?: string; gender?: string; age?: string; biography?: string };
}

export interface AbilityScores {
  str: number;
  dex: number;
  con: number;
  int: number;
  wis: number;
  cha: number;
}
