# Review Mapping Exercise

Match incoming customer reviews (Google, Facebook, etc.) to the home-service job and customer each one is about.

## Progress

| Step | Document | Status |
| --- | --- | --- |
| 1. Requirements | [docs/requirements/01-review-mapping.md](docs/requirements/01-review-mapping.md) | Done |
| 2. Plan | [docs/plans/01-review-mapping.md](docs/plans/01-review-mapping.md) | Done |
| 2a. Data analysis | [docs/findings/dataset_analysis.md](docs/findings/dataset_analysis.md) | Done |
| 3. Implementation | [python/](python/) (`matcher.py`, `test_matcher.py`) | Done: all 6 phases |
| 4. Results and writeup | [docs/writeup.md](docs/writeup.md), [results.csv](results.csv) | Done |

## Run

```
python3 python/matcher.py   # writes results.csv
python3 python/test_matcher.py   # assertion checks as unittest tests, ends with "OK"
python3 -m unittest          # same tests, from the project root
# MATCHER=/path/to/broken_copy.py python3 python/test_matcher.py   checks another copy of the matcher
```

## Inputs

The exercise data is not published in this repository. To run the code, put `reviews.csv` and `jobs.csv` (and, if you have it, the exercise prompt `README.md`) in `data/`. `results.csv` is the output from the original run.

- `data/reviews.csv`: 40 reviews
- `data/jobs.csv`: 100 jobs with review-request and click signals
- `data/README.md`: the original exercise prompt
- `data/analysis.ipynb`: exploratory notebook on both CSVs
- [docs/findings/dataset_analysis.md](docs/findings/dataset_analysis.md): written findings from the data analysis

## Technology

Python 3, standard library only. See [docs/technology_choice.md](docs/technology_choice.md) for why.
