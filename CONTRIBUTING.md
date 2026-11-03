# Contributing

## Workflow

1. Pick a card from the board (max 2 In Progress).
2. Branch from `main`: `feature/<issue>-short-name`, for example `feature/12-stg-orders`.
3. Commit with Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`.
4. Open a PR with `Closes #<issue>` in the body.
5. CI must be green. Squash and merge. The card moves to Done.

`main` is protected. Never push to it directly.

## Definition of Ready

Story sentence, acceptance criteria, estimate, no blocker.

## Definition of Done

Criteria met and demonstrated, safe to re-run, tests passing, docs updated,
no secrets or hard-coded paths, PR reviewed and merged.

## Secrets

Never commit `.env`, keys or passwords. Use `.env` locally, SSM Parameter Store in AWS,
GitHub Secrets in CI.
