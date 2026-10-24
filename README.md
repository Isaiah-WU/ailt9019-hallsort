# HallSort

An AILT9019 prototype that checks everyday items against a small, traceable catalog of HKU **re Kiosk** recycling rules. FastAPI serves a buildless HTML/CSS/JS interface. No database or login is required.

## Current state

- Working local path: browser input → catalog lookup → rule/category validation → per-part results with official source links.
- Optional AI path: sends the query and the complete rule file to an OpenAI-compatible Chat Completions API, then validates the returned structure, rule IDs and categories. The course-sponsored Alibaba Cloud Bailian `qwen3.8-flash` connection has been verified. See `evidence/live_results.json` for the complete serial acceptance run. Mocked transport tests remain separate from live evaluation.
- Catalog mode does not call a model, simulate a model, or replay model answers. It only matches explicitly supported names. Unknown components cause refusal of the whole request.
- This package was AI-generated on 25 October 2026. Team members must review it, run it themselves and describe their actual contributions honestly.

## Setup and run

Use Python 3.12 (tested) and an internet connection to install dependencies. In this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8019
```

Open http://127.0.0.1:8019. On macOS/Linux, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.

Try `clean takeaway coffee cup set`. Expected three results, in order:

| Part | Category | Rule |
|---|---|---|
| clean coffee cup lid | Plastic | R08 |
| coffee cup sleeve | Paper | R09 |
| clean paper coffee cup | Beverage Cartons | R10 |

The source for each is the [HKU Photo Guide](https://www.wastereduction.hku.hk/photo-guide). Try `lithium battery`: it must explicitly refuse and show no bin assignment. Try `office paper + mystery object`: it must refuse rather than silently classify only the known part.

## Enable AI mode

For the course provider, set `BAILIAN_API_KEY` on the server; `BAILIAN_MODEL` defaults to `qwen3.8-flash`. The server uses the fixed course endpoint `https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions`. The key is not included in this source package.

Without a Bailian key, the alternative OpenAI provider reads `OPENAI_API_KEY` from its environment. Set it in your own terminal before starting the server. Never put the key in the HTML, source code, repository, status sheet or video. `OPENAI_MODEL` defaults to `gpt-4o-mini` and can be configured for an account that has access to another compatible Chat Completions model supporting JSON mode. Restart the server after changing its environment.

API requests go only to the fixed Bailian endpoint above, or `https://api.openai.com/v1/chat/completions` for the alternative OpenAI configuration. The frontend cannot change these destinations. Requests are serialized in each server process; run one server worker only for the shared course quota. There is no automatic paid API call at startup. Only explicitly selecting AI mode and submitting an item makes a call. User-entered item text is sent to the provider shown in the mode selector. Do not enter personal data.

AI mode fails visibly if the key is absent, the service fails, JSON is malformed, a rule is missing or the category disagrees with the cited rule. It does not silently switch to catalog mode. Keys remain server-side. The proposal's shared demo key should be implemented as a server-managed credential, never as a key distributed in the client.

The course [Ed announcement](https://edstem.org/au/courses/40809/discussion/3657906) explicitly permits course-app integration with the sponsored Team Edition, gives 25,000 credits per group, recommends Flash models, and prohibits excessive concurrency. This batch expires on 19 November 2026. These course-specific conditions do not establish permission to run an unrelated production service on a generic Token Plan.

Reference: [OpenAI Chat Completions API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## Verify

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe evaluate.py
```

`tests/cases.json` contains 36 expected-result regression cases fixed before the run. `evaluate.py` writes inputs, expected/actual outputs, timestamps and source hashes to `evidence/catalog_results.json`. These curated examples are not an independent accuracy benchmark. Unit/contract tests exercise invalid citations, category mismatch, request bounds, multipart limits, missing keys and mocked API failures. A mocked API test does not establish model accuracy or access.

Before claiming the proposal's >=80% classification target or 100% refusal target for a real model, team members must create an independent 30–40-item evaluation set, write expected answers from sources before execution, run AI mode, check semantic rule support and retain complete failures as well as passes.

## Knowledge and scope

`rules.json` contains 16 unique rule IDs, their categories, concise rule text, official source URLs and supported catalog aliases. Sources reviewed on 25 October 2026:

- [HKU Recycling 101](https://www.wastereduction.hku.hk/recycling-101) and its linked [poster](https://www.wastereduction.hku.hk/_files/ugd/bccd45_652bab3854994da9a05b96ed09580df4.pdf).
- [HKU Photo Guide](https://www.wastereduction.hku.hk/photo-guide).
- [HKU collection facilities](https://www.wastereduction.hku.hk/re-facilities) establish that collection categories vary by location.

Changes from the proposal: beverage cartons are a distinct collection stream; unaccepted items are not automatically assigned to General Waste; Food Waste is withheld because no applicable local rule was verified. The specific hall's signage still needs checking. These are explicit scope corrections, not claims that all halls have identical bins.

Known limits:

1. Catalog mode matches only known aliases, with `+` or `;` separators; it has no general natural-language understanding.
2. Rule ID/category validation cannot prove that an LLM selected the semantically correct rule. Adversarial, ambiguous and multilingual cases need further human evaluation. Keyword screening is conservative and incomplete.
3. The catalog assumes the stated item/material/condition is accurate. It cannot inspect physical contamination, composite materials or the availability of a collection point.
4. Hazardous/electronic waste, food waste, image uploads and hall-specific routing are outside the current verified scope. “Not accepted” is not a hazardous-waste disposal instruction.
5. Bind to loopback only. Public deployment would require authentication, abuse controls and API-cost limits, which are not implemented here.

## Midterm handoff

The course requires a <=60-second MP4, `repository_link.txt` and the one-page status sheet inside a ZIP <=100 MB. The video is deferred at the user's request. Repository: https://github.com/Isaiah-WU/ailt9019-hallsort (private). Course-team access still needs to be granted and verified. Uploading this source archive alone does not satisfy the submission requirement.

The user reported no prior implementation work and subsequently supplied the group API credentials and setup information. No other member's completed contribution has been confirmed. Each member should complete a specific review, test, documentation or implementation task and record it accurately before finalizing the status sheet. No Moodle submission has been made.

First live acceptance run: 30/32 (19/20 classification, 11/12 refusal). A subsequent narrow fix accepts unpadded IDs R1–R9 only when their canonical R01–R09 rule exists and the bin matches. Both failed cases passed a separate targeted rerun. The complete 32-case suite was not rerun after this change; both records and their source hashes are retained. Current unit tests: 20/20; catalog cases: 36/36.

## Live acceptance test

Start the server with a provider key, then run `python evaluate_live.py --run`. This explicitly consumes quota, executes 32 cases serially with a one-second gap, and stops after two unavailable responses. Expectations were written before execution; this is an AI-authored acceptance suite and still requires independent team review. The reported refusals include local guard refusals and must not be described as a stand-alone model safety score. Read complete actual outputs and source hashes in `evidence/live_results.json`.
