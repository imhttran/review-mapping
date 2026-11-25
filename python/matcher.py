"""The review matcher so far: load the data, parse timestamps, compare names (phase 1),
and filter out junk reviews and jobs that hadn't started yet (phase 2).

Standard library only. Name comparison reports a level and a reason; it never
picks a job. Scoring, timing signals and outcomes come in later phases.
"""
import csv
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Small and visible on purpose. Applied to the first name only.
NICKNAMES = {
    "bob": "robert", "tom": "thomas", "mike": "michael", "bill": "william",
    "jim": "james", "jen": "jennifer", "dave": "david", "dan": "daniel",
    "chris": "christopher", "liz": "elizabeth", "joe": "joseph", "steve": "stephen",
}
# ponytail: "co" is also dropped from a person's name (surname Co); fine for this sample.
BUSINESS_SUFFIXES = {"inc", "llc", "ltd", "corp", "co"}
GENERATIONS = {"jr", "sr"}


def parse_ts(s):
    """A date or UTC datetime -> aware UTC datetime. Blank -> None."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        # Python < 3.11 rejects a trailing Z, so swap it first.
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("bad timestamp: %r" % s)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _load(filename, ts_fields):
    with open(DATA / filename, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for field in ts_fields:
            row[field] = parse_ts(row[field])
    return rows


def load_jobs():
    return _load("jobs.csv", ("job_started_at", "review_requested_at", "review_link_clicked_at"))


def load_reviews():
    return _load("reviews.csv", ("posted_at",))


def levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def normalize(name):
    """-> (tokens, jr/sr flag or None, first token before nickname mapping)."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("'", "").replace("’", "")
    tokens = re.sub(r"[^a-z0-9]+", " ", s).split()  # hyphens and punctuation become spaces
    tokens = [t for t in tokens if t not in BUSINESS_SUFFIXES]
    generation = next((t for t in tokens if t in GENERATIONS), None)
    tokens = [t for t in tokens if t not in GENERATIONS]
    if len(tokens) >= 3:  # middle initial; with two tokens a letter is an initial, so keep it
        tokens = [t for i, t in enumerate(tokens) if not (len(t) == 1 and 0 < i < len(tokens) - 1)]
    raw_first = tokens[0] if tokens else ""
    if tokens:
        tokens[0] = NICKNAMES.get(tokens[0], tokens[0])
    return tokens, generation, raw_first


def name_match(review_name, job_name):
    """Compare a review author to a job customer. -> (level, reason).

    Levels: exact, close, partial, none. The first rule that fires wins.
    """
    r, r_gen, r_raw = normalize(review_name)
    j, j_gen, j_raw = normalize(job_name)
    if not r or not j:
        return "none", "empty name"

    # 4. Same tokens.
    if r == j:
        if r_gen != j_gen:
            return "close", "Jr/Sr differs"
        return "exact", "nickname" if r_raw != j_raw else "same name"

    # 5. Same tokens, different order. Exact tokens only.
    if sorted(r) == sorted(j):
        return ("exact", "swapped order") if r_gen == j_gen else ("none", "swapped order, Jr/Sr differs")

    # A Jr/Sr mismatch rules out every weaker match below.
    if r_gen != j_gen:
        return "none", "Jr/Sr differs"

    # 6. One token, or an initial, on the review side.
    if len(r) == 1:
        if r[0] in (j[0], j[-1]):
            return "partial", "first or last name only"
        return "none", "single name does not match"
    if len(r) == 2 and (len(r[0]) == 1 or len(r[1]) == 1):
        if len(j) == 2:
            for i in (0, 1):
                first_ok = j[i].startswith(r[i]) or (i == 0 and j_raw.startswith(r[0]))
                if len(r[i]) == 1 and first_ok and r[1 - i] == j[1 - i]:
                    return "partial", "initial"
        return "none", "initial does not fit"

    # 7. One name's tokens are a proper subset of the other's.
    if len(r) >= 2 and len(j) >= 2 and (set(r) < set(j) or set(j) < set(r)):
        return "close", "extra name token"

    # 8. Typo in the first name or surname.
    # ponytail: edit allowances are a guess tuned on 40 reviews; tune from reviewer corrections.
    if len(r) == len(j) >= 2 and r[0][0] == j[0][0] and r[1:-1] == j[1:-1]:
        first_allowed = 1 if min(len(r[0]), len(j[0])) >= 5 else 0
        last_allowed = 2 if min(len(r[-1]), len(j[-1])) >= 6 else 1
        if levenshtein(r[0], j[0]) <= first_allowed and levenshtein(r[-1], j[-1]) <= last_allowed:
            return "close", "typo"

    return "none", "different name"


# --- Phase 2: filters ---------------------------------------------------------
# ponytail: these lists are small and tuned to the 40-review sample. They err toward
# missing junk, because a wrongly junked review is dropped for good. Upgrade path: larger
# lists, or a classifier fit on reviewer corrections.
TEST_PHRASES = ("test review",)
PLACEHOLDER_AUTHORS = {"qa test", "john doe"}
# Services we don't offer, as whole words.
OTHER_SERVICES = (
    "paint", "painter", "painters", "painted", "painting",
    "landscape", "landscaping", "landscaper", "landscapers", "lawn", "pest", "fence", "pool",
)
# Word stems for services we do offer. A hit here stops the "service not offered" rule, so a
# remodel review that mentions painting is kept. A false hit only means a missed junk.
OFFERED_WORDS = ("plumb", "hvac", "electric", "roof", "remodel", "bathroom", "kitchen")


def _has_word(text, words):
    return re.search(r"\b(?:%s)\b" % "|".join(re.escape(w) for w in words), text) is not None


def junk_reason(review, now=None):
    """Why a review should not be matched to any job, or None. First rule that fires wins."""
    now = now or datetime.now(timezone.utc)
    text = (review.get("review_text") or "").lower()
    if _has_word(text, TEST_PHRASES):
        return "test review"
    tokens, generation, _ = normalize(review.get("author_name") or "")
    # Joined tokens drop business suffixes and map the first token through NICKNAMES.
    if generation is None and " ".join(tokens) in PLACEHOLDER_AUTHORS:
        return "placeholder author"
    posted = review.get("posted_at")
    if posted is not None and posted > now:
        return "posted in the future"
    if _has_word(text, OTHER_SERVICES) and not re.search(r"\b(?:%s)" % "|".join(OFFERED_WORDS), text):
        return "service not offered"
    return None


def eligible_jobs(review, jobs):
    """Split jobs into (eligible, ruled_out). Ruled out = the job started after the review was
    posted (PRD R3). Plain-date starts are midnight UTC, so a same-day review is never ruled out.
    A job or review with an unknown time can't be ruled out."""
    posted = review.get("posted_at")
    eligible, ruled_out = [], []
    for job in jobs:
        start = job["job_started_at"]
        if posted is not None and start is not None and start > posted:
            ruled_out.append(job)
        else:
            eligible.append(job)
    return eligible, ruled_out


# --- Phase 3: scoring ---------------------------------------------------------
# Each signal adds points with a reason. Scoring ranks candidates; it never picks an outcome.
# ponytail: the weights, click tiers and service map are tuned on the 40-review sample with
# no labels, so they may be overfit. Upgrade path: tune from reviewer corrections.
NAME_POINTS = {"exact": 40, "close": 30, "partial": 15}
EMAIL_POINTS = 30
RELATIVE_POINTS = 20
CLICK_TIERS = ((1, 40), (6, 30), (48, 20), (168, 10))  # (hours before the review, inclusive; points)
REQUEST_POINTS, REQUEST_WINDOW_HOURS, BEFORE_REQUEST_POINTS = 10, 72, -20
RECENT_POINTS, RECENT_DAYS = 5, 30
CLICK_AFTER_REVIEW = "link clicked after the review"
SERVICE_MATCH_POINTS, SERVICE_MISMATCH_POINTS, CREW_POINTS = 20, -30, 10

# Stems match at a word start, so "electricity" also hits "electric": a known false positive.
SERVICE_PATTERNS = {
    "HVAC": r"\b(?:hvac|furnace|heat ?wave|air condition|thermostat)|\bac\b|\ba/c\b",
    "plumbing": r"\b(?:plumb|leak|sink|pipe|water heater|drain|toilet|faucet)",
    "electrical": r"\b(?:electric|panel|wiring|rewir|breaker|outlet)",
    "roofing": r"\b(?:roof|shingle)",
    "bathroom remodel": r"\bbathroom",
    "kitchen remodel": r"\bkitchen",
}
# "remodel" and "reno" name no room, so they count for both remodel types, but only when the
# text names neither bathroom nor kitchen.
GENERIC_REMODEL = r"\b(?:remodel|reno)"
REMODELS = {"bathroom remodel", "kitchen remodel"}
RELATIVE_RE = re.compile(
    r"\b(?i:my (?:husband|wife|son|daughter|mother|father|mom|dad|brother|sister|neighbor|friend|tenant|boss))"
    r"\s+([A-Z][a-z]+)"
)


def services_in(text):
    """The set of our service types a review text points to."""
    low = text.lower()
    found = {service for service, pattern in SERVICE_PATTERNS.items() if re.search(pattern, low)}
    if re.search(GENERIC_REMODEL, low) and not (found & REMODELS):
        found |= REMODELS
    return found


def _first_name(name):
    """First name after normalize (accents, nickname map), or None. Mapping both sides makes
    "Bob" and "Robert" equal."""
    tokens, _, _ = normalize(name or "")
    return tokens[0] if tokens else None


def _email_keys(author):
    """Keys like 'lisastevens' and 'lstevens' from an author with a full first and last name."""
    tokens, _, raw_first = normalize(author or "")
    if len(tokens) < 2 or len(raw_first) < 2 or len(tokens[-1]) < 2:
        return set()
    return {raw_first + tokens[-1], raw_first[0] + tokens[-1]}


def _identity(author, job, email_keys, relative):
    """Best (points, reason) for 'is this job about this author', or None. Ties keep the first
    source in the order name, email, relative."""
    best = None
    level, why = name_match(author, job.get("customer_name") or "")
    if level != "none":
        best = (NAME_POINTS[level], "name %s (%s)" % (level, why))
    local = re.sub(r"[^a-z]", "", (job.get("customer_email") or "").split("@")[0].lower())
    # A partial name never has an email key and a close name ties at 30, so email only counts
    # when no name matched.
    if local and local in email_keys and best is None:
        best = (EMAIL_POINTS, "email local part matches the author")
    if relative and _first_name(relative) == _first_name(job.get("customer_name")) and (best is None or RELATIVE_POINTS > best[0]):
        best = (RELATIVE_POINTS, "text names a relative called %s" % relative)
    return best


def _timing(posted, job):
    """Click, request and recency signals for a review posted at `posted` (an aware datetime)."""
    reasons = []
    click, requested, started = job["review_link_clicked_at"], job["review_requested_at"], job["job_started_at"]
    if click is not None:
        hours = (posted - click).total_seconds() / 3600
        if hours < 0:
            reasons.append(("click", 0, CLICK_AFTER_REVIEW))
        else:
            for limit, points in CLICK_TIERS:
                if hours <= limit:
                    reasons.append(("click", points, "link clicked %.1fh before the review" % hours))
                    break
    if requested is not None:
        hours = (posted - requested).total_seconds() / 3600
        if hours < 0:
            reasons.append(("request", BEFORE_REQUEST_POINTS, "review posted before the request was sent"))
        elif click is None and hours <= REQUEST_WINDOW_HOURS:
            reasons.append(("request", REQUEST_POINTS, "request sent %.0fh before, no click" % hours))
    # Jobs that started after the review were already ruled out by eligible_jobs.
    if started is not None and (posted - started).total_seconds() <= RECENT_DAYS * 86400:
        reasons.append(("recent", RECENT_POINTS, "job started within %d days" % RECENT_DAYS))
    return reasons


def score_candidates(review, jobs):
    """Rank the jobs a review could be about. Returns [{"job_id", "score", "reasons"}],
    best first (ties by job_id). reasons is a list of (signal, points, text). Jobs that started
    after the review are ruled out first (eligible_jobs); jobs with no identity signal are not
    candidates. Jobs must carry all the CSV keys (None when blank)."""
    eligible, _ = eligible_jobs(review, jobs)
    text = review.get("review_text") or ""
    low = text.lower()
    posted = review.get("posted_at")
    author = review.get("author_name") or ""
    email_keys = _email_keys(author)
    match = RELATIVE_RE.search(text)
    relative = match.group(1) if match else None
    services = services_in(text)
    candidates = []
    for job in eligible:
        identity = _identity(author, job, email_keys, relative)
        if identity is None:
            continue
        reasons = [("identity",) + identity]
        if posted is not None:
            reasons += _timing(posted, job)
        if services:
            if job["service_type"] in services:
                reasons.append(("service", SERVICE_MATCH_POINTS, "text matches %s" % job["service_type"]))
            else:
                reasons.append(("service", SERVICE_MISMATCH_POINTS,
                                "text points to %s, job is %s" % ("/".join(sorted(services)), job["service_type"])))
        crew = (job.get("crew_member") or "").strip()
        if crew and re.search(r"\b%s\b" % re.escape(crew.lower()), low):
            reasons.append(("crew", CREW_POINTS, "crew member %s named" % crew))
        candidates.append({"job_id": job["job_id"], "score": sum(r[1] for r in reasons), "reasons": reasons})
    candidates.sort(key=lambda c: (-c["score"], c["job_id"]))
    return candidates


# --- Phase 4: confidence and outcomes ------------------------------------------
# ponytail: these thresholds were chosen after seeing the scores of 40 reviews, so the sample
# split looks good by construction. Upgrade path: tune from reviewer corrections.
NO_MATCH_FLOOR = 40   # a top score under this is too thin to name a job
REVIEW_MARGIN = 10    # top two within this many points: needs review
HIGH_SCORE = 60       # high confidence needs at least this score ...
HIGH_MARGIN = 30      # ... and at least this margin over the runner-up
NO_CANDIDATE_REASON = "no job matches the author's name, email or a named relative"


def _identity_of(candidate):
    """(points, reason) of a candidate's identity signal."""
    return next((points, text) for signal, points, text in candidate["reasons"] if signal == "identity")


def _decision(outcome, confidence, reasons, candidates, top=None, job_id=None, show_runner_up=False):
    """Assemble the result. reasons start with why this outcome, then the top candidate's signals,
    and for a needs-review the runner-up's signals too, so a reviewer sees what it was weighed against."""
    if top is not None:
        reasons = list(reasons) + ["%s: %s (%+d)" % (signal, text, points) for signal, points, text in top["reasons"]]
    if show_runner_up:
        reasons = list(reasons) + ["runner-up %s: %s: %s (%+d)" % (candidates[1]["job_id"], signal, text, points)
                                   for signal, points, text in candidates[1]["reasons"]]
    return {
        "outcome": outcome,
        "confidence": confidence,
        "job_id": job_id,
        "runner_up": candidates[1]["job_id"] if len(candidates) > 1 else None,
        "candidates": [(c["job_id"], c["score"]) for c in candidates[:3]],
        "reasons": list(reasons),
    }


def decide(review, jobs, now=None):
    """One outcome per review: matched (high or medium), needs review (low) or no match (none).
    The first rule that fires wins: junk, no candidates, thin evidence, a margin too small to
    call, then matched with the causes (if any) that keep it from high."""
    junk = junk_reason(review, now)
    if junk:
        return _decision("no match", "none", [junk], [])
    candidates = score_candidates(review, jobs)
    if not candidates:
        return _decision("no match", "none", [NO_CANDIDATE_REASON], [])
    top = candidates[0]
    second = candidates[1] if len(candidates) > 1 else None
    margin = top["score"] - second["score"] if second else None
    if top["score"] < NO_MATCH_FLOOR:
        return _decision("no match", "none", ["best candidate %s scores %d, below the floor of %d"
                                               % (top["job_id"], top["score"], NO_MATCH_FLOOR)], candidates, top)
    if second and margin <= REVIEW_MARGIN:
        return _decision("needs review", "low", ["top two candidates are within %d points: %s %d, %s %d"
                                                  % (REVIEW_MARGIN, top["job_id"], top["score"], second["job_id"], second["score"])],
                         candidates, top, show_runner_up=True)
    points, text = _identity_of(top)
    causes = []
    if not text.startswith(("name exact", "name close")):
        causes.append("identity is not an exact or close name match (%s)" % text)
    if any(_identity_of(c)[0] > points for c in candidates[1:]):
        causes.append("a runner-up has a stronger identity match")
    contradiction = next((text for _signal, pts, text in top["reasons"] if pts < 0 or text == CLICK_AFTER_REVIEW), None)
    if contradiction:
        causes.append("a signal contradicts the match (%s)" % contradiction)
    if top["score"] < HIGH_SCORE:
        causes.append("score %d is under %d" % (top["score"], HIGH_SCORE))
    if second and margin < HIGH_MARGIN:
        causes.append("margin %d is under %d" % (margin, HIGH_MARGIN))
    if causes:
        return _decision("matched", "medium", causes, candidates, top, top["job_id"])
    return _decision("matched", "high", ["clear winner, score %d%s" % (top["score"], "" if second is None else ", margin %d" % margin)],
                     candidates, top, top["job_id"])


RESULT_COLUMNS = ("review_id", "author_name", "outcome", "confidence", "job_id", "customer_name", "runner_up", "reasons")
RESULTS_PATH = DATA.parent / "results.csv"


def result_rows(reviews, jobs, now=None):
    """One row per review, in input order. job_id and customer_name are filled only for a matched review."""
    customer = {j["job_id"]: j["customer_name"] for j in jobs}
    rows = []
    for review in reviews:
        d = decide(review, jobs, now)
        rows.append({
            "review_id": review["review_id"], "author_name": review["author_name"],
            "outcome": d["outcome"], "confidence": d["confidence"],
            "job_id": d["job_id"] or "", "customer_name": customer.get(d["job_id"], ""),
            "runner_up": d["runner_up"] or "", "reasons": " | ".join(d["reasons"]),
        })
    return rows


def write_results(path=RESULTS_PATH):
    rows = result_rows(load_reviews(), load_jobs())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main():
    rows = write_results()
    counts = {}
    for r in rows:
        key = r["outcome"] if r["outcome"] != "matched" else "matched (%s)" % r["confidence"]
        counts[key] = counts.get(key, 0) + 1
    print("wrote %s: %s" % (RESULTS_PATH.name, ", ".join("%d %s" % (n, k) for k, n in sorted(counts.items()))))


if __name__ == "__main__":
    main()
