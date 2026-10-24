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
args=parser.parse_args()
if not args.run:
    parser.error('Live evaluation consumes model quota. Start the server then pass --run.')
root=Path(__file__).parent
cases=json.loads((root/'tests/live_cases.json').read_text())
if args.cases:
    selected=[c for c in cases if c['id'] in args.cases]
    if len(selected)!=len(set(args.cases)):parser.error('Unknown case ID')
    cases=selected
out=root/'evidence'/('live_targeted_rerun.json' if args.cases else 'live_results.json')
rows=[]
with httpx.Client(base_url='http://127.0.0.1:8019',timeout=45) as client:
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
                    source_hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['main.py','rules.json','tests/live_cases.json']},cases=rows)
        out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
        print(f"{case['id']} {'PASS' if passed else 'FAIL'} {actual.get('status')} {ids}",flush=True)
        failures=failures+1 if actual.get('status')=='unavailable' else 0
        if failures>=2: raise SystemExit('Stopped after two unavailable responses; inspect provider setup before retrying.')
        time.sleep(1)
print(f"Live acceptance: {result['passed']}/{result['completed']} passed.")
raise SystemExit(0 if result['passed']==len(cases) else 1)
