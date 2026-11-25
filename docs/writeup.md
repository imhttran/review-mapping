# Writeup: mapping reviews to jobs

Plan: [plans/01-review-mapping.md](plans/01-review-mapping.md) · Requirements: [requirements/01-review-mapping.md](requirements/01-review-mapping.md) · Results: [results.csv](findings/results.csv) · Code: [python/matcher.py](../python/matcher.py), [python/test_matcher.py](../python/test_matcher.py)

Run it: `python3 python/matcher.py` writes `docs/findings/results.csv` and `docs/findings/no_match.csv`, and `python3 python/test_matcher.py` runs the checks (`python3 -m unittest` works too). Python 3, standard library only.

## Approach

A review has an author name, a time, a rating and free text. A job has a customer, dates, a service, a crew member and, sometimes, a click on the review link. The matcher is a small set of rules, because there are no labels to train on and every decision has to be explainable out loud.

For each review:

1. **Junk filter.** Test reviews ("test review"), placeholder authors ("John Doe"), reviews posted in the future, and reviews about a service we don't offer (painting) get *no match* with a reason.
2. **Rule out impossible jobs.** A job that hadn't started when the review was posted is never a candidate (PRD R3). Cancelled, estimate-only and in-progress jobs stay candidates (R6).
3. **Score every remaining job.** Each signal adds points and a reason:

| Signal | Points |
| --- | --- |
| Name: exact / close (typo) / partial (initial, first name only) | 40 / 30 / 15 |
| Email local part matches the author (when the name doesn't) | 30 |
| Text names a relative who is the customer ("my husband Carlos") | 20 |
| Link clicked before the review: within 1h / 6h / 48h / 168h | 40 / 30 / 20 / 10 |
| Request sent in the last 72h, no click / review posted before the request | +10 / -20 |
| Job started within 30 days | +5 |
| Service word in the text matches / contradicts the job's service | +20 / -30 |
| Crew member named in the text | +10 |

   If a job has both a partial name (15) and a named relative (20), the relative's 20 is used. Only the best identity signal counts, they are not added.

   Names are compared after normalizing accents, hyphens, case, business suffixes, swapped order and a small nickname table (Bob/Robert). A job needs at least a plausible name, email or relative to be a candidate, so click timing alone never creates one.
4. **Decide.** The first rule that fires wins:
   - **No match:** junk, no candidates, or the top score is under 40.
   - **Needs review (low):** the top two candidates are within 10 points.
   - **Matched, medium:** a likely winner with doubt. The top identity is only a partial name, email or relative; a runner-up has a stronger identity; a signal on the top candidate contradicts it (a negative signal, or a click after the review); the score is under 60; or the margin is under 30.
   - **Matched, high:** everything else.

Every row in `results.csv` carries the decision reason. Every matched or needs-review row also carries the top candidate's signals with points and the runner-up (PRD R9), and a *needs review* row lists the runner-up's signals too. [`no_match.csv`](findings/no_match.csv) repeats the 4 no-match rows with only their reason.

## Results

| Outcome | Reviews |
| --- | --- |
| Matched, high | 21 |
| Matched, medium | 10 |
| Needs review (low) | 5 (R06, R18, R19, R21, R23) |
| No match | 4 (R28, R30, R31, R32) |

All 40 reviews have exactly one outcome and a reason (PRD R1, R2). The tests pass, including the cases below.

## Discussion cases

| Review | Outcome | What it shows |
| --- | --- | --- |
| **R13** Carlos Mendoza | Medium, J013 "Carlos Mendoza Ruiz" | J013 has only a close name (+30) but a click 26.5h earlier and a matching electrical service. The better name match, J075, is a plumbing job and loses 30 points. Timing and service beat name, and the medium flags that a runner-up had the stronger name. |
| **R18** John Smith, **R21** Daniel Kim | Needs review | Repeat customers with the same exact name. R18's J018 scores 75 against J019's 65 (clicks at 3.0h and 25.5h). Ten points is too close to call, so a person decides. |
| **R19** Patricia Nguyen | Needs review | J040 scores 65 and J039 scores 55. J039 has a click 0.2h before the review but its service doesn't match the text. A strong signal pointing at a weaker job is exactly when not to force a pick. |
| **R29** Brian Wright | Medium, J029 | The name is exact and the service matches, but the link was clicked *after* the review was posted. That contradiction keeps it at medium. |
| **R34** Vincent Romano | High, J032 | High only because "Sparkle Plumbing" (a competitor named in the text) hits the plumbing keyword, which happens to match J032. Without those 20 points it would be medium. The keyword lists have no notion of other businesses. |
| **R03** and **R07** (Jennifer Walsh, "Jenifer Walsh") | High and medium, both J003 | The typo (R07, close name +30) lowers the score to 50. Two reviews of one job are allowed (PRD R8). R29 and R38 ("Mary Wright" writing about her son Brian) also share J029. |
| **R37** Lisa Stevens | Medium, J035 "Lisa O'Connor" | No job has this name. Only the email local part (`lstevens@...`) and a click 0.5h earlier point at J035. Medium because the identity is not a name. |
| **R33** ACME Industries Inc | High, J031 "ACME Industries" | The business suffix is stripped, so the names match exactly. |
| **R36** Rebecca Stone | High, J034 | J034 is `estimate_only`, yet it is the right job (name plus a click 0.2h before the review). Excluding such jobs would have lost it (PRD R6). |
| **R28**, **R31**, **R32** | No match | "Test review please ignore", a handle ("no job matches the author's name, email or a named relative"), and a placeholder author ("John Doe"). Leaving a review unmatched is a valid result. R30 is a painting review for a business that does no painting. |

## Limits

- **The thresholds and weights were chosen after looking at the scores of these 40 reviews, with no labels.** The 21/10/5/4 split looks good here by construction. "High" is not proven correct.
- **Service keywords are a short list**, and they match word beginnings, so unrelated words can hit them (R34 above). A classifier would be the upgrade.
- **5 of 40 reviews (12.5%) go to a person.** PRD open question 1 asks whether about 10% is acceptable. A tighter margin would shrink the queue and let R18, R19 and R21 through as matched. That is a business decision, not a coding one.
- **Two pairs of reviews resolve to one job each** (R03/R07 and R29/R38). The PRD allows it, but a person should confirm.
- **The mutation counts are not in the repo.** An external harness (not committed) made 296 small changes to the matcher and the tests caught all but 15, which were judged to have no effect on behavior. Those numbers are as reported, not repo-verifiable. What the repo does show: breaking a click weight or a name weight makes `test_matcher.py` fail.

- **`test_matcher.py` mostly pins today's results.** Its 21/10/5/4 counts and per-review expectations are a regression snapshot of this sample, not a measure of accuracy. R34 is the weak spot of the "high" label: score 75, no runner-up, and the evidence includes a keyword hit that came from a competitor.
- **The future-date rule uses the real clock.** Reviews dated after today are junk, so R28 stops being caught by that rule once today passes 2027-02-15. Its "test review" text still catches it, and no other review is future-dated.

## What I'd do next

- Put a job token in review-request links. That removes most of the guessing.
- Turn the *needs review* queue into labeled data, then fit the weights from reviewer corrections.
- Add address matching if the real system has addresses (the sample has only the city).
