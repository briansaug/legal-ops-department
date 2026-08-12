# Governing-law allowlist

Jurisdictions that do **not** auto-escalate. Everything else — any other US
state, any non-US jurisdiction, or no governing-law clause at all — routes
to attorney review.

- Delaware
- New York
- California

This rule used to live in a senior paralegal's head. Now it lives here, and
`extract_governing_law` + `governing_law_allowlist()` apply it with a regex
and a file read — no model call. Edit this file to change the rule.
