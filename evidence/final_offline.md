# Final Windows verification

On 19 November 2026, the following automated checks ran on Windows 11 build 26200 with Python 3.13.5. The checkout started at PR #2 head `00eba9d` and included the final application fixes. These checks cover the local app and simulated provider failures.

| Check | Observed result |
| --- | --- |
| Fresh virtual environment | `python -m venv .venv` and `.venv\Scripts\python -m pip install -r requirements-lock.txt` succeeded. |
| API and contract tests | `.venv\Scripts\python -m pytest -q` passed all 26 tests in 0.56 s. One Starlette TestClient deprecation warning appeared. |
| Catalog regression | `.venv\Scripts\python evaluate.py` passed all 36 fixed cases after the provider-error message changes. [Expected and actual outputs, run timestamp and source hashes](catalog_results_20261119_195009_668292.json). |
| Windows launcher recovery | Uninstalled Uvicorn from the installed virtual environment, then ran `powershell -NoProfile -ExecutionPolicy Bypass -File start.ps1`. The launcher restored the package and served the app on 127.0.0.1:8019. |
| Broken proxy with local evaluation | With HTTP_PROXY and HTTPS_PROXY pointing at an unused loopback port and NO_PROXY empty, the live evaluator reached the local server, detected that the server had no provider key, and exited before a paid request. |
| Chrome input and result display | The counter showed 0 on load, 5 after typing “hello”, 29 for the coffee cup set example, and 0 after Clear. The coffee set returned three cards. In AI mode, a battery refusal displayed “LOCAL CHECK · NO MODEL CALL”. A regular AI query without a configured key displayed the same provenance with an explicit configuration message. |
| Default mode with a credential configured | With a mocked configured-provider response from `/api/info` and the real local catalog endpoint, Chrome kept catalog selected on first load and displayed three cards for the coffee cup set. On a new load with delayed configuration, manually selecting AI mode and checking a battery produced a local refusal. The later configuration response preserved both the selection and the result. |
| Simulated slow or busy provider | Tests covered an occupied queue slot, an HTTP read timeout and a total-call timeout. The app returned an unavailable status with no classification. A queue timeout made no model attempt. A total deadline made one attempt, released the slot and allowed the next request. |
| Simulated provider access errors | HTTP 401, 403, 429 and 503 each produced one outbound request and a fixed user-facing message. Tests checked authentication, permissions, rate/quota and service errors respectively. No private response detail or credential appeared in the user response. |

The source hashes below use UTF-8 file bytes with CRLF normalized to LF for consistent comparison across Windows and Unix checkouts.

| File | SHA-256 |
| --- | --- |
| main.py | `69fd306f216e8f934f785447297028408cdd5168a732c0a0f57e0b042263d9eb` |
| static/app.js | `85bbb24980e8b43e870d76f1d1e647f0123e390fbbe734e866996332774982c3` |
| start.ps1 | `92511bb48baee41fa830a149d07b2788faa390f7af327f5e92c0236a2222fd6f` |
| tests/test_contracts.py | `1a869f2720820377c380bb8bb309fae28da6a04b5f7ba0ee7fa3dd2e528f30db` |

The timeout checks used simulated delays. Current upstream latency and service availability require separate live measurements.
