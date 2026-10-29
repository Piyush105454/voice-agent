-- Guru Line schema. Source: database-design.md §2.
-- Runs on plain Postgres 16 (local) and Supabase. Supabase-only statements are guarded.
-- Additions vs. the design doc are marked "ADDITIVE".

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
  about text,                            -- ADDITIVE: who they are in their words (college student, working, job seeker…)
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
  consent_id uuid references consents(id) on delete set null,
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
  channel text default 'phone',          -- phone | simulator | web (Sarvam browser call, ADDITIVE)
  bolna_call_id text,
  topic_id text references topics(id),   -- ADDITIVE: the topic chosen for this session
  mode text default 'maths',             -- ADDITIVE: maths | english | topic
  goal_id uuid,                          -- ADDITIVE: goals(id); FK added after goals exists
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
  superseded_by uuid references memory_facts(id) on delete set null
);

-- ---------- safety, audit, evals ----------
-- ON DELETE SET NULL (ADDITIVE): a guardian "delete everything" must succeed, while an
-- anonymised record that a safety event happened (and the teacher was told) is retained.
create table safety_events (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete set null,
  session_id uuid references sessions(id) on delete set null,
  created_at timestamptz default now(), teacher_notified boolean default false, resolved boolean default false
);
create table audit_log (
  id bigserial primary key, actor text, action text, entity text, entity_id text,
  created_at timestamptz default now()
);
create table eval_runs (
  id uuid primary key default gen_random_uuid(), created_at timestamptz default now(),
  n_students int, tag_accuracy real, false_positive_rate real, avg_hints real, notes text,
  report jsonb                                           -- ADDITIVE: full eval_report.json
);
create table eval_cases (
  id uuid primary key default gen_random_uuid(), run_id uuid references eval_runs(id) on delete cascade,
  target_misconception text, predicted_misconception text, correct boolean, hints_to_solve int
);

-- ---------- ADDITIVE: goal-driven coaching (English speaking, any topic, maths) ----------
-- A student's own aim ("become an AI engineer", "speak English confidently") and the plan made for it.
create table goals (
  id uuid primary key default gen_random_uuid(),
  student_id uuid references students(id) on delete cascade,
  mode text not null check (mode in ('maths','english','topic')),
  aim text not null,
  level text,                            -- self-described starting level
  minutes_per_day int default 10,
  plan jsonb,                            -- {"summary","weeks":[{"week","focus","milestone","practice":[]}]}
  status text default 'active' check (status in ('active','done','dropped')),
  created_at timestamptz default now()
);
-- End-of-session evaluation: what improved, what to work on next (shown to student, teacher, parent).
create table session_reviews (
  session_id uuid primary key references sessions(id) on delete cascade,
  student_id uuid references students(id) on delete cascade,
  goal_id uuid references goals(id) on delete set null,
  mode text,
  summary text,
  strengths jsonb default '[]',
  improvements jsonb default '[]',       -- the "improvement points"
  next_steps jsonb default '[]',
  quiz_correct int, quiz_total int,
  created_at timestamptz default now()
);
-- Skill scores over time (0-10) -> day / week / month progress. skill = 'english.fluency', 'topic.understanding', ...
create table skill_scores (
  id bigserial primary key,
  student_id uuid references students(id) on delete cascade,
  session_id uuid references sessions(id) on delete cascade,
  goal_id uuid references goals(id) on delete set null,
  skill text not null,
  score real not null check (score between 0 and 10),
  source text not null default 'llm' check (source in ('llm','self_report','quiz','model')),
  created_at timestamptz default now()
);
create index on goals(student_id, mode, status);
alter table sessions add constraint sessions_goal_fk foreign key (goal_id) references goals(id) on delete set null;
create index on skill_scores(student_id, skill, created_at);

-- ---------- ADDITIVE: history for "over time" charts ----------
-- kind='mastery' -> key=topic_id ; kind='misconception' -> key=misconception_id ; value 0..1
create table learning_snapshots (
  id bigserial primary key,
  student_id uuid references students(id) on delete cascade,
  session_id uuid references sessions(id) on delete cascade,
  kind text not null check (kind in ('mastery','misconception')),
  key text not null,
  value real not null,
  created_at timestamptz default now()
);

-- ---------- realtime feed for the dashboard ----------
create table live_events (
  id bigserial primary key, student_id uuid, kind text, payload jsonb,
  created_at timestamptz default now()
);

create index on attempts(session_id); create index on sessions(student_id, started_at desc);
create unique index on sessions(bolna_call_id) where bolna_call_id is not null;  -- ADDITIVE: idempotent webhooks
create index on memory_facts(student_id, kind);
create index on live_events(student_id, id desc);
create index on learning_snapshots(student_id, kind, created_at);

-- ADDITIVE: NOTIFY for the SSE fallback when Supabase Realtime is not configured.
create or replace function live_events_notify() returns trigger language plpgsql as $$
begin
  perform pg_notify('live_events', row_to_json(new)::text);
  return new;
end $$;
create trigger live_events_notify_trg after insert on live_events
  for each row execute function live_events_notify();

-- ---------- Supabase-only (guarded) ----------
do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    execute 'alter publication supabase_realtime add table live_events';
  end if;
end $$;

do $$
begin
  if exists (select 1 from pg_namespace where nspname = 'auth') then
    execute 'alter table students enable row level security';
    execute 'alter table sessions enable row level security';
    execute 'alter table attempts enable row level security';
    -- Teachers see only students in their classes (backend uses the service role, bypassing RLS).
    execute $p$create policy teacher_reads_own_students on students for select
      using (class_id in (select id from classes where teacher_id = auth.uid()))$p$;
    -- Realtime: the browser (anon key) may read live_events only. Payloads hold IDs + learning
    -- tags, never names or phone numbers. Every other table stays closed to anon.
    execute 'alter table live_events enable row level security';
    execute $p$create policy anon_reads_live_events on live_events for select to anon using (true)$p$;
  end if;
end $$;
