create table evidence (
    id uuid primary key default gen_random_uuid(),
    case_id uuid not null references cases(id) on delete cascade,
    storage_path text not null,
    original_filename text not null,
    media_type text not null check (media_type in ('video', 'audio')),
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'transcribed', 'failed')),
    duration_seconds numeric,
    -- Phase 2 requires heavier review by default (PLANNING.md): a
    -- transcript is not treated as chronology-ready until an attorney
    -- explicitly confirms it, unlike text documents in Phase 1.
    confirmed_by_attorney boolean not null default false,
    uploaded_at timestamptz not null default now()
);

create table evidence_segments (
    id uuid primary key default gen_random_uuid(),
    evidence_id uuid not null references evidence(id) on delete cascade,
    start_time_seconds numeric not null,
    end_time_seconds numeric not null,
    speaker_label text,
    content text not null,
    embedding vector(1024),
    created_at timestamptz not null default now()
);

-- chronology_entries can now cite evidence (timestamp) as well as a
-- document (page) -- exactly one of the two must be set.
alter table chronology_entries alter column source_document_id drop not null;
alter table chronology_entries add column source_evidence_id uuid references evidence(id);
alter table chronology_entries add constraint chronology_entries_source_check
    check (
        (source_document_id is not null and source_evidence_id is null)
        or (source_document_id is null and source_evidence_id is not null)
    );

alter table evidence enable row level security;
alter table evidence_segments enable row level security;

create index evidence_case_id_idx on evidence (case_id);
create index evidence_segments_evidence_id_idx on evidence_segments (evidence_id);
create index evidence_segments_embedding_idx on evidence_segments
    using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index chronology_entries_source_evidence_id_idx on chronology_entries (source_evidence_id);
