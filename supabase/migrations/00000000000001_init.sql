create extension if not exists vector;
create extension if not exists pgcrypto;

create table cases (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    created_at timestamptz not null default now()
);

create table documents (
    id uuid primary key default gen_random_uuid(),
    case_id uuid not null references cases(id) on delete cascade,
    storage_path text not null,
    original_filename text not null,
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'processed', 'failed')),
    uploaded_at timestamptz not null default now()
);

-- embedding dim matches Voyage AI voyage-3 (1024 dims); change here and in
-- the embedding call together if the embedding model ever changes.
create table chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    page_number int,
    content text not null,
    embedding vector(1024),
    created_at timestamptz not null default now()
);

create table chronology_entries (
    id uuid primary key default gen_random_uuid(),
    case_id uuid not null references cases(id) on delete cascade,
    event_date date not null,
    summary text not null,
    source_document_id uuid not null references documents(id),
    source_location text not null,
    version int not null default 1,
    edited_by_attorney boolean not null default false,
    created_at timestamptz not null default now()
);

create table flags (
    id uuid primary key default gen_random_uuid(),
    case_id uuid not null references cases(id) on delete cascade,
    description text not null,
    related_entry_ids uuid[] not null default '{}',
    resolved boolean not null default false,
    created_at timestamptz not null default now()
);

create index chunks_embedding_idx on chunks
    using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index documents_case_id_idx on documents (case_id);
create index chronology_entries_case_date_idx
    on chronology_entries (case_id, event_date);
create index flags_case_id_idx on flags (case_id);
