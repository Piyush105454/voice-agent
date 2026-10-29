export type GraphNode = {
  id: string;
  label: string;
  kind: "student" | "topic" | "misconception" | "strategy"
    // coaching side (after any call): goal, skill (0-10), self-reported confidence, mistake pattern,
    // topic practised, next step, suggested resource, what works for this student
    | "goal" | "skill" | "confidence" | "pattern" | "practice" | "next" | "resource" | "works" | "challenge";
  score?: number;
  trend?: number;
  value?: number | null;
  detail?: string;
  mastery?: number | null;
  strength?: number;
  n?: number;
  x?: number;
  y?: number;
};
export type GraphLink = { source: string | GraphNode; target: string | GraphNode; kind: string; value?: number };
export type GraphData = { nodes: GraphNode[]; links: GraphLink[] };

export type Line = { speaker: "guru" | "student"; name: string; text: string };
export type Attempt = {
  question_id: string;
  question: string;
  student_answer: string;
  correct: boolean;
  misconception_id: string | null;
  misconception_name: string | null;
  hint_level: number;
  created_at: string;
};
export type Arc = {
  topic_id: string | null;
  mastery_before: number | null;
  mastery_after: number | null;
  misconception: string | null;
  misconception_name: string | null;
  mis_before: number | null;
  mis_after: number | null;
  conf_before?: number;
  conf_after?: number;
};
export type Feed = {
  id: string;
  student_id: string;
  first_name: string;
  topic: string | null;
  topic_id: string | null;
  channel: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  lines: Line[];
  attempts: Attempt[];
  confidence: { before?: number; after?: number };
  stats: { questions: number; correct_n: number; attempts_n: number; accuracy: number };
  plan: { day: number; topic: string; type: string; n_questions: number }[];
  arc: Arc;
  mode?: Mode | "open"; // "open" = phone call before the student picks a topic
  review?: Review | null;
};

export type Mode = "coach" | "maths" | "english" | "topic";
export type Resource = { kind: "book" | "quote" | "method"; title: string; by: string | null; why: string; created_at?: string };
export type LearnerProfile = {
  about?: string; motivation?: string; confidence_pattern?: string; recurring_mistakes?: string[];
  what_works?: string[]; watch_outs?: string[]; direction?: string; next_call_plan?: string; updated_at?: string;
  challenges?: string[]; solutions_tried?: string[]; goal_in_their_words?: string;
};
export type JournalDay = {
  session_id: string; started_at: string; channel: string; mode: Mode | "open" | null; topic_id: string | null;
  summary: string | null; strengths: string[] | null; improvements: string[] | null; next_steps: string[] | null;
  resources: Resource[];
};
export type Review = {
  summary: string | null;
  strengths: string[];
  improvements: string[];
  next_steps: string[];
  quiz_correct?: number | null;
  quiz_total?: number | null;
  mode?: Mode | "open"; // "open" = phone call before the student picks a topic
  created_at?: string;
  session_id?: string;
};
export type Goal = {
  id: string;
  mode: Mode;
  aim: string;
  status: "active" | "done" | "dropped";
  created_at: string;
  sessions: number;
  plan: { summary: string; weeks: { week: number; focus: string; milestone: string; practice: string[] }[] } | null;
};
export type SkillPoint = { bucket: string; skill: string; score: number; n: number };
export type Skills = { period: "day" | "week" | "month"; series: SkillPoint[]; reviews: Review[] };
export type CoachFeedback = { headline: string; points: string[]; focus_next: string; trend?: Record<string, number> };

export type TopicMastery = {
  topic_id: string;
  name: string;
  p_known: number;
  p_now: number;
  stability_days: number;
  next_review_days: number;
  attempts: number;
  updated_at: string;
};
export type MisconceptionRow = { id: string; name: string; strength: number; evidence_n: number; last_seen: string };
export type MemoryFact = {
  id: string;
  kind: "misconception" | "strategy" | "goal" | "note";
  content: { id?: string; text?: string; evidence?: string; type?: string; title?: string; direction?: string; language?: string };
  confidence: number;
  created_at: string;
  source_session: string | null;
  source_started_at: string | null;
};
export type SessionRow = {
  id: string;
  channel: string;
  topic_id: string | null;
  status: string;
  started_at: string;
  ended_at: string | null;
  summaries: { audience: string; language: string; body: string }[] | null;
};
export type Snapshot = { kind: "mastery" | "misconception"; key: string; value: number; created_at: string };
export type Overview = {
  id: string;
  first_name: string;
  language: string;
  grade: number;
  consented: boolean;
  topics: TopicMastery[];
  misconceptions: MisconceptionRow[];
  focus_topic: string;
  weak_prerequisite: { id: string; name: string; mastery: number } | null;
  memory: MemoryFact[];
  sessions: SessionRow[];
  snapshots: Snapshot[];
  goals?: Goal[];
  last_reviews?: (Review & { mode: Mode })[];
};
export type SessionPoint = {
  session_id: string;
  started_at: string;
  topic_id: string | null;
  accuracy: number | null;
  conf_before: number | null;
  conf_after: number | null;
};
export type SkillRow = { skill: string; label: string; score: number; trend: number; n: number; days_since: number };
export type NextStep = { kind: string; title: string; why: string; principle: string; priority: number };
export type Progress = {
  session_points: SessionPoint[];
  skills?: SkillRow[];
  self_confidence?: { value: number; trend: number; n: number } | null;
  next_steps?: NextStep[];
};
export type Student = { id: string; first_name: string; language: string; grade: number; consented: boolean };
export type LiveEvent = { id: number; student_id: string | null; kind: string; payload: Record<string, unknown>; created_at: string };
