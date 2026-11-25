# Technology choice: Python

The matcher is written in **Python 3, standard library only**. This is a take-home that gets walked through on-site, so the code has to be easy to run and easy to explain out loud.

## Why Python

- **Nothing to install.** `python3 python/test_matcher.py` runs on any laptop. No package manager, build step or config.
- **The standard library covers every need:**

| Need | Standard library |
| --- | --- |
| Read both CSVs (review text has quoted commas) | `csv` |
| Parse dates and UTC datetimes | `datetime.fromisoformat` |
| Strip accents (José → Jose) | `unicodedata` |
| Tolerate typos (Jenifer → Jennifer) | Hand-written edit distance (`difflib` has none) |
| Tests | `unittest`, with plain comparisons and failure lists |

- **Short, readable rules.** The matching rules are small scoring functions. Less code means less to defend in the discussion.
- **Fits the project rules.** `AGENTS.md` requires Python 3, standard library only, with no new dependencies.

## Alternatives considered

| Option | Why not |
| --- | --- |
| **Go** | No standard-library accent stripping (needs `golang.org/x/text`) and no fuzzy string matching, so more hand-written code. Types and a single binary don't matter for 40 reviews |
| **TypeScript** | No CSV parser in the standard library. Needs Node plus a runner or `tsconfig`. Plain-date timezone handling in `Date` is easy to get wrong |

## When to revisit

If the matcher moves into a production service, port it to that service's language. The rules, signals and thresholds carry over unchanged. The choice here is about the exercise, not the product.
