-- Drops every Guru Line table (used by reset-demo). Safe on Supabase: does not touch the public schema itself.
drop table if exists
  skill_scores, session_reviews, goals, live_events, learning_snapshots, eval_cases, eval_runs, audit_log, safety_events,
  memory_facts, summaries, plan_items, plans, confidence_logs, attempts, sessions,
  student_misconceptions, mastery, questions, misconception_types, topic_prereqs, topics,
  data_sources, consents, guardians, students, classes, teachers
cascade;
drop function if exists live_events_notify() cascade;
