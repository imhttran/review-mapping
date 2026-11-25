# Plan: Review-to-Job Mapping

Status: Done, all 6 phases · Requirements: [requirements/01-review-mapping.md](../requirements/01-review-mapping.md)

## Data findings (input to the design)

Before designing anything, I read all 40 reviews against the 100 jobs. These patterns drive the design:

| Pattern | Example | Design impact |
| --- | --- | --- |
| Link click minutes before the review | R01 posted 12 min after J001's click | Click-to-post gap is the strongest signal |
| Same customer, several jobs | Sarah Johnson: J001, J015 | Name alone can't pick the job; timing must |
| Same name, different people | John Smith: J018, J019, J056 | Need timing and service to break ties |
| An exact name match is wrong | Jose Hernandez J053 vs José Hernández J012 | Name normalization, plus penalties for timing that contradicts |
| Nicknames, initials, swapped order, suffixes | Bob/Robert, "J. Anderson", "Yamamoto Henry", "Inc" | Normalized name comparison, not string equality |
| Name changed, email didn't | Lisa Stevens vs Lisa O'Connor `lstevens@` | Compare against the email local part |
| Shared phone/email across customers | Sarah Chen and Sarah Johnson | Contact fields can't be a unique key |
| Review about someone else | "my husband Carlos", "my son Brian" | Extract the named person from the text |
| Cancelled or estimate-only jobs get reviews | R35 1 star → cancelled J033 | Don't filter by status |
| Very late reviews | Reviews posted a year or more after the job | No hard cutoff, just a recency bonus |
| Junk / other business | Test review, painting review, "happycustomer22" | Explicit no-match path |
| Conflicting strong signals | Click → HVAC job, text → water heater | A *needs review* outcome, not a forced pick |

## Design

A small rule-based ranker. For each review: filter, score every remaining job, then decide.

```
review ─► junk filter ─► rule out impossible jobs ─► score candidates ─► confidence ─► outcome + reasons
```

Why rules and not ML: there is no labeled data, the sample is 40 rows, and the on-site discussion needs every decision to be explainable. Rules also produce the labeled data a model would need later.

### Scoring signals (initial weights, to be tuned)

| Signal | Direction |
| --- | --- |
| Name similarity (required) | + strongest base |
| Link clicked shortly before posting | + strong, decays with gap |
| Request sent recently, no click | + weak |
| Request sent after the review | − |
| Job is recent | + weak |
| Service in text matches / contradicts job | + / − strong |
| Crew member named in text | + |

### Confidence

Based on the top score, its margin over the runner-up, and how strong the top candidate's identity evidence is. First rule that fires wins:

1. **No match:** the review is junk, there are no candidates, or the top score is under 40.
2. **Needs review (low):** the top two candidates are within 10 points.
3. **Matched, medium:** the top identity is only a partial name, an email local part or a named relative, a runner-up has a stronger identity, a signal on the top candidate contradicts the match (a negative signal, or a link click after the review was posted), the score is under 60, or the margin is under 30.
4. **Matched, high:** everything else.

The earlier idea of a separate rule where a strong signal pointing at a different job forces *needs review* was dropped: in the sample only R19 has one, and its margin is already within 10, so the margin rule catches it. The thresholds were chosen after seeing the scores of 40 reviews, so they look good here by construction.

## Phases

Each phase ends in something reviewable. Commit at each one so the progression is visible.

| # | Phase | Deliverable | Done when | Status |
| --- | --- | --- | --- | --- |
| 1 | Load and normalize | CSV loading, date parsing (date and UTC datetime), name normalization | Accented, hyphenated, reordered and suffixed names compare equal in a quick check | Done. `python/matcher.py` and `python/test_matcher.py`; `python3 python/test_matcher.py` passes |
| 2 | Filters | Junk filter, ruling out jobs that hadn't started | The test review is dropped. Jobs after the review date never appear as candidates | Done. `junk_reason` and `eligible_jobs` in `python/matcher.py`, cases in `python/test_matcher.py`; `python3 python/test_matcher.py` passes |
| 3 | Scoring | Signal functions, each returning points plus a reason string | Every candidate has a score and readable reasons | Done. `score_candidates` in `python/matcher.py` (identity, click, request, recency, service, crew), cases in `python/test_matcher.py`; `python3 python/test_matcher.py` passes |
| 4 | Confidence and outcomes | `decide`: thresholds, identity caps, *needs review* / *no match* | Every review has exactly one outcome (PRD R1) | Done. `decide` in `python/matcher.py` (outcome, confidence, runner-up, reasons), cases in `python/test_matcher.py`; `python3 python/test_matcher.py` passes. Sample result: 31 matched (21 high, 10 medium), 5 needs review, 4 no match |
| 5 | Check | One assertion script over the tricky cases in the findings table | Script passes. Breaking a rule makes it fail | Built: `python/test_matcher.py` starts with a map of each findings-table case to the assertion that guards it, plus an explicit "timing beats name" assertion; `python3 python/test_matcher.py` passes. Breaking a click-tier or name weight in a copy of the matcher makes it exit 1 (run with `MATCHER=<copy> python3 python/test_matcher.py`, 2026-11-25: 3 failing tests, `scoring`, `decisions` and `results`). External mutation run: 296 mutants, 15 equivalent survivors |
| 6 | Results and writeup | `results.csv`, writeup of approach, results and discussion cases | Every decision can be explained from its reasons | Built: `python3 python/matcher.py` writes `results.csv` (40 rows: 21 high, 10 medium, 5 needs review, 4 no match); `docs/writeup.md` covers approach, results, discussion cases and limits; `check_results` in `python/test_matcher.py` guards the file |

## Technical choices

- Python 3 standard library only. No dependencies to install on-site.
- One matcher script and one test script (`python/test_matcher.py`), both in `python/`.
- Output CSV columns: `review_id, author_name, outcome, confidence, job_id, customer_name, runner_up, reasons` (reasons joined with ` | `).

## Risks

| Risk | Mitigation |
| --- | --- |
| Weights overfit the 40 samples | Keep weights few and round. Say so in the writeup. Production would tune them on reviewer corrections |
| Keyword lists miss service wording | Keep the lists small and visible. Note a classifier as the upgrade |
| Thresholds too strict, so too many go to manual review | Report the counts per outcome, so the trade-off is visible (PRD open question 1) |

## After this version

- Put a job token in review-request links. That removes most of the guessing.
- Turn the *needs review* queue into labeled data, then fit the weights.
- Add address matching if the real system has addresses.
