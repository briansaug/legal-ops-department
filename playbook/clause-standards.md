# Clause standards

The department's position on each intake field. These definitions follow
CUAD's annotation guidelines (the gold labels are CUAD's), and where CUAD's
definition is broader than everyday usage the section says so.

**This file wins.** If a model's judgment and this file disagree, this file
is right until an attorney edits it.

Each section carries the machine-read line `**Escalate when:**` — the
escalation-router skill and `get_playbook_standard` parse it verbatim.

---

## anti_assignment — Anti-Assignment

Consent or notice required for assignment, or assignment prohibited outright.
Includes clauses that void assignments made without consent.

Department standard: acceptable when consent is not to be unreasonably
withheld and there is a carve-out for assignment to affiliates or in a sale
of substantially all assets.

**Escalate when:** assignment is prohibited outright with no affiliate or
change-of-control carve-out, or an assignment made without consent is void.

## change_of_control — Change of Control

Rights triggered by merger, consolidation, or transfer of a controlling
interest — typically termination rights or required consent/payment.

Department standard: acceptable when limited to notice obligations.
Termination rights held by the counterparty on our change of control are
non-standard.

**Escalate when:** the counterparty can terminate or claim payment on our
merger, acquisition, or change of control.

## termination_for_convenience — Termination for Convenience

Either party may terminate without cause, on notice.

Department standard: acceptable when mutual, or held by us, with 30+ days'
notice. One-sided convenience termination held only by the counterparty is
non-standard.

**Escalate when:** only the counterparty may terminate for convenience, or
the notice period is under 30 days.

## cap_on_liability — Cap on Liability

Liability limited to a fixed amount, fees paid, or another ceiling.

Department standard: expected in commercial paper; standard cap is 12 months
of fees. Absence of any cap is itself a flag (see uncapped_liability).

**Escalate when:** the cap is below fees paid, or the cap applies to us but
not to the counterparty.

## uncapped_liability — Uncapped Liability  ⚠ high-stakes

A party's liability is uncapped for some or all breaches, including
carve-outs from the limitation of liability (indemnity, IP, confidentiality,
gross negligence often ride outside the cap).

**Escalate when:** present in any form. Always attorney review — no
exceptions, not overridable by any model or any confidence level.

## non_compete — Non-Compete  ⚠ high-stakes

Restrictions on competing with the counterparty, operating in a market or
geography, or contracting with competitors.

**Escalate when:** present in any form. Always attorney review.

## exclusivity — Exclusivity  ⚠ high-stakes

Exclusive dealing, exclusive rights or territory, or a commitment to
procure solely from one party. **CUAD's definition is broad** and this
department adopts it: branding exclusivity (e.g. "products shall bear no
other logos") and exclusive license grants count, not just requirements
contracts. The 10-label spot-check before the gold set froze surfaced
exactly this case, and the playbook was aligned to CUAD rather than
quietly relabeling.

**Escalate when:** present in any form. Always attorney review.

## most_favored_nation — Most Favored Nation  ⚠ high-stakes

A commitment that the counterparty receives terms at least as favorable as
those given to any third party.

**Escalate when:** present in any form. Always attorney review.

## governing_law — Governing Law

The jurisdiction whose law governs the agreement. This field is
deterministic: a jurisdiction string checked against
[`governing-law-allowlist.md`](governing-law-allowlist.md). The production
pipeline extracts it with a regex, not a model — the evals showed the model
added cost without accuracy here.

**Escalate when:** the governing jurisdiction is not on the allowlist, or
no governing-law clause is found.

## renewal_term — Renewal Term

Automatic renewal or unilateral renewal rights, including evergreen terms.

Department standard: acceptable when renewal requires mutual agreement or
we hold the renewal option. Auto-renewal is acceptable with a 60+ day
non-renewal notice window.

**Escalate when:** the contract auto-renews with a non-renewal notice
window under 60 days, or renewal is at the counterparty's sole option.
