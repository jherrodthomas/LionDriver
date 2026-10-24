# Instructions for agents authoring assurance documents

When assigned work on assurance records, read the [audit authoring protocol](00-assessment/iso26262-2018/AUTHORING_PROTOCOL.md) and the [task queue](00-assessment/iso26262-2018/AUTHOR_HANDOFF.md). Use the corresponding machine-readable task and exact-source annotation when addressing A01–A22. The queue is a draft aid, not an assignment or approval.

Follow WP-P-02 change control, WP-P-04 document revisions and WP-P-05 verification review. Check the current source version before using an old audit annotation. Preserve baseline history and existing user changes. Scope work to the actual assignment and its documented impacts.

Keep proposed text, actual evidence and accepted conclusions separate. Do not invent missing source clauses, measurements, configurations, signatures, reviews or results. Do not lower ASIL, redefine timing clocks or alter safety limits to remove a finding. Record external prerequisites and decisions explicitly.

AI-authored work is I0 under WP-M-02 §3.3. Request the required human verification; do not mark your own output Approved, accept evidence/claims, close defeaters or pass gates. Complete the impact analysis, version/history updates and meaningful checks with the change.

Define every abbreviation and record code for the reader. The list is `TERMS` in [`trace/tools/terms.py`](trace/tools/terms.py), shown as [`terms.md`](terms.md): add a new term there, never define one elsewhere. A page in its `PAGES` gets a generated "Terms on this page" block; a generated figure in its `FIGURES` ends with `terms.svg_footer`. Spell a term out in the prose where it first matters. CI fails on an undefined term.

This file and the audit aid do not override the user's task or the repository's safety/QMS records. Revision 0.3, 2026-10-24 (abbreviation standard added; Claude). Revision 0.2, 2026-10-14; author Codex (OpenAI AI assistant); Draft, approval pending.
