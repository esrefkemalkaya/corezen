# Contributing to KarotCam

Thanks for your interest in helping make KarotCam better. This is a niche tool — drilling core box photography for mineral exploration — so contributions from people who understand the field workflow are especially welcome.

## Project Status

The repository currently contains the **design specification** and **implementation plan** for Sub-project 1 (Foundation + Capture Loop). No application code has been written yet.

If you want to help, the most valuable contributions right now are:

1. **Reviewing the design spec** — [`docs/superpowers/specs/2026-04-29-karotcam-foundation-design.md`](docs/superpowers/specs/2026-04-29-karotcam-foundation-design.md). Open an issue if you spot something wrong, missing, or impractical.
2. **Reviewing the implementation plan** — [`docs/superpowers/plans/2026-04-29-karotcam-foundation.md`](docs/superpowers/plans/2026-04-29-karotcam-foundation.md). Same — open an issue.
3. **Implementing tasks from the plan** — Each task is self-contained, TDD-structured, and includes complete code. Pick one and open a draft PR.

## How to Propose Changes

1. **Open an issue first** for anything beyond a typo. Briefly describe the problem and your proposed approach.
2. **Fork** the repo, create a feature branch (`feat/<short-description>` or `fix/<short-description>`).
3. **Match the project conventions** — see below.
4. **Open a PR** referencing the issue. Keep PRs focused: one concern per PR.

## Code Conventions (when implementation begins)

These come from `karotcam_prompt.md` and the design spec — please respect them:

- **Python 3.11+**, full type hints (mypy strict)
- **Docstrings in Turkish**, identifier names in English
- `pathlib.Path` only — never `os.path`
- f-strings only — never `%`-format
- No `async`/`await` — keep the field tool simple
- Black formatter, line length 100
- pytest for tests, no GUI unit tests in v1
- All user-facing strings live in `karotcam/gui/i18n/tr.json` — no hardcoded UI text

## Reporting Bugs (once code exists)

Include:
- KarotCam version (visible in the window title)
- Windows version
- digiCamControl version
- Camera model and lens
- Steps to reproduce
- The relevant lines from `data/logs/<date>.log`

## Questions

Open a [GitHub Discussion](../../discussions) or email the maintainer (see `README.md`).
