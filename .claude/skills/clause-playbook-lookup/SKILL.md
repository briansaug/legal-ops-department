---
name: clause-playbook-lookup
description: Answer "what is our standard position on X?" from the versioned playbook files. Use whenever a clause standard, escalation rule, or the governing-law allowlist is in question — the answer comes from the file, never from memory or general legal knowledge.
---

# Clause playbook lookup

Legal judgment in this department lives in versioned files, not in anyone's
head and not in a model's weights.

## Procedure

1. For a clause standard: `get_playbook_standard(clause_type)` — quote the
   returned text. Do not paraphrase a standard into something stricter or
   looser than written.
2. For routing rules: read `playbook/escalation-matrix.md`.
3. For governing law: read `playbook/governing-law-allowlist.md`. Three
   jurisdictions do not escalate; everything else does.

## Rules

- If the playbook has no section for what you're asked, say so — the
  correct answer to an unwritten standard is "unwritten; ask the contracts
  attorney to add it", never an improvised position.
- If the asker disagrees with the standard, that's a playbook edit request
  for the contracts attorney, not a reason to answer differently.
- Answers cite the file and section so the asker can read the source.
