# Rust migration plan

**Status: planned, not started (owner decision, 2026-10-31).** Truestill will be rewritten
entirely in Rust. Until the work starts, the Python code gets minimal investment: only safety fixes
and keeping `main` green, no refactors of code that will be replaced (`CLAUDE.md`, "Until the Rust
rewrite").

This is a plan, not a design. Nothing here is built, and every claim marked "to check" is a question
for the first spike, not a decision.

## Why Rust for Truestill

- **One small binary per OS.** Users no longer need Python, and nothing has to be installed beside
  the program.
- **Much faster scanning and hashing.** Parallel by default, and the program starts instantly.
- **Memory-safe decoders for JPEG, PNG and GIF.** This removes the class of bug behind many of
  Pillow's advisories: memory errors in its C decoders (a JPEG buffer overflow and a TIFF
  out-of-bounds read were among the critical and high ones fixed by the 13.0.0 upgrade). To check:
  that the decoders chosen are the pure-Rust ones (the `image` crate's JPEG, PNG and GIF decoders
  are the candidates).
- **Stronger correctness when moving users' photos.** Ownership and error types rule out a family of
  memory and error-handling mistakes in file handling, in the part of the product where a mistake
  costs someone a photograph.

## Known gaps to check first

- **HEIF still goes through C.** Decoding the pixels of a HEIC photo means libheif bindings, so the
  memory-safety argument does not cover that format. Reading HEIF metadata does not need it (see
  below).
- **RAW support is weaker than Python's.** Compare the formats Truestill reads today
  (`docs/format-coverage-audit.md`) against what the Rust ecosystem decodes, format by format.
- **Duplicate detection.** `image_hasher` is a small project (3.1.1, 2026-02-21, MIT OR Apache-2.0,
  checked on crates.io 2026-10-31), and its hashes may not match Python's `imagehash` bit for bit.
  Decide whether compatibility with the hashes already stored in existing users' catalogs is
  needed. If it is, the Rust hashes must reproduce the Python ones exactly, and that is the first
  differential test to write; if it is not, existing catalogs need a one-time rehash.
- **Video and photo metadata.** `nom-exif` (3.8.0, 2026-09-07, pure Rust, reads Exif from images
  including HEIF/HEIC and metadata from video and audio) is the candidate. crates.io lists its
  licence as "non-standard": read the licence text before adopting it.

## Approach

- **Full rewrite in pieces, with the Python version as the reference.** In this order: scan,
  metadata, hashing, organize, undo.
- **Differential testing.** Run both implementations on the same photo corpus and compare their
  results. The existing corpus and the existing tests are the specification: a piece is done when
  Rust gives the same answers on them, or when a difference has been decided on purpose and written
  down.
- **An optional bridge.** PyO3 with maturin can run Rust modules inside the Python app during the
  transition, so a finished piece can ship before the rest exists. Use it only if it saves work;
  it is not a goal.
- **Switch only when results match, then retire Python.** No period of two implementations being
  both authoritative.
- **The UI is decided later.** Either keep the current web UI on a Rust backend, or build a desktop
  app. Nothing in the first pieces depends on that choice.

## Sources

- The Compute Paris 2026 talk "The Rust tipping point for Python libraries" (named by the owner; the
  talk itself was not re-read for this document).
- `image_hasher` on lib.rs and crates.io; `nom-exif` on docs.rs and crates.io; the `image` crate
  (0.25.10, checked on crates.io 2026-10-31).
