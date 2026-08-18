# Safe Editing Rules

This repository is a live tournament website. The priority is to make small changes without disturbing working tournament behavior.

## Before changing code

1. Read `CODE_GUIDE.md`.
2. Identify the smallest file and function that owns the behavior.
3. Do not rebuild an entire HTML file for a one-function change.
4. Preserve existing Firestore field names and bracket keys unless a migration is intentional.
5. Keep current tournament History data backward-compatible.

## During a change

- Prefer isolated edits.
- Keep comments around important state and data-flow boundaries.
- Do not rename DOM IDs casually; JavaScript handlers may depend on them.
- Do not remove `pendingBracketMaps`, `pool`, `bracket`, `seeds`, `teamNames`, `mapPool`, or `history` without a migration plan.
- Never replace the bracket renderer just to change a small visual detail.

## After a change

- Run the repository validation workflow.
- Check the changed page in the browser.
- Verify Firebase reads/writes still work.
- Verify the public viewer still updates from the same tournament document.
- Verify History remains independent from current-tournament resets.

## Rollback

Every Git commit is a rollback point. If a change causes a regression, revert the smallest offending commit rather than rebuilding the site from memory.

## Architecture rule

Feature logic should live in the smallest logical section. If a section becomes too large, split it into a separate module in a dedicated refactor instead of mixing restructuring with a tournament-feature change.
