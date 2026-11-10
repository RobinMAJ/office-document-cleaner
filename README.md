# Office Document Cleaner

A standalone, browser-only utility for inspecting and removing common metadata from Word (`.docx`), Excel (`.xlsx`) and PowerPoint (`.pptx`) packages. Chinese interface with an Apple-like system visual style, responsive forms and light/dark appearance.

## Privacy and scope

- Documents are selected, parsed, changed and downloaded in the visitor's browser.
- No document upload endpoint, analytics, remote font or runtime CDN dependency.
- JSZip 3.10.1 is vendored with its license and registry integrity record.
- The origin serves only a manifest-verified static allowlist, rejects uploads/mutations, and sends a CSP that forbids network connections from the application.
- No login password, as requested by the owner. The public webpage is accessible to anyone with the URL.
- Frontend source delivered to browsers is inspectable. NAS deployment and runtime state are not served.

The tool targets the metadata fields and supported common traces shown in the interface. It does not promise removal of identities embedded in document content, pictures, embedded objects, all OOXML extensions or every revision format. Original files remain unchanged; a new copy is downloaded. Office may recreate metadata after a cleaned copy is opened and saved.

## Local use

Requires Python 3.8+ to serve static assets. No server-side application dependencies.

```sh
python3 deploy/build.py
python3 deploy/static_server.py --port 18815
```

Open `http://127.0.0.1:18815/`. Test data is synthetic. To run functional fixtures, use an environment with `python-docx`, `openpyxl`, and `python-pptx`:

```sh
python3 tests/generate_fixtures.py
node --test tests/metadata.test.cjs
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## NAS deployment

Target project: `/config/workspace/office-document-cleaner`.
Versioned release: `deployment/20261110-v1`.
Loopback static origin: `127.0.0.1:18815`.
Independent node: `office-document-cleaner`, socket `/tmp/office-document-cleaner.sock`, dedicated UDP 41660.
Intended HTTPS URL: `https://office-document-cleaner.tailee7aa5.ts.net/` (accept only after owner enrollment, publication and external verification).

From that NAS release directory, as the project owner:

```sh
python3 deploy/start_origin.py probe
python3 deploy/start_origin.py start
python3 deploy/tailscale_node.py probe
# New-device registration and public publication require owner authorization.
python3 deploy/tailscale_node.py enroll
python3 deploy/tailscale_node.py publish
```

Read-only checks:

```sh
python3 deploy/start_origin.py status
python3 deploy/tailscale_node.py status
```

To pause only this site's public entry:

```sh
python3 deploy/tailscale_node.py pause
```

The scripts preserve A1, Orbital and Chili node identities and routing. They never import another node's private identity. State and logs are outside the public release tree at `var/` and excluded from Git.

These scripts detach the origin/node from the development terminal. This is distinct from boot recovery: startup after NAS/container reboot must be integrated into the NAS service lifecycle and separately verified. Do not claim a reboot test from an editor-disconnection test.

## Updating code and the live site

GitHub is the versioned source. Committing/pushing does not automatically modify the NAS service.

1. Edit the source and run affected functional/security checks.
2. Run `python3 deploy/build.py` after final source edits; inspect both code and manifest.
3. Commit the reviewed source and record its commit SHA. Keep secrets, runtime state and user documents out of Git.
4. Stage a fresh NAS release and verify all file hashes before switching a live origin.
5. A frontend change also needs a matching manifest; this origin refuses changed/unlisted files.
6. Preserve previous release/process provenance, update only this project, and verify actual public page and download. Roll back if acceptance fails.

This repository does not install an automatic deployment watcher. Future backend or lifecycle changes require their own review.

## Design provenance

Uses guidance from [Apple Design](https://github.com/emilkowalski/apple-design), adapted into native HTML/CSS: system typography, immediate press feedback, contextual grouping, accessible focus and reduced-motion/transparency support. See `docs/DESIGN.md`.
