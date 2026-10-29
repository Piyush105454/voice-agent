# database-design.md — Guru Line (Postgres + FalkorDB graph memory)

Two stores, two jobs:

| Store | Job |
|---|---|
| **Supabase Postgres** | Source of truth: people, consent, sessions, attempts, plans, summaries, audit. Realtime feed for the dashboard. |
| **FalkorDB (graph)** | Learning memory: topics, prerequisites, misconceptions, mastery, strategies. Answers "why is the student failing X?" in one query. |

Rule: **Postgres is truth, the graph is a derived, rebuildable index of learning state.** A rebuild script can recreate the graph from Postgres at any time.

---

## 1. Entity overview

```
Teacher ─< Class >─ Student >─ Guardian
                       │
        ┌──────────────┼───────────────────────┐
     Session ─< Attempt >─ Question >─ Topic     │
        │                      │                 │
   ConfidenceLog        MisconceptionType     Mastery (student x topic)
        │                                        │
     Summary                         StudentMisconception
                       Plan ─< PlanItem
        MemoryFact (provenance)    DataSource + Consent
        SafetyEvent   AuditLog   EvalRun ─< EvalCase
```

---

## 2. Postgres schema (`sql/schema.sql`)

```sql
create extension if not exists "pgcrypto";

-- ---------- people ----------
create table teachers (
  id uuid primary key default gen_random_uuid(),
  name text not null, email text unique, created_at timestamptz default now()
);

create table classes (
  id uuid primary key default gen_random_uuid(),
  teacher_id uuid references teachers(id) on delete set null,
  name text not null, grade int, subject text default 'Mathematics'
);

create table students (
  id uuid primary key default gen_random_uuid(),
  class_id uuid references classes(id) on delete set null,
  first_name text not null,
  phone_e164 text,                       -- store encrypted at rest if possible
  language text default 'hi-en',         -- hi | en | hi-en
  grade int,
  is_minor boolean default true,
  call_window_start time default '09:00',
  call_window_end   time default '19:00',
  active boolean default true,
  created_at timestamptz default now()
);

create table guardians (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  name text, phone_e164 text, preferred_language text default 'hi'
);

-- ---------- consent & privacy ----------
create table consents (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  given_by text not null check (given_by in ('guardian','student_adult')),
  purpose text not null,                 -- 'voice_tutoring','recording','teacher_sharing'
  granted boolean not null default true,
  granted_at timestamptz default now(),
  revoked_at timestamptz
);

create table data_sources (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  kind text not null check (kind in
    ('call_transcript','grading_result','teacher_note','homework_photo','parent_goal','whatsapp_optin')),
  consent_id uuid references consents(id),
  purpose text not null,
  created_at timestamptz default now()
);

-- ---------- curriculum ----------
create table topics (
  id text primary key,                   -- e.g. 'alg_linear_eq'
  subject text not null default 'Mathematics',
  name text not null, grade_min int, grade_max int
);

create table topic_prereqs (
  prereq_id text references topics(id),
  topic_id  text references topics(id),
  primary key (prereq_id, topic_id)
);

create table misconception_types (
  id text primary key,                   -- 'adds_instead_of_inverse'
  topic_id text references topics(id),
  name text not null, description text, example text
);

create table questions (
  id text primary key,                   -- 'q_017'
  topic_id text references topics(id) not null,
  text text not null,
  answer text not null,
  difficulty real default 0.5,           -- 0..1
  wrong_answer_map jsonb default '{}'    -- {"17":"adds_instead_of_inverse"}
);

-- ---------- learning state ----------
create table mastery (
  student_id uuid references students(id) on delete cascade,
  topic_id text references topics(id),
  p_known real not null default 0.3,
  stability_days real not null default 3,
  attempts int default 0,
  updated_at timestamptz default now(),
  primary key (student_id, topic_id)
);

create table student_misconceptions (
  student_id uuid references students(id) on delete cascade,
  misconception_id text references misconception_types(id),
  strength real not null default 0.3,    -- 0..1
  first_seen timestamptz default now(), last_seen timestamptz default now(),
  evidence_n int default 1,
  primary key (student_id, misconception_id)
);

-- ---------- sessions ----------
create table sessions (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  channel text default 'phone',          -- phone | simulator
  bolna_call_id text,
  started_at timestamptz default now(), ended_at timestamptz,
  transcript text,
  status text default 'active'
);

create table attempts (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  question_id text references questions(id),
  student_answer text, correct boolean,
  misconception_id text references misconception_types(id),
  hint_level int default 0,
  created_at timestamptz default now()
);

create table confidence_logs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  topic_id text references topics(id),
  phase text check (phase in ('before','after')),
  value int check (value between 1 and 10),
  created_at timestamptz default now()
);

-- ---------- plans & summaries ----------
create table plans (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  created_at timestamptz default now(), valid_from date, valid_to date
);
create table plan_items (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid references plans(id) on delete cascade,
  day int, topic_id text references topics(id),
  type text check (type in ('guided','independent','review')),
  n_questions int default 3, done boolean default false
);
create table summaries (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  audience text check (audience in ('teacher','parent')),
  language text, body text, created_at timestamptz default now()
);

-- ---------- memory facts (explainable memory) ----------
create table memory_facts (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  kind text check (kind in ('misconception','strategy','goal','note')),
  content jsonb not null,
  confidence real default 0.5,
  source_session uuid references sessions(id) on delete set null,
  source_kind text default 'call_transcript',
  created_at timestamptz default now(),
  superseded_by uuid references memory_facts(id)
);

-- ---------- safety, audit, evals ----------
create table safety_events (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id), session_id uuid references sessions(id),
  created_at timestamptz default now(), teacher_notified boolean default false, resolved boolean default false
);
create table audit_log (
  id bigserial primary key, actor text, action text, entity text, entity_id text,
  created_at timestamptz default now()
);
create table eval_runs (
  id uuid primary key default gen_random_uuid(), created_at timestamptz default now(),
  n_students int, tag_accuracy real, false_positive_rate real, avg_hints real, notes text
);
create table eval_cases (
  id uuid primary key default gen_random_uuid(), run_id uuid references eval_runs(id) on delete cascade,
  target_misconception text, predicted_misconception text, correct boolean, hints_to_solve int
);

-- ---------- realtime feed for the dashboard ----------
create table live_events (
  id bigserial primary key, student_id uuid, kind text, payload jsonb,
  created_at timestamptz default now()
);
alter publication supabase_realtime add table live_events;

create index on attempts(session_id); create index on sessions(student_id, started_at desc);
create index on memory_facts(student_id, kind);
```

### Row-level security (Supabase)
```sql
alter table students enable row level security;
alter table sessions enable row level security;
alter table attempts enable row level security;
-- Teachers see only students in their classes:
create policy teacher_reads_own_students on students for select
  using (class_id in (select id from classes where teacher_id = auth.uid()));
-- Backend uses the service key (bypasses RLS). Never expose the service key in the browser.
```

---

## 3. Seed data (`sql/seed.sql`, abridged)

```sql
insert into topics(id,name,grade_min,grade_max) values
 ('num_negatives','Negative numbers',6,8),
 ('alg_expressions','Variables and expressions',6,8),
 ('alg_linear_eq','Linear equations',7,9),
 ('alg_distribution','Distributive property',7,9),
 ('alg_multistep','Multi-step equations',8,10);

insert into topic_prereqs values
 ('num_negatives','alg_expressions'),('alg_expressions','alg_linear_eq'),
 ('num_negatives','alg_linear_eq'),('alg_linear_eq','alg_multistep'),('alg_distribution','alg_multistep');

insert into misconception_types(id,topic_id,name,example) values
 ('adds_instead_of_inverse','alg_linear_eq','Adds instead of using inverse','x+5=12 -> 17'),
 ('sign_not_flipped','alg_linear_eq','Sign not flipped when moving a term','x-3=7 -> 4'),
 ('coefficient_ignored','alg_linear_eq','Ignores coefficient','3x=12 -> 12'),
 ('neg_number_confusion','num_negatives','Negative number rules','-2-3 -> -1'),
 ('distributes_partially','alg_distribution','Partial distribution','2(x+3) -> 2x+3'),
 ('equals_as_answer','alg_expressions','Treats = as "answer comes"','3+4=7+2');

insert into questions(id,topic_id,text,answer,difficulty,wrong_answer_map) values
 ('q_017','alg_linear_eq','x + 5 = 12, x kya hoga?','7',0.3,'{"17":"adds_instead_of_inverse"}'),
 ('q_018','alg_linear_eq','x - 3 = 7, x kya hoga?','10',0.4,'{"4":"sign_not_flipped"}'),
 ('q_019','alg_linear_eq','3x = 12, x kya hoga?','4',0.4,'{"12":"coefficient_ignored","9":"sign_not_flipped"}');
-- generate the remaining ~40 questions with the LLM, then review manually.
-- Also insert 5 demo students (consented) + one "Rahul" with a clear arc for the live demo.
```

---

## 4. FalkorDB graph schema

**Graph name:** `guruline` (one graph; every node/edge keyed by IDs from Postgres).

### Nodes
| Label | Properties |
|---|---|
| `Student` | `id`, `name`, `grade` |
| `Topic` | `id`, `name`, `subject` |
| `Misconception` | `id`, `name`, `topic_id` |
| `Strategy` | `id` (`step_by_step`, `analogy`, `worked_example`, `visual`, `repetition`) |
| `Goal` | `id`, `text` |
| `Session` | `id`, `started` |

### Relationships
| Edge | From → To | Properties |
|---|---|---|
| `PREREQUISITE_OF` | Topic → Topic | — |
| `AFFECTS` | Misconception → Topic | — |
| `MASTERY` | Student → Topic | `p`, `stability`, `updated` |
| `HOLDS` | Student → Misconception | `strength`, `first_seen`, `last_seen`, `n` |
| `RESPONDS_WELL_TO` | Student → Strategy | `evidence_n`, `last_seen` |
| `HAS_GOAL` | Student → Goal | `created` |
| `HAD_SESSION` | Student → Session | — |
| `PRACTISED` | Session → Topic | `before_conf`, `after_conf`, `accuracy` |

### Setup (run once)
```cypher
CREATE INDEX FOR (s:Student) ON (s.id);
CREATE INDEX FOR (t:Topic) ON (t.id);
CREATE INDEX FOR (m:Misconception) ON (m.id);
CREATE INDEX FOR (st:Strategy) ON (st.id);
```

### Build from Postgres (`api/graph_seed.py`)
```python
from graph import q
import db

def rebuild_graph():
    q("MATCH (n) DETACH DELETE n")
    for t in db.all_topics():
        q("MERGE (:Topic {id:$id}) SET ...", {"id": t["id"], "name": t["name"]})  # set name, subject
    for p in db.all_prereqs():
        q("MATCH (a:Topic {id:$a}),(b:Topic {id:$b}) MERGE (a)-[:PREREQUISITE_OF]->(b)",
          {"a": p["prereq_id"], "b": p["topic_id"]})
    for m in db.all_misconceptions():
        q("""MERGE (x:Misconception {id:$id}) SET x.name=$name
             WITH x MATCH (t:Topic {id:$tid}) MERGE (x)-[:AFFECTS]->(t)""",
          {"id": m["id"], "name": m["name"], "tid": m["topic_id"]})
    for s in db.all_students():
        q("MERGE (s:Student {id:$id}) SET s.name=$name", {"id": s["id"], "name": s["first_name"]})
    for r in db.all_mastery():
        q("""MATCH (s:Student {id:$sid}),(t:Topic {id:$tid})
             MERGE (s)-[m:MASTERY]->(t) SET m.p=$p, m.stability=$st, m.updated=timestamp()""",
          {"sid": r["student_id"], "tid": r["topic_id"], "p": r["p_known"], "st": r["stability_days"]})
    for r in db.all_student_misconceptions():
        q("""MATCH (s:Student {id:$sid}),(m:Misconception {id:$mid})
             MERGE (s)-[h:HOLDS]->(m) SET h.strength=$str, h.n=$n""",
          {"sid": r["student_id"], "mid": r["misconception_id"], "str": r["strength"], "n": r["evidence_n"]})
```

---

## 5. Key queries

```cypher
// 1. Root-cause: weakest prerequisite for a failing topic
MATCH (p:Topic)-[:PREREQUISITE_OF*1..3]->(t:Topic {id:$topic})
OPTIONAL MATCH (s:Student {id:$sid})-[pm:MASTERY]->(p)
WITH p, coalesce(pm.p,0.3) AS m WHERE m < 0.5
RETURN p.name, m ORDER BY m ASC LIMIT 1;

// 2. Active misconceptions for today's topic
MATCH (s:Student {id:$sid})-[h:HOLDS]->(x:Misconception)-[:AFFECTS]->(t:Topic {id:$topic})
WHERE h.strength > 0.3 RETURN x.name, h.strength ORDER BY h.strength DESC;

// 3. Best teaching strategy so far
MATCH (s:Student {id:$sid})-[r:RESPONDS_WELL_TO]->(st:Strategy)
RETURN st.id ORDER BY r.evidence_n DESC LIMIT 1;

// 4. Dashboard subgraph (student + 2 hops)
MATCH (s:Student {id:$sid})-[r1]->(a)
OPTIONAL MATCH (a)-[r2]->(b)
RETURN s, r1, a, r2, b LIMIT 80;

// 5. Class heat: most common misconceptions in a class
MATCH (s:Student)-[h:HOLDS]->(x:Misconception) WHERE s.id IN $student_ids AND h.strength>0.4
RETURN x.name, count(s) AS students ORDER BY students DESC;
```

---

## 6. Memory quality rules

1. **Provenance:** every fact in `memory_facts` links to a session; graph edges can be traced back.
2. **Confidence:** LLM-extracted facts carry confidence 0-1; below 0.4 they are ignored for teaching decisions.
3. **Contradictions:** newer evidence supersedes (`superseded_by`); never silently delete.
4. **Decay:** mastery decays with `exp(-dt/stability)`; stability increases after successful reviews.
5. **Forbidden memory:** no mood, personality type, health, family details, or anything outside learning. The extraction prompt and a post-filter both enforce this.
6. **Student/guardian control:** `GET /students/{id}/memory` (export) and `DELETE` (removes Postgres rows + graph node) must work and be shown in the UI privacy center.

## 7. Privacy and retention

| Data | Retention | Notes |
|---|---|---|
| Call audio | Do not store unless needed; if stored, 30 days | Ask Bolna config for recording settings |
| Transcripts | 90 days, then keep only extracted facts | Needed for memory provenance |
| Mastery / misconceptions | While the student is active | Deleted on request |
| Phone numbers | Encrypt at rest; mask in UI (`+91 98•••• ••21`) | Never in the graph |
| Audit log | 1 year | Who viewed which student |

Dashboard shows teachers only their class. Never show one student's data to another. Never rank students against each other.

## 8. Live events contract (dashboard realtime)

`live_events.kind` ∈ `session_started | attempt | confidence | misconception_detected | session_ended | safety`
```json
{ "kind":"attempt","payload":{"correct":false,"misconception":"adds_instead_of_inverse","mastery":0.34,"topic":"alg_linear_eq"} }
```
The web app subscribes to `live_events` filtered by `student_id` and animates the matching graph node.

## 9. Backups and demo safety

- Daily `pg_dump`; keep a `demo_snapshot.sql` so the demo DB can be reset in one command.
- `rebuild_graph()` must run in < 5 s so you can reset the graph before every demo.
- Keep a seeded student "Rahul" with a clean arc: mastery 0.30 → 0.62, confidence 3 → 6, misconception strength 0.8 → 0.35.
