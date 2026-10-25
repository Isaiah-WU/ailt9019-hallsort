# Install reproduction and documentation check (macOS)

Task: midterm contribution check assigned to YANG (Andi), 25 October 2026.
Scope: fresh-clone installation, documented commands, documented behaviour and document accuracy.
Out of scope: rule and signage correctness (LUO), independent test design (WANG), integration and submission (WU).

This record covers what was actually executed on this machine. Nothing below is inferred from the author's own run.

## 1. Environment

| Item | Value |
|---|---|
| Commit | `02d7c8a` (`main`, `origin/main`) |
| OS | macOS 27.0.1, build 26A434, arm64 |
| Python A | 3.12.13 (pyenv), new virtual environment |
| Python B | 3.13.12, separate virtual environment |
| Clone | fresh `git clone`, no cached environment, no prior `.venv` |
| API key | not used. AI mode was not exercised end to end |

## 2. Commands executed, in order

The documented steps, using the macOS interpreter path. `python3.12` is named explicitly because `python` on this machine resolves to 3.13, and 3.12 is the version the README states as tested.

```bash
git clone https://github.com/Isaiah-WU/ailt9019-hallsort.git
cd ailt9019-hallsort
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8019
```

Results:

| Step | Outcome |
|---|---|
| virtual environment creation | success, no warnings |
| `pip install -r requirements.txt` | success, 17 packages, `fastapi 0.162.0`, `uvicorn 0.54.0`, `httpx 0.28.1` |
| server start | `Application startup complete`, listening on `http://127.0.0.1:8019` |
| `GET /` | `200 text/html` |
| `GET /static/app.js`, `/static/style.css`, `/api/rules` | `200`, `2802 b`, `3554 b`, `5185 b` |
| `GET /api/info` | `llm_available: false`, `provider: OpenAI`, `rule_version: 2026-10-25.1` |

`pip freeze` after installing `requirements.txt` matches `requirements-lock.txt` line for line, except `colorama==0.4.6`, which the lock file lists and a macOS install does not pull in. The lock file is therefore accurate, not stale.

## 3. Documented behaviour, checked against the running server

| README claim | Observed | Match |
|---|---|---|
| `clean takeaway coffee cup set` returns three results, in order R08 Plastic, R09 Paper, R10 Beverage Cartons | `clean coffee cup lid / Plastic / R08`, `coffee cup sleeve / Paper / R09`, `clean paper coffee cup / Beverage Cartons / R10` | yes |
| `lithium battery` refuses and shows no bin | `status: refused`, `parts: []`, hazardous-waste message | yes |
| `office paper + mystery object` refuses instead of classifying only the known part | `status: refused`, `parts: []` | yes |
| AI mode without a key fails visibly | `status: unavailable`, message "AI mode is not configured..." | yes |
| Every result carries a server-owned source link | `source` and `source_title` populated from `rules.json`, never from the model | yes |
| `rules.json` holds 16 unique rule IDs with categories, text and official source URLs | 16 rules, 16 unique IDs, all fields non-empty, all sources on `www.wastereduction.hku.hk`, no dangling rule references from the 17 catalog items, no duplicate aliases | yes |
| Cited sources are live | both distinct URLs return `200` (poster PDF, photo guide) | yes |

## 4. Test and evaluation reruns

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python evaluate.py
```

| Run | Result |
|---|---|
| `pytest` on Python 3.12.13 | `20 passed, 1 warning in 0.35s` |
| `pytest` on Python 3.13.12 with `requirements-lock.txt` | `20 passed, 1 warning in 0.28s` |
| `evaluate.py` | `Catalog regression: 36/36 passed. Live LLM: not tested.` exit code 0 |

The single warning is `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`. It is the same warning recorded in `evidence/unit_tests.txt` and does not affect any result.

The rerun reproduces the committed record exactly:

| Field | Committed `catalog_results.json` | This rerun |
|---|---|---|
| `total` / `passed` | 36 / 36 | 36 / 36 |
| per-case pass set | all 36 pass | identical |
| `source_hashes` for `main.py`, `rules.json`, `tests/cases.json` | `6518f4ef...`, `401442f7...`, `31ffb204...` | identical |

Identical source hashes mean `main.py`, `rules.json` and `tests/cases.json` have not changed since the recorded catalog run. The 36/36 figure is reproducible on a clean machine, not only on the author's.

## 5. Live-model evidence, re-read rather than re-run

AI mode was not re-executed because the key is deliberately withheld from the repository and was not supplied to this check. The recorded evidence was inspected instead.

`evidence/live_results.json`: 32 planned, 32 completed, 30 passed. Expected statuses 20 classified and 12 refused; 19 and 11 passed.

Both non-passes, L17 and L32, have `status: unavailable` and no parts. `unavailable` is only produced when the upstream call fails or the returned structure fails validation. Neither is a wrong bin assignment, so the honest description of the first run is "30 of 32 produced an expected, verifiable answer; 2 produced no verifiable answer", not "2 wrong answers".

`evidence/live_targeted_rerun.json`: 2 of 2 passed, with a newer `main.py` hash (`6518f4ef...`, the same hash this check verified).

Causation check on the rerun:

- L17 expected R08/R09/R10 and now returns them. The narrow fix (accept `R1`-`R9` only when the canonical `R01`-`R09` rule exists and the bin matches) plausibly explains it: unpadded IDs previously raised `ValueError` and became `unavailable`.
- L32 expected `refused` and now returns `refused`. The refusal path never reads a rule ID, so the ID normalization cannot be the cause. The rerun recorded a different model response. The cause is not isolated and the case should not be cited as fixed by that change.

## 6. Defects found

Severity is about what a marker or TA would hit, not about code quality.

| # | Severity | Defect | Suggested fix |
|---|---|---|---|
| D1 | Medium | Setup and verify commands are PowerShell only. On a stock macOS there is no `python` on `PATH`, so the first documented command fails. `start.ps1` has no POSIX equivalent. | Dual-platform command blocks; name `python3` for macOS. A `start.sh` is optional. |
| D2 | Medium | `requirements-lock.txt` exists but the README never mentions it, so a reader installs unpinned transitive dependencies. | Document `-r requirements-lock.txt` as the exact-reproduction path. |
| D3 | Low | README states Python 3.12 only. 3.13.12 also passes 20/20. | State 3.12 and 3.13 as verified. |
| D4 | High (accuracy) | README and the group summary attribute both live-test failures to the rule-ID fix. The evidence supports that for L17 only; L32 passed on a different model response. Both were `unavailable`, not misclassifications. | Reword to what the evidence shows, and state that the 32-case pass rate after the fix is unmeasured. |
| D5 | Low | README says the live script "stops after two unavailable responses"; the counter resets after each successful call, so it stops after two consecutive ones. | Add "consecutive". |
| D6 | Low | The live-test section says `python evaluate_live.py --run`, but the dependencies live in `.venv`, and the script hardcodes `127.0.0.1:8019` without the README saying the server must listen there. | Use the venv interpreter and state the fixed address. |
| D7 | Low | `evidence/browser_*.png` are JPEG data, not PNG. They open correctly in browsers and viewers, but the extension is wrong. | Rename to `.jpg` or re-encode. Cosmetic only; no functional impact. |
| D8 | Low | `evidence/unit_tests.txt` is the only test log and contains the author's local path `C:\Users\hanli\...`. | Add a macOS log; the path is a minor local-path disclosure. |
| D9 | Low | `httpx` honours `HTTP_PROXY`. On a machine with proxy environment variables set, calls to `127.0.0.1` are proxied and `evaluate_live.py` fails with connection errors. Reproduced here. | Document `NO_PROXY=127.0.0.1`, or pass `trust_env=False` in the client. |
| D10 | Medium (accuracy) | The verify section lists "multipart limits" among the tested behaviours. The API accepts JSON only; `main.py` has no multipart handling and `tests/test_contracts.py` has no multipart case. | Remove the claim, or add a real test. |

D1 to D6 and D10 were corrected in `README.md` in the same commit as this record. D7 to D9 are recorded only.

## 7. What this check does and does not establish

Establishes:

- A clean clone installs and runs on macOS with Python 3.12 and 3.13 using only documented commands.
- The three documented demo queries behave as described, including both refusal cases.
- 20/20 unit tests and 36/36 catalog cases reproduce, with identical source hashes.
- No API key, token or `.env` file exists in the working tree or anywhere in git history.

Does not establish:

- That AI mode works. The key is withheld; the claim rests on the author's recorded run.
- That the rules match current HKU signage. Not checked here.
- That 19/20 and 11/12 measure model accuracy. The suite is AI-authored and small, as the README already says.

## 8. Reproduce this check

```bash
git clone https://github.com/Isaiah-WU/ailt9019-hallsort.git && cd ailt9019-hallsort
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pytest -q            # expect: 20 passed, 1 warning
.venv/bin/python evaluate.py             # expect: Catalog regression: 36/36 passed.
```

`requirements-lock.txt` already includes `pytest`, so no separate dev install is needed.

Before signing the status sheet, rerun these four commands and confirm the two expected lines. Do not record this check as your own contribution unless you have done so.
