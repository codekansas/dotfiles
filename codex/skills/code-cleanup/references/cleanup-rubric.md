# Cleanup Rubric

Use this rubric to keep cleanup work targeted and repository-specific.

## Pick The Right Range

Prefer one of these, in order:

1. A user-specified commit, PR, or commit range.
2. The diff from the current branch to its merge-base with the default branch.
3. The last 3-10 commits when the branch context is local and recent.

The point is to clean up the code that was actually introduced, not to relitigate the whole repository.

## Categories Of Cleanup

### Structural

- Move code into the right package, folder, or ownership boundary.
- Collapse accidental duplication introduced by recent work.
- Remove new junk-drawer modules and vague helper layers.

### Interface Quality

- Tighten naming, parameters, return types, exports, and error surfaces.
- Normalize public API shape to match the repository's existing patterns.

### Maintainability

- Improve comments and docs where the changed code is hard to reason about.
- Add or adjust only the tests that materially prove the changed behavior.
- Make config and logging flow consistent with house style.

## Non-Goals

- Global formatting churn.
- Unrelated architecture rewrites.
- Replacing direct code with abstract patterns just because they look cleaner.
- Reopening settled product decisions in the name of style.

## Conflict Resolution

When the recent code, `CODE_STYLE.md`, and existing repository reality disagree:

- Follow enforced tooling first.
- Follow stable public or cross-module contracts second.
- Apply style guidance where it can improve the changed area without causing churn.
- Call out gaps in `CODE_STYLE.md` when the document no longer matches the repository.
