# Data analysis findings

Quick profile of `data/jobs.csv` (100 rows) and `data/reviews.csv` (40 rows), done before building the matcher. Nothing was modified. Counts come from a throwaway stdlib script, not committed. Names were normalized (accents, hyphens, case) before comparing.

## Jobs

| Field | Finding |
| --- | --- |
| `job_id` | 100 unique |
| `customer_name` | 84 distinct, so repeat customers exist. Same-name pairs with the same service type: Sarah Johnson (plumbing x2), Daniel Kim (HVAC x2) |
| `customer_email` | 1 blank (J007). 87 distinct, so emails repeat across a customer's jobs (3x for sjohnson, dkim, pnguyen). Reviews have no email, so it can't be used to join |
| `job_status` | 94 completed, 3 in_progress, 2 cancelled, 1 estimate_only |
| `service_city` | Austin 70, Cedar Park 13, Round Rock 12, Pflugerville 5 |
| `service_type` | plumbing 36, HVAC 26, electrical 19, roofing 11, bathroom remodel 7, kitchen remodel 1 |
| `crew_member` | Marcus 33, Diego 27, Eric 26, Hector 11, three singletons |
| `review_requested_at` | 21 blank. Gap from job start is 0-3 days (up to ~10 at the top end). Only 1 request is dated 2025, the other 78 are 2026 |
| `review_link_clicked_at` | 45 blank, 55 clicked. Every click has a request (0 clicks without one) |
| `job_started_at` | 2024-08 to 2026-06, with 73 of 100 in 2026-05. Mix of dates and UTC datetimes |

Only 76 jobs are completed and have a request or click. Those are the realistic candidates for a review. The 6 non-completed jobs (J033, J034, J069, J076, J084, J094) are unlikely targets.

Names to normalize in jobs: `José Hernández`, `Tomás García`, `Lisa O'Connor`, `Megan O'Brien`.

## Reviews

| Field | Finding |
| --- | --- |
| `source` | google 39, facebook 1 |
| `rating` | 5-star 31, 4-star 7, 2-star 1, 1-star 1 |
| `author_name` | 39 distinct. Linda Garcia posted twice |
| `posted_at` | 2024-11 to 2027-02. R28 is dated 2027-02-15, after today (2026-11-24) |
| Contact fields | No email, phone or city on any review |

Text signals are sparse: 22 of 40 reviews mention a service type (plumbing, HVAC, ...), 5 name a crew member, 1 names a city.

## Matching-relevant findings

**Exact normalized name match against jobs (candidates per review):**

| Candidates | Reviews |
| --- | --- |
| 0 | 11 |
| 1 | 18 |
| 2 | 6 |
| 3 | 5 |

So 29 reviews have an exact-name candidate, but only 18 are unambiguous by name. The other 11 need other signals.

**Reviews with no exact-name candidate (11):**

| Review | Author | Kind | Note |
| --- | --- | --- | --- |
| R07 | Jenifer Walsh | typo | Likely Jennifer Walsh, 4-star bathroom remodel |
| R08 | Mike | first name only | Electrician, breaker panel |
| R10 | J. Anderson | initial | Garage wiring |
| R20 | K. Anderson | initial | Garage rewiring, a second Anderson review for what looks like similar work |
| R15 | Sarah J. | initial | Plumbing, same-day fix |
| R16 | Yamamoto Henry | swapped order | HVAC replacement |
| R37 | Lisa Stevens | no job under this name | Plumbing, could be a different person |
| R28 | QA Test | test data | "Test review please ignore", dated 2027 |
| R31 | happycustomer22 | handle | Generic text, no usable signal |
| R32 | John Doe | placeholder | "Great service.", no signal |
| R33 | ACME Industries Inc | business | Office HVAC, business suffix |

**Timing against link clicks** (exact-name pairs only):
- 7 reviews were posted within 30 minutes of the job's click (R05, R19, R27, R01, R14, R36, R40). This is the strongest signal in the data.
- 14 pairs fall within 0-48 hours after a click. Many cluster around 24 hours.
- For some repeat customers, timing is the only thing separating their jobs. Example: R18 matches a name on two jobs (J018 at 3h, J019 at 25.5h).
- R29 posted 48.5 hours *before* the click on J029, so name matches but timing doesn't.
- 4 reviews are posted before a same-name job started (R03 vs J041, R12 vs J053, R25 vs J026, R26 vs J061). Those jobs can be ruled out, which narrows the ambiguous ones.
- R36 and J034 pair up by name and click time, but J034 is `estimate_only`. Decided: J034 stays a candidate (PRD R6, implication 6).

## Implications for the matcher

1. Name alone isn't enough: 11 reviews have 2-3 same-name jobs.
2. Timing is the best disambiguator. Use click → post within ~48h, and rule out jobs that started after the review.
3. Name normalization needs: typos (Jenifer), initials (J., K., Sarah J.), swapped order, first-name-only, accents.
4. Some reviews should stay unmatched: R28 (test), R31 (handle), R32 (John Doe, no signal), and likely R33 and R37 unless text and timing line up. Never force a match.
5. Soft signals (service type in text, crew name, rating) are tie-breakers only: they are sparse and don't beat timing.
6. Keep cancelled, estimate_only and in_progress jobs as candidates (PRD R6): unhappy and estimate-only customers do leave reviews. Lower confidence only when timing or text contradicts the job.
