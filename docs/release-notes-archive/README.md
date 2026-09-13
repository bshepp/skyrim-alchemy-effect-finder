# Release notes archive

The public bodies of the `v0.1.0` and `v1.0.0` GitHub releases as they were before
repair on 2026-09-11. **Do not fix these files.** The garbage is the record.

## What happened

Both bodies were written inline from a PowerShell console (cp1252) and then edited
again with `gh release edit`. Each round-trip re-encoded the previous result, so every
em dash grew into a nested run of mojibake: about 94% of each body by the end, 1,680
runs in the worse one. Both releases were rewritten from UTF-8 files on 2026-09-11
and verified clean. Cause and prevention: `publish-all-the-things/venues/github.md`.

## Why these are kept

GitHub keeps no edit history for a release body. Once the pages were repaired,
nothing on the platform shows that the broken versions were ever live. These two
files are the only surviving copy.

They lived in `dist/` until 2026-09-13, which is gitignored, so one clean rebuild would
have deleted them. Moved here to be tracked.

## Fidelity

`.gitattributes` in this directory disables line-ending conversion, so git stores the
bytes as saved rather than normalising them. SHA-256 at the time of the move:

| File | Bytes | SHA-256 |
|---|---:|---|
| `release-notes-v0.1.0-original.md` | 19,972 | `747c02560201ae43b1e36a87466e9fd40e258dcc6a6c0c4124bf0725025b3b66` |
| `release-notes-v1.0.0-original.md` | 42,997 | `e3a8f693aa280b720e926b17918d0a944e75b04c23f4f6207d4b91c51ab19cde` |

One honest limit: these are the local backups as saved before the repair. They contain
CRLF line endings, which may have been introduced on save rather than served by
GitHub, so they are faithful to the backup and not proven byte-identical to the page.

The repaired versions are not archived here. They are the current release bodies and
can be read from the releases themselves.
