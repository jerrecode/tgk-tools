# Offline source bundle verification implementation plan

**Goal:** Package the current supported sources reproducibly without following external links or damaging prior outputs on failure.

**Architecture:** Keep the existing local source copier and deterministic tar metadata. Reject nonregular source entries, stage compressed output beside its destination, and publish only after success. Preserve target-device native compilation.

**Tech stack:** Python 3.10+, unittest, tarfile, existing shell installers.

**Spec:** User TGK/TGK Tools handoff dated 2026-10-23.

## Constraints and review focus

No generated host binaries, Git data or private external files. Cover source symlinks, FIFOs, output paths inside source, failed archive writes, byte reproducibility, reinstall and removal of extracted sources. Android hardware validation remains pending.

## Task 1: Repair source/output boundaries

- [x] Add failing tests for external source symlinks and special files.
- [x] Add a failing test preserving an existing archive on archive-write failure.
- [x] Reject unsupported source entries, stage output and atomically replace on success.
- [x] Run full unittest suite, CLI help, compileall and shell syntax checks.
- [x] Build twice, compare bytes, run the offline installer checker and fresh editable install with isolated configuration.
- [ ] Document packaging guarantees and manual hardware commands. Commit and open PR; inspect reviews/checks before a policy-compliant merge.

## Evidence ledger

Baseline: 128 tests pass from the tools checkout using current TGK main. Initial run from the parent of both editable checkouts hit Python namespace shadowing; rerunning from the project directory resolved it. No source change justified for that harness invocation.

Verification: 133 tests pass; offline copy installation/reinstallation/source deletion/native rendering/uninstall pass. Fresh editable installs pass. Edited palette, typography, config and SVG preserved byte-for-byte on reinstall. Independent review identified an output-alias self-inclusion regression; failing tests cover dot-dot and symlinked parent aliases, then pass after parent canonicalization. PR publication/checks remain pending at this commit.
