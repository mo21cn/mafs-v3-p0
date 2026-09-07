# MAFS Skill 1.1.0 — Known Limitations (Repository Record)

This is the **in-repo** GA known-limitations note. The canonical
user-facing limitations document is in the GA release envelope:

```text
MAFS_Skill_1.1.0_release/KNOWN_LIMITATIONS.md
```

inside `MAFS_Skill_1.1.0_release.zip` (SHA256
`ad947816739ebd2faa51b0a4764643012686414fc7d8ec4874fa5d2c6fc41742`).

## Brief summary (for repository governance)

- HO-mediated selection is required at every governed STOP boundary.
- External scientific source accessibility depends on provider availability.
- A scientifically valid run may terminate as `PARTIAL` / `NOT_ADDRESSED` /
  `NOT_GROUNDED` / `INSUFFICIENT_EVIDENCE` / `UNRESOLVED` / `NO_SELECTION`.
- MAFS Skill 1.1 does **not** provide: autonomous top-1 source selection,
  autonomous release authority, automatic scientific truth arbitration,
  unbounded recursion, clinical decision authority, self-evolving skill
  modification, SKILL.state-style canonical execution state,
  WikiSkill-style automated evolution loop. The last two belong to the
  MAFS Skill 1.2 / 2.x roadmap.
- R1 PASS is a product/release acceptance judgment. It is **not** a claim
  that the full bright-light evaluator scientific narrative is established.
  CP-004 supports a narrower objective circadian phase-shifting proposition
  only.
- Production cutover is not yet authorized.

For the full text of each limitation and the precise non-feature list, see
the envelope's `KNOWN_LIMITATIONS.md`.
