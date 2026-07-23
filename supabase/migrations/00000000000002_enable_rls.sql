-- Only api/ (using the Supabase service_role key, which bypasses RLS) talks
-- to this database today; web/ never calls Supabase directly per
-- docs/architecture.md. So enabling RLS with no policies is correct as-is:
-- it default-denies the anon/authenticated roles Supabase client libraries
-- use, closing the "RLS Disabled in Public" advisory, while api/ is
-- unaffected. Add real per-firm policies here if web/ ever gets direct
-- Supabase access instead of going through api/.
alter table cases enable row level security;
alter table documents enable row level security;
alter table chunks enable row level security;
alter table chronology_entries enable row level security;
alter table flags enable row level security;
