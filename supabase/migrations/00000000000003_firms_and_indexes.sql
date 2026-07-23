-- Per-firm access model: every attorney belongs to a firm, every case
-- belongs to a firm. firm_members links Supabase Auth users to firms;
-- application-level queries in api/ filter by firm_id (RLS stays
-- default-deny for anon/authenticated per migration 00000000000002 since
-- only the service-role-backed api/ touches this data today).
create table firms (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    created_at timestamptz not null default now()
);

create table firm_members (
    id uuid primary key default gen_random_uuid(),
    firm_id uuid not null references firms(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    created_at timestamptz not null default now(),
    unique (firm_id, user_id)
);

alter table cases add column firm_id uuid references firms(id);
create index cases_firm_id_idx on cases (firm_id);

alter table firms enable row level security;
alter table firm_members enable row level security;

-- ponytail: real Supabase Auth (login, JWT verification, firm_members
-- lookup) isn't wired into api/ yet — building that before the ingest
-- pipeline even works would be scope creep this early. Until then, api/
-- defaults new cases to this single dev firm. Upgrade path: add auth
-- middleware that resolves the caller's firm_id from their JWT via
-- firm_members, drop the default, make cases.firm_id required in the API
-- layer (it's already NOT NULL-eligible at the DB level once real data
-- exists — left nullable here only because it's set explicitly below).
insert into firms (id, name) values
    ('00000000-0000-0000-0000-000000000001', 'Dev Firm (placeholder until auth exists)');

-- fill in two FK indexes the performance advisor flagged as missing
create index chunks_document_id_idx on chunks (document_id);
create index chronology_entries_source_document_id_idx
    on chronology_entries (source_document_id);
