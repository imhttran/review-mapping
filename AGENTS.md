# Agents Guide — mapping-exercise

General rules (senior dev mode, Git workflow, authorization) come from `~/.claude/CLAUDE.md` and `~/.config/AGENT-POLICY.md`. This file covers only what is specific to this project.

## Requirements

An interview take-home: map each review in `reviews.csv` to the job (and customer) it is about in `jobs.csv`, then write up the approach and results. The original prompt is `data/README.md`. The solution is discussed on-site, so the writeup and code must be easy to explain out loud.

## Workflow

The project shows its progression through documents, then implementation and writeup.

| Kind                | Location             | Naming                                                                    |
| ------------------- | -------------------- | ------------------------------------------------------------------------- |
| Requirements (PRDs) | `docs/requirements/` | `NN-<topic>.md`, for example `01-review-mapping.md`                       |
| Plans               | `docs/plans/`        | `NN-<topic>.md`, using the same number and topic as the PRD it implements |
| Data analysis       | `docs/findings/`     | `dataset_analysis.md`: profile of both CSVs and what it means for the matcher |
| Writeup             | `docs/writeup.md`    | Approach, results and discussion cases. Numbers come from `results.csv` |
| Results             | `results.csv`        | Written by `python3 python/matcher.py`. Never edit by hand |
| EGM artifacts       | `docs/egm/`          | `egm_lite_checklist.md`, `egm_lite_alternatives.md`, and other EGM skill output |

- Put every PRD in `docs/requirements/` and every plan in `docs/plans/`. Don't create them anywhere else.
- Each plan links to its PRD, and each PRD links to its plan.
- Work one phase at a time, following the plan.
- Update the plan when a decision changes.
- Keep the README progress table current.
- Write EGM skill artifacts (checklists, alternatives, drafts) to `docs/egm/`, not the project root.

EGM artifact directory: docs/egm

## Data

The CSVs and the exercise prompt live in `data/` (alongside an exploratory `analysis.ipynb`; `data/.venv` is local tooling).

| File                             | Rows | Notes                                                                                                                                                                       |
| -------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `data/reviews.csv`        | 40   | `review_id, source, posted_at, author_name, rating, review_text`. No email or phone.                                                                                        |
| `data/jobs.csv`       | 100  | `job_id, customer_*, service_city, service_type, job_started_at, review_requested_at, review_link_clicked_at, photo_count, job_status, crew_member`. Some fields are blank. |

- Treat both CSVs as read-only input. Never edit them.
- The prompt mentions an address, but `jobs.csv` has only `service_city`.
- Timestamps mix dates (`2026-05-28`) and UTC datetimes (`2026-06-02T14:30:00Z`). Parse both.
- Names need normalizing: accents, hyphens, initials, nicknames, swapped order, business suffixes.

## Conventions

- Python 3 standard library only. No new dependencies.
- One matcher script and one test script (`python/test_matcher.py`, run with `python3 python/test_matcher.py` or `python3 -m unittest` from the project root), both in `python/`. Keep matching rules readable and explainable over clever.
- Every review gets either a job ID with a confidence level and a reason, or an explicit "no match" with a reason. Leaving a review unmatched is a valid result. Never force a match.
- Keep one small assertion-based check covering the tricky cases (for example, timing beating an exact name match).
