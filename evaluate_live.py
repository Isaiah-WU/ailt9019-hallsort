"""Opt-in serial live test. Uses the running local server; consumes course quota."""
import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--run',action='store_true',help='Explicitly enable the live calls')
parser.add_argument('--cases',nargs='+',help='Optional case IDs for a separately saved targeted rerun')
parser.add_argument('--suite', choices=('october', 'november'), default='october')
parser.add_argument('--server-port', type=int, default=8019)
args=parser.parse_args()
if not args.run:
    parser.error('Live evaluation consumes model quota. Start the server then pass --run.')
root=Path(__file__).parent
case_file = 'tests/november_cases.json' if args.suite == 'november' else 'tests/live_cases.json'
cases=json.loads((root/case_file).read_text(encoding='utf-8'))
if args.cases:
    selected=[c for c in cases if c['id'] in args.cases]
    if len(selected)!=len(set(args.cases)):parser.error('Unknown case ID')
    cases=selected
label = 'live_targeted' if args.cases else 'live_results'
out = root/'evidence'/f"{label}_{args.suite}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
print(f"Saving this run to {out.name}", flush=True)
rows=[]
with httpx.Client(base_url=f'http://127.0.0.1:{args.server_port}', timeout=65, trust_env=False) as client:
    info=client.get('/api/info').json()
    if not info['llm_available']: raise SystemExit('No model configured; no calls made.')
    failures=0
    for case in cases:
        started=time.perf_counter()
        response=client.post('/api/classify',json={'query':case['query'],'mode':'llm'})
        actual=response.json()
        ids=sorted(p['rule_id'] for p in actual.get('parts',[]))
        passed=response.status_code==200 and actual.get('status')==case['status'] and ids==sorted(case['rule_ids'])
        rows.append(dict(**case,passed=passed,seconds=round(time.perf_counter()-started,2),actual=actual))
        result=dict(date=datetime.now().astimezone().isoformat(),provider=info['provider'],model=info['model'],
                    planned=len(cases),completed=len(rows),passed=sum(r['passed'] for r in rows),
                    note='AI-authored small acceptance suite, expected results fixed before running. Not independent team validation or broad accuracy.',
                    source_hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['main.py','rules.json',case_file]},cases=rows)
        out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
        print(f"{case['id']} {'PASS' if passed else 'FAIL'} {actual.get('status')} {ids}",flush=True)
        failures=failures+1 if actual.get('status')=='unavailable' else 0
        if failures>=2: raise SystemExit('Stopped after two unavailable responses; inspect provider setup before retrying.')
        time.sleep(1)
print(f"Live acceptance: {result['passed']}/{result['completed']} passed.")
raise SystemExit(0 if result['passed']==len(cases) else 1)
