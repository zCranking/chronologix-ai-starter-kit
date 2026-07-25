-- Phase 4: adjacent verticals. Same document/evidence shapes as personal
-- injury (PLANNING.md), different evaluation standard per case_type --
-- workers' comp (benefits/disability rating, no pain-and-suffering) and
-- med mal (standard-of-care/breach/causation) get their own demand-letter
-- prompt in demands/draft.py. Chronology/flags are case_type-agnostic.
alter table cases
    add column case_type text not null default 'personal_injury'
        check (case_type in ('personal_injury', 'workers_comp', 'med_malpractice'));
