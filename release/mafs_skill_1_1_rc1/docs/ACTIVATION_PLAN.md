# Atomic activation plan (design only)

Production activation is not authorized by RC1 engineering.

The proposed reversible cutover uses versioned directories plus one small
registration pointer. Install 1.1 beside 1.0, validate package identity and
doctor state, atomically replace the registration file through a same-volume
temporary file, and retain the prior registration plus legacy manifest as the
rollback anchor. Rollback restores the prior registration atomically and then
verifies the complete legacy manifest and legacy doctor state. User evidence
artifacts are outside the version-owned directory and are never removed.

Only Gate R1 acceptance and subsequent HO/ChatGPT release authorization may
permit this plan to be executed against production registration.
