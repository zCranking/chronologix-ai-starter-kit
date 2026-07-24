-- Phase 3: demand letter drafts generated from a signed-off chronology.
-- A draft is never a finished/sent artifact -- it always requires attorney
-- review and their own damages/demand-amount input before it leaves draft
-- status. Stored (not just returned) so an attorney can revise across
-- sessions and so regeneration doesn't lose prior edits.
create table demand_letters (
    id uuid primary key default gen_random_uuid(),
    case_id uuid not null references cases(id) on delete cascade,
    body text not null,
    version int not null default 1,
    edited_by_attorney boolean not null default false,
    created_at timestamptz not null default now()
);

alter table demand_letters enable row level security;
create index demand_letters_case_id_idx on demand_letters (case_id);
