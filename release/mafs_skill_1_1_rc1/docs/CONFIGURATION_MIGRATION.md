# Configuration and state migration

MAFS Skill 1.0 contains no product configuration file that must be translated.
Its runtime pins are historical product identity, not user configuration.

| Legacy surface | Classification | RC1 action |
|---|---|---|
| provider environment references | SECRET_REFERENCE_ONLY | detect presence only; never copy values |
| deploy scripts and manifests | DEPRECATED | preserve in legacy tree; do not import |
| `.omx` session/log state | UNSUPPORTED / IGNORED_BY_DESIGN | preserve legacy bytes; do not activate in RC |
| user evidence artifacts | COPY_AS_IS only when user explicitly supplies an external evidence root | never delete on rollback |

`STATE_MIGRATION_NOT_REQUIRED` applies to the RC runtime itself. New RC files
are version-owned and safe to remove; operation logs and rollback anchors must
be preserved for audit.

`mafs-skill-1.1-configuration.json` is `RC_OWNED`. It contains only release
bootstrap capability flags, not user data or credentials. Clean uninstall and
rollback remove it together with the versioned RC target. Operation logs,
registration history supplied by the caller, and rollback anchors remain
separate audit state.
