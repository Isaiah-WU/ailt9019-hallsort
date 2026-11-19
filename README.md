# HallSort

HallSort helps an HKU student decide how to separate an item at the **re Kiosk**. A clean takeaway coffee set, for example, yields a plastic lid (R08), paper sleeve (R09) and paper cup for the beverage-carton stream (R10). Each part links to the campus guidance used for that decision.

**[Project page](https://isaiah-wu.github.io/ailt9019-hallsort/) · [Final demo with English narration and captions](submission/hallsort-final-demo.mp4) · [Source rules](rules.json) · [Final Windows verification](evidence/final_offline.md)**

## Run HallSort

Use Python 3.12 or 3.13. On Windows, run the following from PowerShell in the repository:

```powershell
.\start.ps1
```

The launcher creates the virtual environment if needed and installs the runtime requirements on each launch, including after an interrupted install. For an installation with the exact versions used in verification, or if the launcher is unavailable:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8019
```

On macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8019
```

Open [HallSort locally](http://127.0.0.1:8019). Use **Catalog** and try `clean takeaway coffee cup set`. Then try `office paper + mystery object`. An unknown part makes the whole request decline classification. Catalog runs without an API key. The [public project page](https://isaiah-wu.github.io/ailt9019-hallsort/) includes a recorded demonstration.

## How it works

- **Catalog** matches known names and aliases in 17 entries against 16 source-linked rules. Enter up to 400 characters and separate items with `+` or `;`. A query can return up to eight parts.
- **AI interpretation** sends eligible item descriptions and the rule set to the configured provider. FastAPI validates the JSON structure, part count, rule IDs and matching categories. Reasons and links come from the server's rule file. The model can still choose a valid rule for the wrong item.
- **Photo to draft** sends a downscaled JPEG to `/api/describe`. The provider returns one sentence naming the item and its parts; that sentence is placed in the input box for the user to check and edit. Classification then runs on the confirmed text, so a photo never produces a bin on its own.
- **Your own key** lets a visitor use their own provider key for one session instead of the server's. The destination stays on the server's allowlist.
- **Result labels** show when a local check decided the result, when the app attempted a provider call and when classification was unavailable. Hazardous items, some contaminated items and instructions to override signs can be refused locally. Provider errors return an empty result with guidance.

### Optional AI configuration

Three providers are supported, in this order of precedence: `BAILIAN_API_KEY` (Alibaba Cloud Bailian, `qwen3.8-flash`), `OPENROUTER_API_KEY` (OpenRouter, default `nvidia/nemotron-3.5-super-vl:free`), then `OPENAI_API_KEY` (`gpt-4o-mini`). Set one of them in the server environment and restart. The selector names whichever provider and model answered.

**Your own key.** A visitor can paste a key into "Use your own key" instead. It is held in that browser tab's `sessionStorage`, sent as `X-Provider-Key` with each AI request, used for that request only and never written to disk, logs or the response. The provider is chosen from a fixed list and the destination URL is always taken from the server's allowlist, so a supplied key cannot redirect the server anywhere.

**Photo input.** "Add a photo" sends a downscaled JPEG to `/api/describe`, which returns a one-sentence description of the item and its parts. The description is placed in the input box for the user to check and edit, and classification then runs on that confirmed text. No bin, category or rule is ever assigned from a photo, which keeps every answer traceable to a rule matched against a description the user approved. Requires a vision-capable provider: OpenRouter and OpenAI qualify, Bailian in this project does not.

Do not commit a key. `.env` is ignored, and the repository, the recordings and the report contain no credential.

On **19 November 2026**, the sponsored endpoint returned HTTP 403 (`AccessDenied.Unpurchased`). Catalog mode remains usable. A successful live run requires an account with active model access. Run one worker for the shared quota. The app serializes calls, waits up to 5 seconds for a slot, and limits a model attempt to 50 seconds with an 8-second connection timeout and 45-second read timeout. It does not automatically retry a paid request.

## Reproduce the checks

After installing `requirements-lock.txt`, run the commands below in the repository. On Windows, use `.\.venv\Scripts\python.exe` in place of `.venv/bin/python`.

```sh
.venv/bin/python -m pytest -q
.venv/bin/python evaluate.py
```

| Date and scope | Observed result | Evidence |
| --- | --- | --- |
| 19 Nov · Windows 11, Python 3.13.5 | 26/26 contract tests. 36/36 catalog cases. Launcher recovered after a missing dependency. | [Verification](evidence/final_offline.md) · [catalog outputs](evidence/catalog_results_20261119_195009_668292.json) |
| 19 Nov · macOS, Python 3.12 | 37/37 tests, including the photo and own-key paths. 36/36 catalog cases. | Run `pytest -q` |
| 25 Oct · original live suite | 30/32. Two requests returned unavailable. | [First run](evidence/live_results.json) |
| 25 Oct · targeted and full live reruns | 2/2 targeted, then 32/32 on the original suite. | [Targeted](evidence/live_targeted_rerun.json) · [full rerun](evidence/live_results_full_rerun.json) |
| 19 Nov · new English and Chinese suite | 32 planned. The first two requests returned unavailable. The runner stopped and the other 30 were unexecuted. | [Fixed cases](tests/november_cases.json) · [partial run](evidence/live_results_november_20261119_194843_641633.json) · [access check](evidence/final_scope.md) |

The October failures were L17 (unpadded rule ID) and L32 (cause unresolved, later model output differed). The suite checks the status and rule IDs for prewritten cases. An AI assistant drafted both live suites. Refusal counts include local checks. The experiments do not establish performance on an independent human sample.

With authorized provider access and the server running on port 8019, explicitly opt in to the paid serial tests:

```sh
.venv/bin/python evaluate_live.py --run --suite november
```

Use `--suite october` to reproduce the earlier set or `--cases N01` with the November set to select one case. The evaluator bypasses environment proxies for loopback requests, saves a timestamped result after each response, and stops after two consecutive unavailable responses. See the [October clean macOS installation record](evidence/install_reproduction_yang.md) for the earlier revision.

## Rule sources and scope

The [HKU Photo Guide](https://www.wastereduction.hku.hk/photo-guide), [Recycling 101](https://www.wastereduction.hku.hk/recycling-101) and [facility directory](https://www.wastereduction.hku.hk/re-facilities) document the kiosk and its collection streams. The rule file links individual decisions to the corresponding guide or poster. The [November source review](evidence/final_scope.md) records the distinction between a kiosk and a specific hall's facilities.

HallSort accepts a text description, or a photo that it turns into a description for the user to confirm. It cannot inspect an item's cleanliness or a collection point's current signage, and it never assigns a category from an image. Food waste, hazardous disposal instructions and hall-specific routing are outside the verified scope. Follow posted instructions at the collection point. Run the application on loopback. The public site hosts project information and a video.

## Project credits

AILT9019 Group 12 developed HallSort with AI assistance for implementation, evaluation cases, documentation and final verification. The repository retains observed outcomes and the scope of each run. The October [walkthrough](submission/hallsort-demo.mp4) shows the original interface and a real provider response from that date.
