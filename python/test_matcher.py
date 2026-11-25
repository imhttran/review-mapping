"""Assertion checks for python/matcher.py, run as unittest tests.

  python3 python/test_matcher.py                  # or: python3 -m unittest   (from the project root)
  MATCHER=/path/to/matcher.py python3 python/test_matcher.py   # check a broken copy (mutation test)

One test per check group; a failing group prints one FAIL line per broken case.

Where each tricky case from docs/findings/dataset_analysis.md is guarded (table name + review id, or an
`expect` label; grep for the literal):
  typo (Jenifer)            EXPECTED_TOP / EXPECTED_MEDIUM R07; check_names "typo" label
  first name only (Mike)    EXPECTED_MEDIUM R08
  initial (J., K., Sarah J.) EXPECTED_MEDIUM R10, R20, R15
  swapped order             EXPECTED_HIGH R16; check_names "swapped order" label
  nickname                  NICKNAME_PAIRS (check_names)
  business suffix (R33)     EXPECTED_HIGH R33; check_names "ACME Industries Inc", "Acme Corp"
  no job under the name     EXPECTED_MEDIUM R37
  test review, placeholder, handle   EXPECTED_NO_MATCH R28, R32, R31; "test review beats painting"
  job started after review  RULED_OUT R03, R12, R25, R26
  click right after post    EXPECTED_TOP R05, R27, R36, R40, R01; EXPECTED_HIGH R14 (decision only); click tier cases
  repeat customer, timing only   EXPECTED_REVIEW R18 (3h vs 25.5h, from the findings doc), R19; AMBIGUOUS
  review posted before click     EXPECTED_MEDIUM R29 ("link clicked after the review")
  estimate-only job stays a candidate   EXPECTED_HIGH R36 (J034)
  timing beating exact name      "timing beats name" (click timing), "stronger runner-up cap"; R13 (timing + service)
"""
import csv
import importlib.util
import io
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_matcher(path=None):
    path = path or Path(__file__).with_name("matcher.py")
    spec = importlib.util.spec_from_file_location("matcher", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NICKNAME_PAIRS = [
    ("Bob", "Robert"), ("Tom", "Thomas"), ("Mike", "Michael"), ("Bill", "William"),
    ("Jim", "James"), ("Jen", "Jennifer"), ("Dave", "David"), ("Dan", "Daniel"),
    ("Chris", "Christopher"), ("Liz", "Elizabeth"), ("Joe", "Joseph"), ("Steve", "Stephen"),
]

# (review name, job name, level, reason or None to skip the reason check)
NAME_CASES = [
    ("José Hernández", "Jose Hernandez", "exact", "same name"),
    ("Maria Lopez-Garcia", "Maria Lopez Garcia", "exact", "same name"),
    ("Lisa O'Connor", "Lisa OConnor", "exact", "same name"),
    ("Bob Miller", "Robert Miller", "exact", "nickname"),
    ("Bob Miller", "Bob Miller", "exact", "same name"),
    ("Yamamoto Henry", "Henry Yamamoto", "exact", "swapped order"),
    ("ACME Industries Inc", "ACME Industries", "exact", "same name"),
    ("Linda Garcia", "Linda M Garcia", "exact", "same name"),
    ("John Smith Jr", "John Smith Jr", "exact", "same name"),
    ("Tom Anderson", "Tom Anderson", "exact", "same name"),
    ("Tom Anderson", "Thomas Anderson", "exact", "nickname"),
    ("Acme Co", "Acme", "exact", "same name"),  # pins the accepted "co" suffix limit
    ("Lisa O\u2019Connor", "Lisa OConnor", "exact", "same name"),  # curly apostrophe
    ("Jenifer Walsh", "Jennifer Walsh", "close", "typo"),
    ("Carlos Mendoza", "Carlos Mendez", "close", "typo"),
    ("Maria Lopez", "Maria Lopez Garcia", "close", "extra name token"),
    ("Carlos Mendoza", "Carlos Mendoza Ruiz", "close", "extra name token"),
    ("John Smith Jr", "John Smith", "close", "Jr/Sr differs"),
    ("John Smith", "John Smith Jr", "close", "Jr/Sr differs"),
    ("John Smith Jr", "John Smith Sr", "close", "Jr/Sr differs"),
    ("J. Anderson", "James Anderson", "partial", None),
    ("K. Anderson", "Karen Anderson", "partial", None),
    ("Sarah J.", "Sarah Johnson", "partial", None),
    ("Mike", "Mike Chen", "partial", None),
    ("Mike", "Michael Chen", "partial", None),
    ("B. Miller", "Bob Miller", "partial", None),  # initial vs a nickname-mapped first name
    ("Mark Davis", "Mark Davies", "close", "typo"),  # 1-edit surname under 6 letters
    ("Karen Smith", "Karan Smith", "close", "typo"),  # 5-letter first name allows 1 edit
    ("Maria Lopez Garcia", "Maria Lopez", "close", "extra name token"),
    ("ABC LLC", "ABC", "exact", "same name"),
    ("Smith Ltd", "Smith", "exact", "same name"),
    ("Acme Corp", "Acme", "exact", "same name"),
    ("Anderson", "Karen Anderson", "partial", None),  # last name only
    ("K. Anderson", "James Anderson", "none", None),
    ("J. Anderson", "Karen Anderson", "none", None),
    ("J. Anderson", "Tom Anderson", "none", None),
    ("Sarah J.", "Sarah Chen", "none", None),
    ("Sarah J.", "Sandra Johnson", "none", None),
    ("Sarah Johnson", "Sandra Johnson", "none", None),
    ("Sarah Johnson", "Sara Johnson", "none", None),
    ("Linda Garcia", "Linda Martinez", "none", None),
    ("Tom Anderson", "James Anderson", "none", None),
    ("Mark Davis", "Mark Stevens", "none", None),
    ("Mark Davis", "Mary Davis", "none", None),
    ("Tomás García", "Thomas Brown", "none", None),
    ("Anna Reed", "Anna Rood", "none", None),  # 2-edit surname under 6 letters
    ("Maria Johnson", "Maria Jackson", "none", None),  # 3-edit surname, 6+ letters
    ("Maria Lopez", "Maria Lopezzz", "none", None),  # 2 edits, shorter surname is 5 letters
    ("Mark Smith", "Marc Smith", "none", None),  # 4-letter first name allows no edits
    ("Inc", "John Smith", "none", "empty name"),
    ("Mike", "Jr", "none", "empty name"),
    ("Mike", "Chen", "none", None),
    ("J. Smith", "J. Smithson", "none", "initial does not fit"),
    ("Mike Chen", "Chen", "none", None),  # a one-token job name never matches by subset
    ("Karen Smith", "Kxxen Smith", "none", None),  # 2-edit first name at 5+ letters
    ("Sarah J.", "Sarah Jane Lee", "none", None),  # initials only match two-token jobs
    ("J Robert Smith", "James Robert Smith", "none", None),  # leading initial is kept
    ("John Smith J", "John Smith Jones", "none", None),  # trailing initial is kept
    ("Karen Smith", "Waren Smith", "none", None),  # first letter must match
    ("Anna Maria Lopez", "Anna Marie Lopez", "none", None),  # middle tokens must match
    ("Maria Lopez Jr", "Maria Lopez Garcia", "none", "Jr/Sr differs"),
    ("Jenifer Walsh Jr", "Jennifer Walsh", "none", "Jr/Sr differs"),
    ("J. Anderson Jr", "James Anderson", "none", "Jr/Sr differs"),
    ("Smith Jr", "John Smith", "none", "Jr/Sr differs"),
    ("John Smith Jr", "Smith John", "none", None),
    ("Jon Smith Jr", "John Smith", "none", None),
]


def check_names(m):
    failures = []
    for review, job, level, reason in NAME_CASES:
        got = m.name_match(review, job)
        want = "%s / %s" % (level, reason or "any reason")
        if got[0] != level or (reason and got[1] != reason):
            failures.append("name_match(%r, %r) = %s, wanted %s" % (review, job, got, want))
    # Every nickname pair, spelled out here (not read from the module, or a bad entry would pass).
    for nick, full in NICKNAME_PAIRS:
        got = m.name_match("%s Doe" % nick, "%s Doe" % full)
        if got != ("exact", "nickname"):
            failures.append("nickname %s -> %s: got %s" % (nick, full, got))
    if len(m.NICKNAMES) != len(NICKNAME_PAIRS):
        failures.append("NICKNAMES has %d entries, test_matcher.py lists %d" % (len(m.NICKNAMES), len(NICKNAME_PAIRS)))
    return failures


def check_levenshtein(m):
    failures = []
    for a, b, want in (("kitten", "sitting", 3), ("henderson", "sanders", 4), ("abc", "xbc", 1), ("xabc", "abc", 1), ("abc", "bc", 1), ("", "abc", 3), ("same", "same", 0)):
        if m.levenshtein(a, b) != want:
            failures.append("levenshtein(%r, %r) = %d, wanted %d" % (a, b, m.levenshtein(a, b), want))
    return failures


def check_dates(m):
    failures = []
    day, dt = m.parse_ts("2026-05-28"), m.parse_ts("2026-05-28T00:00:00Z")
    if day != dt or day.tzinfo is None or day.utcoffset().total_seconds() != 0:
        failures.append("parse_ts: date and UTC datetime should be the same aware UTC value")
    if m.parse_ts("2026-06-02T14:30:00Z") != datetime(2026, 6, 2, 14, 30, tzinfo=timezone.utc):
        failures.append("parse_ts: UTC datetime keeps its time")
    off = m.parse_ts("2026-06-02T10:00:00-04:00")  # aware datetimes compare by instant, so check the offset too
    if off.utcoffset().total_seconds() != 0 or off.hour != 14:
        failures.append("parse_ts: an offset should convert to UTC")
    if m.parse_ts("") is not None or m.parse_ts("  ") is not None:
        failures.append("parse_ts: blank should be None")
    try:
        m.parse_ts("not-a-date")
        failures.append("parse_ts: 'not-a-date' should raise")
    except ValueError as e:
        if "not-a-date" not in str(e):
            failures.append("parse_ts: error should contain the bad value")
    return failures


NOW_ISO = "2026-11-24T00:00:00Z"
# Spelled out here (not read from the module, or a deleted entry would still pass).
TEST_WORDS = ["test review"]
OTHER_SERVICE_WORDS = ["paint", "painter", "painters", "painted", "painting", "landscape", "landscaping",
                       "landscaper", "landscapers", "lawn", "pest", "fence", "pool"]
OFFERED_STEMS = ["plumb", "hvac", "electric", "roof", "remodel", "bathroom", "kitchen"]
# Review ids whose name candidates include a job that started after the review (sample-specific).
RULED_OUT = {"R03": ["J041"], "R12": ["J053"], "R13": ["J051"], "R15": ["J001"],
             "R17": ["J018", "J019"], "R25": ["J026"], "R26": ["J061"]}


def check_filters(m):
    failures = []
    now = m.parse_ts(NOW_ISO)
    reviews = m.load_reviews()
    by_id = dict((r["review_id"], r) for r in reviews)

    def rev(text, author="Pat Lee", posted="2026-05-01T00:00:00Z"):
        return {"review_text": text, "author_name": author, "posted_at": m.parse_ts(posted)}

    junk_cases = [
        ("R28", by_id["R28"], "test review"),
        ("R30", by_id["R30"], "service not offered"),
        ("R32", by_id["R32"], "placeholder author"),
        ("QA Test author", rev("Great work", author="QA Test"), "placeholder author"),
        ("QA-Test author", rev("Great work", author="QA-Test"), "placeholder author"),
        ("future date", rev("Great work", posted="2026-11-25T00:00:00Z"), "posted in the future"),
        ("placeholder before future", rev("Great work", author="John Doe", posted="2026-11-25T00:00:00Z"), "placeholder author"),
        ("R31 handle", by_id["R31"], None),
        ("R34 competitor", by_id["R34"], None),
        ("R24 business author", by_id["R24"], None),
        ("R33 business author", by_id["R33"], None),
        ("exactly now", rev("Great work", posted=NOW_ISO), None),
        ("Doe John", rev("Great work", author="Doe John"), None),
        ("John Doe Jr", rev("Great work", author="John Doe Jr"), None),
        ("latest review", rev("Please check the latest review I posted"), None),
        ("carpool", rev("Easy to schedule around our carpool"), None),
        ("pesto", rev("Smelled like pesto all day, but great work"), None),
        ("remodel mentions paint", rev("Great bathroom remodel, they even painted the walls"), None),
        ("blank text and author", {"review_text": "", "author_name": "", "posted_at": m.parse_ts("2026-05-01")}, None),
        ("missing text and author", {"posted_at": None}, None),
        ("missing every key", {}, None),
        ("now is a parameter", rev("Great work", posted="2026-05-20T00:00:00Z"), "posted in the future", m.parse_ts("2026-05-15")),
        ("please ignore the mess", rev("Please ignore the mess, they cleaned it well"), None),
        ("test review beats painting", rev("Test review, painting"), "test review"),
        ("placeholder beats painting", rev("Great painting", author="John Doe"), "placeholder author"),
        ("future beats painting", rev("Great painting", posted="2026-11-25T00:00:00Z"), "posted in the future"),
        ("offered stem must start a word", rev("Painters did a great job, loved the subroof"), "service not offered"),
    ]
    for case in junk_cases:
        label, review, want = case[:3]
        got = m.junk_reason(review, case[3] if len(case) > 3 else now)
        if got != want:
            failures.append("junk_reason %s = %r, wanted %r" % (label, got, want))
    for phrase in TEST_WORDS:
        if m.junk_reason(rev("This is a %s, thanks" % phrase), now) != "test review":
            failures.append("junk_reason: test phrase %r not flagged" % phrase)
    for word in OTHER_SERVICE_WORDS:
        if m.junk_reason(rev("They did the %s work" % word), now) != "service not offered":
            failures.append("junk_reason: other service %r not flagged" % word)
    for stem in OFFERED_STEMS:
        if m.junk_reason(rev("The painters and the %sing crew" % stem), now) is not None:
            failures.append("junk_reason: offered stem %r should keep the review" % stem)
    if (len(m.TEST_PHRASES), len(m.OTHER_SERVICES), len(m.OFFERED_WORDS)) != (len(TEST_WORDS), len(OTHER_SERVICE_WORDS), len(OFFERED_STEMS)):
        failures.append("junk word lists changed size; update test_matcher.py")
    real_now = datetime.now(timezone.utc)  # default now is the real clock, not a constant
    for delta, want in ((timedelta(days=1), "posted in the future"), (-timedelta(days=1), None)):
        r = {"review_text": "Great work", "author_name": "Pat Lee", "posted_at": real_now + delta}
        if m.junk_reason(r) != want:
            failures.append("junk_reason default now: %s from now gave %r, wanted %r" % (delta, m.junk_reason(r), want))
    if m.junk_reason(rev("Great work", posted="2999-01-01T00:00:00Z")) != "posted in the future":
        failures.append("junk_reason default now: a year-2999 review should be future")
    if m.junk_reason(rev("Great work", posted="2026-05-01T00:00:00Z")) is not None:
        failures.append("junk_reason default now: a 2026-05 review should not be junk")
    junk = sorted(r["review_id"] for r in reviews if m.junk_reason(r, now))
    if junk != ["R28", "R30", "R32"]:
        failures.append("junk set over the sample = %s, wanted R28, R30, R32" % junk)

    jobs = m.load_jobs()
    for r in reviews:
        _, out = m.eligible_jobs(r, jobs)
        named = sorted(j["job_id"] for j in out if m.name_match(r["author_name"], j["customer_name"])[0] != "none")
        if named != RULED_OUT.get(r["review_id"], []):
            failures.append("eligible_jobs %s ruled out name candidates %s, wanted %s" % (r["review_id"], named, RULED_OUT.get(r["review_id"], [])))
    if "J028" not in [j["job_id"] for j in m.eligible_jobs(by_id["R27"], jobs)[0]]:
        failures.append("eligible_jobs: J028 (same-day start) should be eligible for R27")

    job = {"job_id": "X", "job_started_at": m.parse_ts("2026-05-28")}
    for posted, want_eligible in (("2026-05-28T00:00:00Z", True), ("2026-05-27T23:59:59Z", False)):
        eligible, out = m.eligible_jobs(rev("x", posted=posted), [job])
        if bool(eligible) != want_eligible or bool(out) == want_eligible:
            failures.append("eligible_jobs boundary at %s: eligible=%s" % (posted, bool(eligible)))
    unknown = {"job_id": "Y", "job_started_at": None}
    if m.eligible_jobs(rev("x"), [unknown]) != ([unknown], []):
        failures.append("eligible_jobs: a job with no start time should be kept")
    if m.eligible_jobs({}, [job]) != ([job], []):
        failures.append("eligible_jobs: a review with no posted_at key rules out nothing")
    if m.eligible_jobs({"posted_at": None}, [job]) != ([job], []):
        failures.append("eligible_jobs: a review with no posted_at rules out nothing")
    return failures


# Sample-specific expectations for the real reviews (top job and its exact score).
EXPECTED_TOP = {"R01": ("J001", 105), "R03": ("J003", 60), "R05": ("J005", 105), "R07": ("J003", 50),
                "R09": ("J009", 85), "R13": ("J013", 75), "R15": ("J015", 50), "R17": ("J017", 65),
                "R27": ("J028", 105), "R35": ("J033", 55), "R36": ("J034", 105), "R37": ("J035", 95),
                "R38": ("J029", 55), "R39": ("J036", 95), "R40": ("J038", 115)}
# Genuinely ambiguous: only a small margin is asserted (phase 4 turns these into "needs review").
AMBIGUOUS = {"R06": None, "R18": None, "R19": {"J040", "J039"}, "R21": None, "R23": {"J013", "J051"}}
SERVICE_WORDS = {
    "HVAC": ["hvac", "furnace", "heat wave", "air condition", "thermostat", "ac", "a/c"],
    "plumbing": ["plumb", "leak", "sink", "pipe", "water heater", "drain", "toilet", "faucet"],
    "electrical": ["electric", "panel", "wiring", "rewir", "breaker", "outlet"],
    "roofing": ["roof", "shingle"],
    "bathroom remodel": ["bathroom"],
    "kitchen remodel": ["kitchen"],
}
RELATION_WORDS = ["husband", "wife", "son", "daughter", "mother", "father", "mom", "dad", "brother", "sister",
                  "neighbor", "friend", "tenant", "boss"]
JOB_KEYS = ("job_id", "customer_name", "customer_phone", "customer_email", "service_city", "service_type",
            "job_started_at", "review_requested_at", "review_link_clicked_at", "photo_count", "job_status", "crew_member")


POSTED = datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)


def job(**over):
    """A completed plumbing job for Pat Lee, started 2026-01-01; override any field."""
    base = dict.fromkeys(JOB_KEYS, None)
    base.update(job_id="X", customer_name="Pat Lee", customer_email="", service_type="plumbing",
                job_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc), job_status="completed", crew_member="")
    base.update(over)
    return base


def rev(text="", author="Pat Lee", at=POSTED):
    return {"review_text": text, "author_name": author, "posted_at": at}


def expecter(failures):
    def expect(label, got, want):
        if got != want:
            failures.append("%s: got %r, wanted %r" % (label, got, want))
    return expect


def check_scoring(m):
    failures = []
    posted = POSTED

    def signal(candidates, name):
        if not candidates:  # no candidate at all means no signal
            return []
        return [(r[1], r[2]) for r in candidates[0]["reasons"] if r[0] == name]

    expect = expecter(failures)

    def points(candidates, name):
        return [p for p, _ in signal(candidates, name)]

    def ago(**kw):
        return posted - timedelta(**kw)

    # Click tiers: inclusive upper bounds at 1h, 6h, 48h, 168h.
    for seconds, want in ((0, [40]), (3600, [40]), (3601, [30]), (21600, [30]), (21601, [20]), (172800, [20]),
                          (172801, [10]), (604800, [10]), (604801, [])):
        c = m.score_candidates(rev(), [job(review_link_clicked_at=ago(seconds=seconds))])
        expect("click %ds before" % seconds, points(c, "click"), want)
    after = signal(m.score_candidates(rev(), [job(review_link_clicked_at=ago(seconds=-60))]), "click")
    expect("click after the review", after, [(0, "link clicked after the review")])

    # Request: +10 only with no click at all, within 72h inclusive; -20 when posted before the request.
    for seconds, want in ((0, [10]), (259200, [10]), (259201, [])):
        expect("request %ds before" % seconds,
               points(m.score_candidates(rev(), [job(review_requested_at=ago(seconds=seconds))]), "request"), want)
    expect("a click after the review still suppresses the request bonus",
           points(m.score_candidates(rev(), [job(review_requested_at=ago(hours=10), review_link_clicked_at=ago(seconds=-60))]), "request"), [])
    expect("a click suppresses the request bonus",
           points(m.score_candidates(rev(), [job(review_requested_at=ago(hours=10), review_link_clicked_at=ago(hours=9))]), "request"), [])
    expect("posted before the request", points(m.score_candidates(rev(), [job(review_requested_at=ago(seconds=-60))]), "request"), [-20])
    expect("posted before the request, with a click",
           points(m.score_candidates(rev(), [job(review_requested_at=ago(seconds=-60), review_link_clicked_at=ago(hours=1))]), "request"), [-20])

    # Recent: 0 to 30 x 24h inclusive.
    for delta, want in ((timedelta(0), [5]), (timedelta(days=30), [5]), (timedelta(days=30, seconds=1), [])):
        expect("job started %s before" % delta, points(m.score_candidates(rev(), [job(job_started_at=posted - delta)]), "recent"), want)

    # Service: match, mismatch, none, multi-service, remodel specificity, pattern edges.
    def services(text):
        return dict((c["job_id"], points([c], "service")) for c in m.score_candidates(
            rev(text), [job(job_id=t, service_type=t) for t in
                        ("HVAC", "plumbing", "electrical", "roofing", "bathroom remodel", "kitchen remodel")]))
    expect("service match and mismatch", services("They fixed the leak fast")["plumbing"], [20])
    mismatch = signal(m.score_candidates(rev("They fixed the leak fast"), [job(service_type="HVAC")]), "service")
    expect("service mismatch reason", (mismatch[0][0], "plumbing" in mismatch[0][1] and "HVAC" in mismatch[0][1]), (-30, True))
    expect("no service words", points(m.score_candidates(rev("Great crew, thanks"), [job()]), "service"), [])
    multi = services("Quick repair on the kitchen sink")
    expect("multi-service", (multi["plumbing"], multi["kitchen remodel"], multi["HVAC"], multi["bathroom remodel"]), ([20], [20], [-30], [-30]))
    kitchen, bathroom, generic = services("The kitchen reno went well"), services("Our bathroom remodel is lovely"), services("We did a full remodel")
    expect("kitchen reno", (kitchen["kitchen remodel"], kitchen["bathroom remodel"]), ([20], [-30]))
    expect("bathroom remodel", (bathroom["bathroom remodel"], bathroom["kitchen remodel"]), ([20], [-30]))
    expect("generic remodel counts for both types", (generic["bathroom remodel"], generic["kitchen remodel"], generic["plumbing"]), ([20], [20], [-30]))
    for text, service in (("The AC broke down", "HVAC"), ("Their a/c work was great", "HVAC"), ("Came through the heatwave", "HVAC"),
                          ("Came through the heat wave", "HVAC"), ("They rewired our garage", "electrical")):
        expect("pattern %r" % text, services(text)[service], [20])
    for text in ("Nice pace of work", "They came back twice", "A bleak outlook", "It was unplumbed", "Fixed our sunroof glare",
                 "They were actually fine", "Across the street", "Marcus Moreno was great"):
        expect("no service in %r" % text, [v for v in services(text).values() if v], [])

    # Every service word, spelled out here so a deleted entry is caught.
    for service, words in SERVICE_WORDS.items():
        for word in words:
            expect("service word %r" % word, services("They did the %s work" % word)[service], [20])

    # Crew: whole word, non-blank.
    expect("crew named", points(m.score_candidates(rev("Eric was great"), [job(crew_member="Eric")]), "crew"), [10])
    expect("crew inside a longer word", points(m.score_candidates(rev("Ericsson was great"), [job(crew_member="Eric")]), "crew"), [])
    expect("whitespace crew against a double space", points(m.score_candidates(rev("great  job"), [job(crew_member="  ")]), "crew"), [])
    expect("padded crew name", points(m.score_candidates(rev("Eric was great"), [job(crew_member=" Eric ")]), "crew"), [10])
    expect("crew left boundary", points(m.score_candidates(rev("a generic reply"), [job(crew_member="Eric")]), "crew"), [])
    for blank in ("", None, "  "):
        expect("blank crew %r" % blank, points(m.score_candidates(rev("Anything at all"), [job(crew_member=blank)]), "crew"), [])

    # Identity: name levels, best-of (not first, not sum), email and relative sources.
    for author, want in (("Pat Lee", 40), ("Pat Lea", 30), ("Pat", 15)):
        expect("identity for author %r" % author, points(m.score_candidates(rev(author=author), [job()]), "identity"), [want])
    expect("partial name + relative: best is the relative",
           points(m.score_candidates(rev("My husband Pat loved it", author="Pat"), [job()]), "identity"), [20])
    expect("exact name + email key stays 40",
           points(m.score_candidates(rev(), [job(customer_email="plee@email.com")]), "identity"), [40])
    lisa = m.score_candidates(rev(author="Lisa Stevens"), [job(customer_name="Lisa O'Connor", customer_email="lstevens@email.com")])
    expect("email source", [(c["job_id"], signal([c], "identity")[0][0]) for c in lisa], [("X", 30)])
    expect("email source needs two full names",
           (m.score_candidates(rev(author="Lisa"), [job(customer_name="Zed Quux", customer_email="lstevens@email.com")]),
            m.score_candidates(rev(author="Sarah J."), [job(customer_name="Zed Quux", customer_email="sjohnson@email.com")])), ([], []))
    other = lambda text, name: points(m.score_candidates(rev(text, author="Zed Quux"), [job(customer_name=name)]), "identity")
    expect("relative: husband Carlos", other("My husband Carlos had you out", "Carlos Mendoza"), [20])
    expect("relative: son Brian", other("My son Brian needed help", "Brian Wright"), [20])
    expect("relative: Bob matches Robert", other("my husband Bob called", "Robert Miller"), [20])
    expect("relative: Bob matches Bob", other("my husband Bob called", "Bob Miller"), [20])
    expect("relative: Robert matches Bob", other("my husband Robert called", "Bob Miller"), [20])
    expect("relative: lowercase word", other("my husband was away", "Carlos Mendoza"), [])
    expect("relative: lowercase name", other("my husband carlos was away", "Carlos Mendoza"), [])
    expect("relative: no name", other("my husband loved it", "Carlos Mendoza"), [])

    # More service patterns, relation words and email keys (each kills a specific mutant).
    both = services("We had plumbing done during the remodel")
    expect("generic remodel next to another service", (both["bathroom remodel"], both["kitchen remodel"], both["plumbing"], both["HVAC"]), ([20], [20], [20], [-30]))
    expect("reno counts for both remodel types", (services("It was a big reno")["bathroom remodel"], services("It was a big reno")["kitchen remodel"]), ([20], [20]))
    expect("outlet is electrical", services("A dead outlet in the hall")["electrical"], [20])
    expect("thermostat is HVAC", services("Our thermostat died")["HVAC"], [20])
    for word in RELATION_WORDS:
        expect("relation word %r" % word, other("My %s Dana had you out" % word, "Dana Fox"), [20])
    stevens = lambda author, email: m.score_candidates(rev(author=author), [job(customer_name="Zed Quux", customer_email=email)])
    expect("email key: initial with a surname is too short", stevens("L. Stevens", "lstevens@email.com"), [])
    expect("email key: surname initial is too short", stevens("Lisa S.", "lisas@email.com"), [])
    expect("email key: one-token author", stevens("Lisa", "llisa@email.com"), [])
    expect("email key: first+last", points(stevens("Lisa Stevens", "lisastevens@email.com"), "identity"), [30])
    expect("email key: digits in the local part are ignored", points(stevens("Carlos Mendoza", "cmendoza2@email.com"), "identity"), [30])
    expect("email is case-insensitive", points(stevens("Lisa Stevens", "LSTEVENS@EMAIL.COM"), "identity"), [30])
    expect("two-letter names: initial key", points(stevens("Al Li", "ali@email.com"), "identity"), [30])
    expect("two-letter names: full key", points(stevens("Al Li", "alli@email.com"), "identity"), [30])
    expect("email uses the raw first name", (points(stevens("Bob Miller", "bobmiller@email.com"), "identity"),
                                              points(stevens("Bob Miller", "bmiller@email.com"), "identity"),
                                              stevens("Bob Miller", "rmiller@email.com")), ([30], [30], []))
    for blank in (None, ""):
        expect("blank customer_name %r" % blank,
               (m.score_candidates(rev(), [job(customer_name=blank)]),
                m.score_candidates(rev("My husband Carlos had you out", author="Zed Quux"), [job(customer_name=blank)])), ([], []))
    tie = signal(m.score_candidates(rev(author="Pat Lea"), [job(customer_email="plea@email.com")]), "identity")
    expect("tie between name close and email names the name", (tie[0][0], "name close" in tie[0][1]), (30, True))
    both_ids = signal(m.score_candidates(rev("My husband Pat loved it"), [job()]), "identity")
    expect("exact name + relative keeps the name", (both_ids[0][0], "name exact (same name)" in both_ids[0][1]), (40, True))
    expect("a job that started after the review is not scored", m.score_candidates(rev(), [job(job_started_at=posted + timedelta(seconds=1))]), [])

    # Pool and shape.
    expect("no identity gives no candidates", m.score_candidates(rev(author="Nobody Here"), [job()]), [])
    tied = m.score_candidates(rev(), [job(job_id="B"), job(job_id="A")])
    expect("ties sort by job_id", [c["job_id"] for c in tied], ["A", "B"])
    for label, review in (("empty review", {}), ("no posted_at", rev("The leak was fixed", at=None))):
        try:
            m.score_candidates(review, [job(customer_email=None, crew_member=None)])
        except Exception as e:
            failures.append("%s raised %r" % (label, e))
    expect("no posted_at skips timing signals",
           [r[0] for r in m.score_candidates(rev(at=None), [job(review_link_clicked_at=ago(hours=1))])[0]["reasons"]], ["identity"])

    # Real reviews (sample-specific).
    reviews = dict((r["review_id"], r) for r in m.load_reviews())
    jobs = m.load_jobs()
    for rid, want in EXPECTED_TOP.items():
        c = m.score_candidates(reviews[rid], jobs)
        expect("%s top candidate" % rid, (c[0]["job_id"], c[0]["score"]) if c else None, want)
    for rid, top_two in AMBIGUOUS.items():
        c = m.score_candidates(reviews[rid], jobs)
        expect("%s margin is small" % rid, c[0]["score"] - c[1]["score"] <= 10, True)
        if top_two:
            expect("%s top two" % rid, set(x["job_id"] for x in c[:2]), top_two)
    expect("R01 candidates", dict((c["job_id"], c["score"]) for c in m.score_candidates(reviews["R01"], jobs)),
           {"J001": 105, "J014": 65, "J015": 65, "J055": 15})
    expect("R31 has no candidates", m.score_candidates(reviews["R31"], jobs), [])
    return failures


# Sample-specific decisions for the real reviews (job id, or None).
EXPECTED_HIGH = {"R01": "J001", "R02": "J002", "R03": "J003", "R04": "J004", "R05": "J005", "R09": "J009",
                 "R11": "J011", "R12": "J012", "R14": "J014", "R16": "J016", "R17": "J017", "R22": "J023",
                 "R24": "J024", "R25": "J025", "R26": "J027", "R27": "J028", "R33": "J031",
                 "R34": "J032", "R36": "J034", "R39": "J036", "R40": "J038"}
# review id: (job id, substrings that must all appear in the decision reasons, before the signal lines)
EXPECTED_MEDIUM = {"R07": ("J003", ("score 50",)), "R08": ("J008", ("name partial", "identity is not an exact or close name match")), "R10": ("J010", ("name partial",)),
                   "R13": ("J013", ("stronger identity",)), "R15": ("J015", ("name partial",)), "R20": ("J020", ("name partial",)),
                   "R29": ("J029", ("contradicts", "link clicked after the review")),
                   "R35": ("J033", ("margin 15",)), "R37": ("J035", ("email local part",)),
                   "R38": ("J029", ("relative", "stronger identity"))}
EXPECTED_REVIEW = {"R06": ("J006", "J007"), "R18": ("J018", "J019"), "R19": ("J040", "J039"),
                   "R21": ("J021", "J022"), "R23": ("J013", "J051")}
EXPECTED_NO_MATCH = {"R28": "test review", "R30": "service not offered", "R32": "placeholder author",
                     "R31": "no job matches the author's name, email or a named relative"}
DECISION_KEYS = {"outcome", "confidence", "job_id", "runner_up", "candidates", "reasons"}
OUTCOME_CONFIDENCE = {"matched": {"high", "medium"}, "needs review": {"low"}, "no match": {"none"}}


def check_decisions(m):
    failures = []
    now = m.parse_ts(NOW_ISO)
    posted = POSTED

    expect = expecter(failures)

    def causes(d):
        """The decision reasons: everything before the top candidate's own signal lines."""
        out = []
        for r in d["reasons"]:
            if r.startswith("identity: "):
                break
            out.append(r)
        return out

    def has(d, text):
        """Is `text` in a decision reason (not just in a signal line)?"""
        return any(text in r for r in causes(d))

    def margin(review, jobs):
        c = m.score_candidates(review, jobs)
        return c[0]["score"] - c[1]["score"]

    def label(d):
        return (d["outcome"], d["confidence"])

    recent = posted - timedelta(days=10)

    click = posted - timedelta(minutes=30)

    # Floor: 35 is thin, 40 is not under the floor.
    d = m.decide(rev("They fixed the leak", author="Pat"), [job()], now)
    expect("partial + service = 35", (label(d), d["job_id"], d["reasons"][0]),
           (("no match", "none"), None, "best candidate X scores 35, below the floor of 40"))
    expect("floor result keeps the top candidate's signals, after the decision reason", d["reasons"][1:],
           ["identity: name partial (first or last name only) (+15)", "service: text matches plumbing (+20)"])
    pair = [job(job_id="A", customer_name="Pat Lee"), job(job_id="B", customer_name="Pat Fox")]
    d = m.decide(rev("Great work", author="Pat"), pair, now)
    expect("two candidates under the floor beat the margin rule (rule order)", (label(d), d["candidates"]), (("no match", "none"), [("A", 15), ("B", 15)]))
    d = m.decide(rev("They fixed the leak", author="Pat"), [job(job_started_at=recent)], now)
    expect("partial + service + recent = 40", (label(d), d["job_id"]), (("matched", "medium"), "X"))

    # Margins: needs review at 10 or less, medium under 30, high from 30. The margin is asserted first.
    two = lambda a, b: [job(job_id="A", **a), job(job_id="B", **b)]
    cases = (
        ("margin 10", rev(), two({}, dict(customer_name="Pat Lea")), 10, ("needs review", "low")),
        ("margin 15", rev(), two(dict(job_started_at=recent), dict(customer_name="Pat Lea")), 15, ("matched", "medium")),
        ("margin 25", rev("They fixed the leak"),
         two(dict(job_started_at=recent, review_link_clicked_at=posted - timedelta(hours=40)), {}), 25, ("matched", "medium")),
        ("margin 30", rev("They fixed the leak"),
         two(dict(review_link_clicked_at=posted - timedelta(hours=5)), {}), 30, ("matched", "high")),
    )
    for name, review, jobs, want_margin, want_label in cases:
        expect(name + " fixture", margin(review, jobs), want_margin)
        d = m.decide(review, jobs, now)
        expect(name, label(d), want_label)
        expect(name + " runner_up", d["runner_up"], "B")
        if want_label == ("matched", "high"):
            expect(name + " reason", d["reasons"][0], "clear winner, score 90, margin 30")
    d = m.decide(rev(), two({}, dict(customer_name="Pat Lea")), now)
    expect("needs review has no job", (d["job_id"], d["candidates"], d["reasons"][0]),
           (None, [("A", 40), ("B", 30)], "top two candidates are within 10 points: A 40, B 30"))
    expect("needs review shows both candidates' signals",
           ("identity: name exact (same name) (+40)" in d["reasons"], "runner-up B: identity: name close (typo) (+30)" in d["reasons"]), (True, True))
    d = m.decide(rev(), two(dict(job_started_at=recent), dict(customer_name="Pat Lea")), now)
    expect("margin cause is named", has(d, "margin 15 is under 30"), True)

    # High score boundary, with a lone candidate (no margin to apply).
    d = m.decide(rev("They fixed the leak"), [job()], now)
    expect("lone exact + service = 60", (label(d), d["runner_up"]), (("matched", "high"), None))
    d = m.decide(rev("They fixed the leak", author="Pat Lea"), [job(review_link_clicked_at=click)], now)
    expect("a lone close name can be high", (label(d), d["job_id"]), (("matched", "high"), "X"))
    d = m.decide(rev(), [job(job_started_at=recent, review_requested_at=posted - timedelta(hours=10))], now)
    expect("lone exact + recent + request = 55", (label(d), has(d, "score 55 is under 60")), (("matched", "medium"), True))

    # Caps: a weak identity, or a runner-up with a stronger one, keeps a wide win at medium.
    d = m.decide(rev("They fixed the leak", author="Lisa Stevens"),
                 [job(customer_name="Lisa O'Connor", customer_email="lstevens@email.com", review_link_clicked_at=click)], now)
    expect("email-only cap", (label(d), has(d, "identity is not an exact or close name match (email local part"),
                              "identity: email local part matches the author (+30)" in d["reasons"]),
           (("matched", "medium"), True, True))
    d = m.decide(rev("My husband Carlos had you out about a leak", author="Zed Quux"),
                 [job(customer_name="Carlos Mendoza", review_link_clicked_at=click)], now)
    expect("relative-only cap", (label(d), has(d, "relative")), (("matched", "medium"), True))
    jobs = two(dict(customer_name="Pat Lea", review_link_clicked_at=click), {})
    review = rev("They fixed the leak")
    expect("stronger-runner-up fixture", margin(review, jobs), 30)
    d = m.decide(review, jobs, now)
    expect("stronger runner-up cap", (label(d), d["job_id"], has(d, "stronger identity")), (("matched", "medium"), "A", True))
    # Timing beating an exact name match (pure click-timing example): A has only a close name, but its click
    # 30 minutes before the post wins it the job over B's exact name. Real-data version: R13 (timing + service).
    top, other = m.score_candidates(review, jobs)
    pts = lambda c, name: [r[1] for r in c["reasons"] if r[0] == name]
    expect("timing beats name", (top["job_id"], pts(top, "click"), pts(top, "identity"), pts(other, "identity")),
           ("A", [40], [30], [40]))

    # A stronger identity anywhere among the runners-up caps at medium, even at index 2.
    jobs = [job(job_id="A", customer_name="Pat Lea", review_link_clicked_at=click), job(job_id="B", customer_name="Pat Leo"),
            job(job_id="C", service_type="HVAC")]
    review = rev("They fixed the leak")
    expect("third candidate fixture", [(c["job_id"], c["score"]) for c in m.score_candidates(review, jobs)], [("A", 90), ("B", 50), ("C", 10)])
    d = m.decide(review, jobs, now)
    expect("a stronger identity at index 2", (label(d), d["job_id"], has(d, "stronger identity")), (("matched", "medium"), "A", True))
    jobs = [job(job_id="A", customer_name="Pat Lea", review_link_clicked_at=click), job(job_id="B", customer_name="Pat Leo"),
            job(job_id="C", customer_name="Pat Lei", service_type="HVAC"),
            job(job_id="D", service_type="HVAC", review_requested_at=posted + timedelta(minutes=1))]
    expect("fourth candidate fixture", [(c["job_id"], c["score"]) for c in m.score_candidates(review, jobs)],
           [("A", 90), ("B", 50), ("C", 0), ("D", -10)])
    d = m.decide(review, jobs, now)
    expect("a stronger identity at index 3", (label(d), d["job_id"], has(d, "stronger identity")), (("matched", "medium"), "A", True))

    # A contradicting signal on the top candidate keeps a strong match at medium.
    for name, over, text in (("click after the review", dict(review_link_clicked_at=posted + timedelta(hours=1), job_started_at=recent), "link clicked after the review"),
                             ("posted before the request", dict(review_link_clicked_at=click, review_requested_at=posted + timedelta(minutes=1)),
                              "review posted before the request was sent")):
        d = m.decide(rev("They fixed the leak"), [job(**over)], now)
        expect(name, (label(d), has(d, "a signal contradicts the match (%s)" % text)), (("matched", "medium"), True))
    d = m.decide(rev("They fixed the leak"), [job(job_started_at=recent, review_link_clicked_at=click)], now)
    expect("no contradiction stays high", label(d), ("matched", "high"))

    # Junk and no candidates.
    d = m.decide(rev("Test review"), [job()], now)
    expect("junk", (label(d), d["reasons"]), (("no match", "none"), ["test review"]))
    d = m.decide(rev("Great work", at=m.parse_ts("2026-11-25T00:00:00Z")), [job()], now)
    expect("future review", (label(d), d["reasons"]), (("no match", "none"), ["posted in the future"]))
    d = m.decide(rev(author="Nobody Here"), [job()], now)
    expect("no candidates", (label(d), d["reasons"]), (("no match", "none"), [EXPECTED_NO_MATCH["R31"]]))

    # Shape.
    many = [job(job_id=str(i), customer_name="Pat Lee" if i < 2 else "Pat Lea") for i in range(4)]
    for label_, review, jobs in (("matched", rev("They fixed the leak"), [job()]), ("needs review", rev(), many),
                                 ("no match", rev("Test review"), [job()])):
        d = m.decide(review, jobs, now)
        expect(label_ + " keys", set(d), DECISION_KEYS)
        expect(label_ + " mapping", d["confidence"] in OUTCOME_CONFIDENCE[d["outcome"]], True)
    d = m.decide(rev(), many, now)
    expect("at most three candidates", len(d["candidates"]), 3)
    d = m.decide(rev("They fixed the leak"), [job()], now)
    expect("signals in the reasons", "identity: name exact (same name) (+40)" in d["reasons"], True)
    expect("a high decision says why", d["reasons"][0], "clear winner, score 60")
    for review in ({}, {"review_text": None, "author_name": None, "posted_at": None}):
        try:
            expect("empty review is a no match", label(m.decide(review, [job()], now)), ("no match", "none"))
        except Exception as e:
            failures.append("decide raised %r on %r" % (e, review))

    # Real reviews (sample-specific).
    reviews = dict((r["review_id"], r) for r in m.load_reviews())
    jobs = m.load_jobs()
    out = dict((rid, m.decide(r, jobs, now)) for rid, r in reviews.items())
    expect("every review has one outcome", len(out), 40)
    for rid, job_id in EXPECTED_HIGH.items():
        expect("%s high" % rid, (label(out[rid]), out[rid]["job_id"]), (("matched", "high"), job_id))
    for rid, (job_id, causes_) in EXPECTED_MEDIUM.items():
        expect("%s medium" % rid, (label(out[rid]), out[rid]["job_id"], all(has(out[rid], c) for c in causes_)),
               (("matched", "medium"), job_id, True))
    for rid, pair in EXPECTED_REVIEW.items():
        expect("%s needs review" % rid, (label(out[rid]), out[rid]["job_id"], tuple(j for j, _ in out[rid]["candidates"][:2])),
               (("needs review", "low"), None, pair))
        expect("%s is never high" % rid, out[rid]["confidence"] != "high", True)
    for rid, reason in EXPECTED_NO_MATCH.items():
        expect("%s no match" % rid, (label(out[rid]), out[rid]["reasons"]), (("no match", "none"), [reason]))
    totals = {}
    for d in out.values():
        totals[d["outcome"]] = totals.get(d["outcome"], 0) + 1
    expect("totals", totals, {"matched": 31, "needs review": 5, "no match": 4})
    expect("high count", sum(1 for d in out.values() if d["confidence"] == "high"), 21)
    return failures


def check_results(m):
    failures = []
    reviews, jobs = m.load_reviews(), m.load_jobs()
    rows = m.result_rows(reviews, jobs)
    job_ids = {j["job_id"]: j["customer_name"] for j in jobs}
    columns = ("review_id", "author_name", "outcome", "confidence", "job_id", "customer_name", "runner_up", "reasons")
    if tuple(m.RESULT_COLUMNS) != columns:
        failures.append("results: columns are %r" % (m.RESULT_COLUMNS,))
    if [r["review_id"] for r in rows] != [r["review_id"] for r in reviews]:
        failures.append("results: not one row per review, in input order")
    allowed = {"matched": ("high", "medium"), "needs review": ("low",), "no match": ("none",)}
    for r in rows:
        who = r["review_id"]
        if r["confidence"] not in allowed.get(r["outcome"], ()):
            failures.append("results: %s has %s/%s" % (who, r["outcome"], r["confidence"]))
        if r["outcome"] == "matched":
            if job_ids.get(r["job_id"]) != r["customer_name"] or not r["customer_name"]:
                failures.append("results: %s customer %r does not belong to %s" % (who, r["customer_name"], r["job_id"]))
        elif r["job_id"] or r["customer_name"]:
            failures.append("results: %s is not matched but has a job or customer" % who)
        if r["runner_up"] and (r["runner_up"] not in job_ids or r["runner_up"] == r["job_id"]):
            failures.append("results: %s runner-up %r is not another job" % (who, r["runner_up"]))
        if not r["reasons"]:
            failures.append("results: %s has no reasons" % who)
    # Each row is exactly what decide() says: outcome, confidence, job, runner-up and the full reasons.
    for review, r in zip(reviews, rows):
        d = m.decide(review, jobs)
        got = (r["outcome"], r["confidence"], r["job_id"], r["runner_up"], r["reasons"])
        want = (d["outcome"], d["confidence"], d["job_id"] or "", d["runner_up"] or "", " | ".join(d["reasons"]))
        if got != want:
            failures.append("results: %s row differs from decide(): got %r, wanted %r" % (r["review_id"], got, want))
    # A comma, quote and newline in a reason survive the CSV round trip.
    tricky = [dict(rows[0], reasons='a, "b"\nc | d')]
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=m.RESULT_COLUMNS)
    writer.writeheader()
    writer.writerows(tricky)
    if list(csv.DictReader(io.StringIO(buf.getvalue(), newline=""))) != tricky:
        failures.append("results: a tricky reason does not round-trip through the CSV writer")
    # The file on disk is what the matcher gives now (catches a stale results.csv).
    on_disk = Path(__file__).resolve().parent.parent / "docs" / "findings" / "results.csv"
    if not on_disk.exists():
        failures.append("results: results.csv is missing (run python3 python/matcher.py)")
    else:
        with open(on_disk, newline="", encoding="utf-8") as f:
            if list(csv.DictReader(f)) != rows:
                failures.append("results: results.csv is stale (run python3 python/matcher.py)")
    return failures


def check_loaders(m):
    # Sample-specific counts. Runs last so a name or date failure shows first.
    failures = []
    jobs, reviews = m.load_jobs(), m.load_reviews()
    if (len(jobs), len(reviews)) != (100, 40):
        failures.append("loaders: wanted 100 jobs and 40 reviews, got %d and %d" % (len(jobs), len(reviews)))
    for rows, fields in ((jobs, ("job_started_at", "review_requested_at", "review_link_clicked_at")), (reviews, ("posted_at",))):
        for row in rows:
            for field in fields:
                if row[field] is not None and not isinstance(row[field], datetime):
                    failures.append("loaders: %s not parsed in %r" % (field, row))
    return failures


class MatcherChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matcher = load_matcher(os.environ.get("MATCHER"))

    def run_group(self, check):
        try:
            failures = check(self.matcher)
        except Exception as e:  # a crash is a failure too, reported by name
            failures = ["%s crashed: %r" % (check.__name__, e)]
        if failures:
            self.fail("\n" + "\n".join("FAIL: " + f for f in failures))

    def test_names(self):
        self.run_group(check_names)

    def test_levenshtein(self):
        self.run_group(check_levenshtein)

    def test_dates(self):
        self.run_group(check_dates)

    def test_filters(self):
        self.run_group(check_filters)

    def test_scoring(self):
        self.run_group(check_scoring)

    def test_decisions(self):
        self.run_group(check_decisions)

    def test_results(self):
        self.run_group(check_results)

    def test_loaders(self):
        self.run_group(check_loaders)


if __name__ == "__main__":
    unittest.main()
