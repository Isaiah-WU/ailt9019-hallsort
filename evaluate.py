"""Curated regression checks, NOT a live-LLM accuracy benchmark."""
import hashlib
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from main import app

root=Path(__file__).parent
cases=json.loads((root/'tests'/'cases.json').read_text(encoding='utf-8'))
client=TestClient(app)
rows=[]
for case in cases:
    response=client.post('/api/classify',json={'query':case['query'],'mode':'catalog'})
    actual=response.json()
    bins=[p['bin'] for p in actual.get('parts',[])]
    passed=response.status_code==200 and actual['status']==case['status'] and bins==case['bins']
    rows.append(dict(**case,passed=passed,actual=actual,http_status=response.status_code))
out=root/'evidence';out.mkdir(exist_ok=True)
result=dict(date=datetime.now().astimezone().isoformat(),mode='catalog',live_llm_tested=False,
            description='Curated regression cases with expected results fixed before this run; not independent or representative accuracy.',
            total=len(rows),passed=sum(r['passed'] for r in rows),
            source_hashes={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['main.py','rules.json','tests/cases.json']},cases=rows)
(out/'catalog_results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(f"Catalog regression: {result['passed']}/{result['total']} passed. Live LLM: not tested.")
raise SystemExit(0 if result['passed']==result['total'] else 1)
