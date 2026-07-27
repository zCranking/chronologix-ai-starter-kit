# Graph Report - .  (2026-07-26)

## Corpus Check
- Corpus is ~27,013 words - fits in a single context window. You may not need a graph.

## Summary
- 370 nodes · 641 edges · 42 communities (18 shown, 24 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 43 edges (avg confidence: 0.82)
- Token cost: 287,299 input · 0 output

## Community Hubs (Navigation)
- API Core & Endpoints
- Seed Demo & Endpoint Tests
- Web Package Dependencies
- TypeScript Config
- Chronology Generation
- LLM Client & Flag Detection
- Project Docs & Agent Roles
- Frontend Case Review UI
- Demand Letter Drafting
- Document Ingest Pipeline
- Date Extraction
- Evidence Processing Pipeline
- Transcription (Deepgram)
- Document Parsing
- Web Root Layout & Fonts
- MCP Postgres Example Server
- Dedup Key Bugfix
- JSON Fence Stripping Bugfix
- Defense-Side Scope Decision
- Sensitive Commit Guard Script
- Post-Edit Check Script
- Web AI Agent Rules
- Web ESLint Config
- Next.js Config
- PostCSS Config
- CORS Gotcha Note
- LiteLLM Abandoned
- Unstructured Lib Abandoned
- Wrong-Parent Commit Mistake
- Open Direction A
- API Package Metadata
- Case Mgmt Integrations (Blocked)
- Case Value Benchmarking (Deferred)
- Transcription Finetuning (Deferred)
- File Icon Asset
- Globe Icon Asset
- Next.js Logo Asset
- Vercel Logo Asset
- Window Icon Asset
- Web README Overview

## God Nodes (most connected - your core abstractions)
1. `main()` - 31 edges
2. `get_client()` - 29 edges
3. `build_chronology()` - 24 edges
4. `compilerOptions` - 16 edges
5. `_fake_db()` - 15 edges
6. `draft_demand_letter()` - 14 edges
7. `extract_dates()` - 13 edges
8. `process_evidence()` - 12 edges
9. `detect_flags()` - 12 edges
10. `process_document()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Unit tests are the floor, live verification is the proof` --semantically_similar_to--> `Retrospective — learnings from the build`  [INFERRED] [semantically similar]
  CLAUDE.md → docs/RETROSPECTIVE.md
- `Claude markdown-fenced JSON bug (strip_json_fence)` --semantically_similar_to--> `Claude markdown JSON fence bug (retrospective account)`  [INFERRED] [semantically similar]
  PLANNING.md → docs/RETROSPECTIVE.md
- `Chronology dedup key iterative fix (source,location,event_date)` --semantically_similar_to--> `Chronology dedup live-only bug (retrospective account)`  [INFERRED] [semantically similar]
  PLANNING.md → docs/RETROSPECTIVE.md
- `Unit tests are the floor, live verification is the proof` --conceptually_related_to--> `accuracy-verifier subagent`  [INFERRED]
  CLAUDE.md → .claude/agents/accuracy-verifier.md
- `Model-tier orchestration policy (Opus orchestrates, cheaper builder, mid-tier review, strongest model for accuracy)` --conceptually_related_to--> `accuracy-verifier subagent`  [INFERRED]
  CLAUDE.md → .claude/agents/accuracy-verifier.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Plan-build-review-verify workflow (ship skill + subagents)** — claude_skills_ship_skill, claude_agents_builder, claude_agents_code_reviewer, claude_agents_accuracy_verifier [EXTRACTED 1.00]
- **Speculative work deferred with explicit prerequisite/reason** — planning_transcription_finetuning_deferred, planning_case_value_benchmarking_deferred, planning_case_mgmt_integrations_blocked [INFERRED 0.85]
- **Modules subject to the LLM-call centralization rule** — docs_architecture_chronology_module, docs_architecture_flags_module, docs_architecture_llm_centralization_rule [INFERRED 0.85]

## Communities (42 total, 24 thin omitted)

### Community 0 - "API Core & Endpoints"
Cohesion: 0.07
Nodes (37): Settings, get_client(), Client, embed(), _get_client(), Client, CaseDetailResponse, CaseResponse (+29 more)

### Community 1 - "Seed Demo & Endpoint Tests"
Cohesion: 0.09
Nodes (35): main(), _pdf_bytes(), Client, Seed a rich, synthetic demo case so the app shows a complete workflow (documents, _seed_case(), _upload(), _wait_processed(), test_get_case_returns_404_when_not_found() (+27 more)

### Community 2 - "Web Package Dependencies"
Cohesion: 0.06
Nodes (32): eslint, eslint-config-next, next, react, react-dom, tailwindcss, @tailwindcss/postcss, @types/node (+24 more)

### Community 3 - "TypeScript Config"
Cohesion: 0.07
Nodes (28): dom, dom.iterable, esnext, **/*.mts, .next/dev/types/**/*.ts, next-env.d.ts, .next/types/**/*.ts, node_modules (+20 more)

### Community 4 - "Chronology Generation"
Cohesion: 0.16
Nodes (25): _attach_dates_and_sort(), build_chronology(), _build_row(), _entry_key(), _fetch_case_excerpts(), _format_excerpts(), _format_timestamp(), generate_chronology() (+17 more)

### Community 5 - "LLM Client & Flag Detection"
Cohesion: 0.15
Nodes (21): Anthropic, generate(), _get_client(), Claude (and other chat models) routinely wrap JSON output in a     markdown code, strip_json_fence(), detect_flags(), _format_entries(), generate_flags() (+13 more)

### Community 6 - "Project Docs & Agent Roles"
Cohesion: 0.16
Nodes (26): accuracy-verifier subagent, builder subagent, code-reviewer subagent, cost-auditor subagent, Chronologix AI project overview (root CLAUDE.md), Unit tests are the floor, live verification is the proof, Model-tier orchestration policy (Opus orchestrates, cheaper builder, mid-tier review, strongest model for accuracy), /ship skill workflow (plan-build-review-verify loop) (+18 more)

### Community 7 - "Frontend Case Review UI"
Cohesion: 0.19
Nodes (14): CASE_TYPE_STYLES, CaseTypeBadge(), api, Case, CASE_TYPE_LABELS, CaseDetail, CaseType, ChronologyEntry (+6 more)

### Community 8 - "Demand Letter Drafting"
Cohesion: 0.32
Nodes (14): draft_demand_letter(), _format_events(), generate_demand_letter(), _entries(), _fake_db(), _signed_off_case(), test_draft_demand_letter_increments_version_when_prior_draft_exists(), test_draft_demand_letter_prompts_with_events_and_inserts_version_1() (+6 more)

### Community 9 - "Document Ingest Pipeline"
Cohesion: 0.25
Nodes (11): chunk_text(), process_document(), test_chunk_text_preserves_none_page_number_for_docx(), test_chunk_text_skips_blank_pages(), test_chunk_text_splits_long_page_into_multiple_chunks_preserving_page_number(), _fake_db(), test_process_document_happy_path_inserts_chunks_and_marks_processed(), test_process_document_marks_failed_and_reraises_on_document_fetch_error() (+3 more)

### Community 10 - "Date Extraction"
Cohesion: 0.39
Nodes (10): extract_dates(), test_extract_dates_finds_abbreviated_month(), test_extract_dates_finds_iso_format(), test_extract_dates_finds_month_name_format(), test_extract_dates_finds_multiple_dates_in_order(), test_extract_dates_finds_us_slash_format(), test_extract_dates_orders_mixed_formats_by_position_in_text(), test_extract_dates_returns_empty_list_for_no_dates() (+2 more)

### Community 11 - "Evidence Processing Pipeline"
Cohesion: 0.42
Nodes (8): process_evidence(), _fake_db(), test_process_evidence_handles_utterance_with_no_speaker(), test_process_evidence_happy_path_inserts_segments_and_marks_transcribed(), test_process_evidence_marks_failed_and_reraises_on_evidence_fetch_error(), test_process_evidence_marks_failed_and_reraises_on_transcription_error(), test_process_evidence_skips_segment_insert_when_no_utterances(), test_process_evidence_stores_segments_with_null_embedding_when_embed_fails()

### Community 12 - "Transcription (Deepgram)"
Cohesion: 0.36
Nodes (7): _get_client(), transcribe(), _fake_utterance(), test_transcribe_accepts_custom_keyterms(), test_transcribe_returns_empty_list_when_no_utterances(), test_transcribe_returns_utterance_segments(), DeepgramClient

### Community 13 - "Document Parsing"
Cohesion: 0.42
Nodes (7): _extract_docx(), _extract_pdf(), extract_text(), test_extract_text_falls_back_to_ocr_when_page_has_no_text_layer(), test_extract_text_from_docx_with_real_text_layer(), test_extract_text_from_pdf_with_real_text_layer(), test_extract_text_raises_for_unsupported_extension()

### Community 14 - "Web Root Layout & Fonts"
Cohesion: 0.33
Nodes (4): inter, jetBrainsMono, metadata, spectral

### Community 15 - "MCP Postgres Example Server"
Cohesion: 0.50
Nodes (3): npx, _example_postgres, @modelcontextprotocol/server-postgres

## Knowledge Gaps
- **68 isolated node(s):** `npx`, `@modelcontextprotocol/server-postgres`, `chronologix-api`, `block-sensitive-commit.sh script`, `post-edit-check.sh script` (+63 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_client()` connect `API Core & Endpoints` to `Chronology Generation`, `LLM Client & Flag Detection`, `Demand Letter Drafting`, `Document Ingest Pipeline`, `Evidence Processing Pipeline`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `build_chronology()` connect `Chronology Generation` to `API Core & Endpoints`, `LLM Client & Flag Detection`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `process_document()` connect `Document Ingest Pipeline` to `API Core & Endpoints`, `Document Parsing`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `main()` (e.g. with `test_get_case_returns_404_when_not_found()` and `test_get_case_returns_case_detail()`) actually correct?**
  _`main()` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `npx`, `@modelcontextprotocol/server-postgres`, `chronologix-api` to the rest of the system?**
  _68 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `API Core & Endpoints` be split into smaller, more focused modules?**
  _Cohesion score 0.07294117647058823 - nodes in this community are weakly interconnected._
- **Should `Seed Demo & Endpoint Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.08974358974358974 - nodes in this community are weakly interconnected._