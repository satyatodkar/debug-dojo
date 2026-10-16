"""
test_api.py  —  Debug Dojo Phase 2 API tests
=============================================
Run with:  python3 test_api.py
(server must be running on localhost:8000)

No pytest needed — uses only the stdlib.
"""

import sys, os, json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0


def request(path):
    """Return (http_status, parsed_json_body)."""
    try:
        with urllib.request.urlopen(BASE + path, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def ok(description, passed, detail=""):
    global PASS, FAIL
    icon = "✓" if passed else "✗"
    msg  = f"  {icon}  {description}"
    if not passed and detail:
        msg += f"\n       → {detail}"
    print(msg)
    if passed:
        PASS += 1
    else:
        FAIL += 1


# ── 1. Health endpoint ──────────────────────────────────────────────────────
print("\n── Health endpoint ─────────────────────────────────────────")
status, body = request("/api/health")
ok("GET /api/health → 200", status == 200, f"Got {status}")
ok('{"status":"ok"} returned', body.get("status") == "ok", str(body))


# ── 2. Challenge list ───────────────────────────────────────────────────────
print("\n── GET /api/challenges ─────────────────────────────────────")
status, challenges = request("/api/challenges")
ok("Returns 200", status == 200, f"Got {status}")
ok("Returns a list", isinstance(challenges, list), str(type(challenges)))
ok("Contains exactly 10 challenges", len(challenges) == 10, f"Got {len(challenges)}")

EXPECTED_KEYS = {"id", "title", "difficulty", "tags"}
for ch in challenges:
    ok(f"  [{ch.get('id','??')}] has correct summary keys",
       set(ch.keys()) == EXPECTED_KEYS,
       f"Keys present: {set(ch.keys())}")

difficulties = {ch["difficulty"] for ch in challenges}
ok("At least 3 difficulty levels present", len(difficulties) >= 3,
   f"Found: {difficulties}")

all_tags = {tag for ch in challenges for tag in ch["tags"]}
ok("At least 4 distinct concept tags", len(all_tags) >= 4,
   f"Found: {all_tags}")

FORBIDDEN = {"description", "starter_code", "visible_tests", "hidden_tests", "tests"}
for ch in challenges:
    leak = set(ch.keys()) & FORBIDDEN
    ok(f"  [{ch['id']}] summary has no detail/hidden keys", not leak, f"Leaked: {leak}")


# ── 3. Challenge detail ─────────────────────────────────────────────────────
print("\n── GET /api/challenges/{id} ────────────────────────────────")
ids = [ch["id"] for ch in challenges]

for cid in ids:
    s, detail = request(f"/api/challenges/{cid}")
    ok(f"  [{cid}] returns 200", s == 200, f"Got {s}")

    required = {"id", "title", "difficulty", "tags", "description",
                "starter_code", "visible_tests"}
    ok(f"  [{cid}] has all required detail keys",
       required <= set(detail.keys()),
       f"Missing: {required - set(detail.keys())}")

    vis = detail.get("visible_tests", [])
    ok(f"  [{cid}] has >= 3 visible tests", len(vis) >= 3, f"Got {len(vis)}")

    for t in vis:
        ok(f"    [{cid}] visible test has label+call+expected",
           {"label", "call", "expected"} <= set(t.keys()),
           str(list(t.keys())))

    hidden_leaked = any(k in detail for k in ("hidden_tests", "hidden", "all_tests"))
    ok(f"  [{cid}] does NOT expose hidden tests", not hidden_leaked,
       f"Keys present: {list(detail.keys())}")


# ── 4. Unknown IDs → 404 ───────────────────────────────────────────────────
print("\n── Unknown challenge IDs → 404 ─────────────────────────────")
for bad in ("nope", "123", "count_PASSES", "hidden_tests"):
    s, _ = request(f"/api/challenges/{bad}")
    ok(f"  /api/challenges/{bad} → 404", s == 404, f"Got {s}")


# ── 5. Hidden test isolation (pure Python, no HTTP) ─────────────────────────
print("\n── Hidden test isolation (backend module check) ────────────")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from challenges import CHALLENGES, HIDDEN_TESTS

challenge_ids = {ch["id"] for ch in CHALLENGES}
hidden_ids    = set(HIDDEN_TESTS.keys())

ok("Hidden test keys match challenge ids exactly",
   challenge_ids == hidden_ids,
   f"Missing: {challenge_ids - hidden_ids}  |  Extra: {hidden_ids - challenge_ids}")

for cid, tests in HIDDEN_TESTS.items():
    ok(f"  [{cid}] has >= 5 hidden tests", len(tests) >= 5, f"Got {len(tests)}")
    for t in tests:
        ok(f"    [{cid}] hidden test has description+args+expected",
           {"description", "args", "expected"} <= set(t.keys()),
           str(list(t.keys())))


# ── Summary ─────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"\n{'═' * 55}")
print(f"  Results: {PASS}/{total} passed  |  {FAIL} failed")
print(f"{'═' * 55}\n")
sys.exit(0 if FAIL == 0 else 1)
