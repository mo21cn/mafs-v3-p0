# MAFS Skill 1.1.0 — GA Release Notes (Repository Record)

This is the **in-repo** GA release note. The canonical user-facing release
notes are in the GA release envelope:

```text
MAFS_Skill_1.1.0_release/RELEASE_NOTES.md
```

inside `MAFS_Skill_1.1.0_release.zip` (SHA256
`ad947816739ebd2faa51b0a4764643012686414fc7d8ec4874fa5d2c6fc41742`).

This in-repo record is a governance pointer that the GA PR added a release
note to the repository. It preserves the GA identity facts and points to
the envelope for the full narrative.

## Identity

- **Product:** MAFS Skill
- **Outer version:** 1.1.0
- **Tested payload version:** 1.1.0-rc1
- **R1 accepted SHA:** `f970327ae91e211eb2ac813430918c8851cbd6af`
- **R1 seal tag:** `mafs-skill-v1.1.0-rc1-r1-accepted` → `f970327a…`
- **Tested payload SHA256:** `ac881d9d80ca46d31ec65988306ee25bb455c22e83ddd5599e5b8c1d3617d82f`
- **GA release envelope SHA256:** `ad947816739ebd2faa51b0a4764643012686414fc7d8ec4874fa5d2c6fc41742`
- **GA tag:** `mafs-skill-v1.1.0` (post-merge; see GA_RELEASE_RECORD.json for the post-merge SHA)

## What this record is

This is one of the 7 in-repo governance files added by the GA promotion PR
(per release contract §26). The full list:

- `GA_RELEASE_RECORD.json`
- `GA_RELEASE_ACCEPTANCE.json`
- `GA_RELEASE_MANIFEST.json`
- `GA_RELEASE_NOTES.md` (this file)
- `GA_KNOWN_LIMITATIONS.md`
- `GA_RELEASE_CHANGED_FILES.txt`
- `GA_RELEASE_SHA256_MANIFEST.txt`

## Production status

- `MAFS_SKILL_1_1_RELEASED = true` (this GA promotion completes the release)
- `MAFS_SKILL_1_1_PRODUCTION_ACTIVE = false` (production cutover not authorized)
- `PRODUCTION_CUTOVER_AUTHORIZED = false` (separate Production Cutover Contract by DSH)
- `MAFS_SKILL_1_0_REPLACED = false` (legacy 1.0 preserved at `I:\MAFS Skill 1.0\`)

## Full narrative

For the complete release narrative — what MAFS Skill 1.1 is, what changed
from 1.0, what R1 proved, what Attempts 1/2 discovered, what RA2/RA3
corrected, what the final tested payload is, what remains out of scope, and
upgrade/rollback note — see the envelope's `RELEASE_NOTES.md`.
