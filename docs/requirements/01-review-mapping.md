# PRD: Review-to-Job Mapping

· Plan: [plans/01-review-mapping.md](../plans/01-review-mapping.md)

## Problem

Our customers are home service businesses. After a job we ask the homeowner for a review on Google, Facebook and similar sites. A review comes back with only a display name, a timestamp, a star rating and free text. There is no job ID, email or phone number.

We need to know **which job (and customer) each review is about**, to credit the right crew, follow up on bad reviews and report review rates. Sometimes that is obvious. Often it isn't. A wrong match is worse than no match: it credits the wrong crew, can send the wrong customer a follow-up and corrupts the numbers.

## Scope

- **In:** map each review to a job, with a confidence level and a reason. The sample is 40 reviews and 100 jobs in `data/` (profile: [dataset_analysis.md](../findings/dataset_analysis.md)). Some job fields are blank. Output is a file or report.
- **Out:** adding a job token to review-request links (a strong follow-up), fetching reviews from Google or Facebook, auto-replying to reviews, a UI, ML models (no labeled data yet), address matching (the sample has only the city).

## Requirements

**Must**

- **R1:** Every review gets one outcome: a matched job, _needs review_ (candidates too close to call) or _no match_. Junk, test and other-business reviews get _no match_ with a reason.
- **R2:** Every outcome has a confidence level and the reasons behind it, so a person can check it without re-deriving it.
- **R3:** Never match a review to a job that hadn't started when the review was posted.
- **R5:** Tolerate messy names: accents, hyphens, initials, nicknames, swapped order, business suffixes, typos.
- **R6:** Cancelled, estimate-only and in-progress jobs stay candidates. Unhappy and estimate-only customers do leave reviews.
- **R8:** Allow more than one review per job (several sites, or several people in a household).

**Should**

- **R7:** Handle reviews written about someone else ("my husband Carlos had your team out...").
- **R9:** Show the runner-up candidate.
- **R10:** Use service clues in the text ("leak", "breaker panel") and crew names.

## Confidence levels

- **High:** one clear winner. Outcome: matched.
- **Medium:** a likely winner with some doubt. Outcome: matched, flagged for a quick check.
- **Low:** candidates too close to call. Outcome: _needs review_, never a forced pick.
- **None:** nothing plausible, or junk. Outcome: _no match_.

## Success

- All 40 reviews have an outcome and a reason.
- The check script's tricky cases pass (for example, timing beating an exact name match).
- No high-confidence match contradicts a check case.

## Open questions

1. **Coverage vs precision.** Is a 10% manual-review queue acceptable, or is the bar higher? This sets the confidence thresholds.
2. **Shared contact details.** When a household shares a phone and email, is it one customer?
3. **Old jobs.** Is there a cutoff after which a job is no longer a candidate? The sample has reviews posted over a year after the job.
4. **Address data.** Is the address available in the real system? It would settle property-manager reviews ("the rental at 1247 Cedar").
