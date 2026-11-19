import json
import httpx
import pytest
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

@pytest.fixture(autouse=True)
def isolated_keys(monkeypatch):
    monkeypatch.delenv('BAILIAN_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)


def test_bailian_configuration_does_not_expose_key(monkeypatch):
    monkeypatch.setenv('BAILIAN_API_KEY','TEST_ONLY_BAILIAN_SECRET')
    provider,url,key,model=main.provider_config()
    assert url=='https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions'
    assert model=='qwen3.8-flash'
    response=client.get('/api/info')
    assert response.json()['provider']=='Alibaba Cloud Bailian'
    assert 'TEST_ONLY' not in response.text


def test_model_requests_are_serial(monkeypatch):
    import asyncio
    monkeypatch.setenv('BAILIAN_API_KEY','TEST_ONLY_BAILIAN_SECRET')
    counters={'active':0,'peak':0}
    async def fake(q,k):
        counters['active']+=1
        counters['peak']=max(counters['peak'],counters['active'])
        await asyncio.sleep(.01)
        counters['active']-=1
        return {'status':'refused','parts':[]}
    monkeypatch.setattr(main,'call_model',fake)
    monkeypatch.setattr(main,'MODEL_LOCK',asyncio.Semaphore(1))
    async def run():
        await asyncio.gather(*(main.classify(main.Query(query='unknown item',mode='llm')) for _ in range(3)))
    asyncio.run(run())
    assert counters['peak']==1


@pytest.mark.parametrize('payload', [
    {'status':'classified','parts':[{'part':'can','bin':'Metal','rule_id':'R999'}]},
    {'status':'classified','parts':[{'part':'can','bin':'Paper','rule_id':'R03'}]},
    {'status':'classified','parts':[]},
    {'status':'refused','parts':[{'part':'can','bin':'Metal','rule_id':'R03'}]},
    {'status':'classified','parts':[{'part':'can','bin':'Metal','rule_id':'R03','source':'https://bad.example'}]},
])
def test_reject_invalid_model_outputs(payload):
    with pytest.raises(ValueError): main.validate_answer(payload, 'llm')


def test_source_is_server_owned():
    result=main.validate_answer({'status':'classified','parts':[{'part':'can','bin':'Metal','rule_id':'R03'}]},'llm')
    assert result['parts'][0]['source']==main.RULES['R03']['source']


def test_only_known_short_ids_are_normalized():
    result=main.validate_answer({'status':'classified','parts':[{'part':'lid','bin':'Plastic','rule_id':'R8'}]},'llm')
    assert result['parts'][0]['rule_id']=='R08'
    assert result['parts'][0]['returned_rule_id']=='R8'
    for bad_id in ['R0','R0008','r8','R99']:
        with pytest.raises(ValueError):
            main.validate_answer({'status':'classified','parts':[{'part':'lid','bin':'Plastic','rule_id':bad_id}]},'llm')


def test_missing_key_is_explicit(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    data = client.post('/api/classify',json={'query':'clean aluminium can','mode':'llm'}).json()
    assert data['status'] == 'unavailable' and not data['model_attempted']


@pytest.mark.parametrize('bad', [ValueError('bad json'), httpx.ReadTimeout('timeout'),KeyError('choices')])
def test_upstream_failures_do_not_leak(monkeypatch,bad):
    monkeypatch.setenv('OPENAI_API_KEY','TEST_ONLY_NOT_A_KEY')
    async def fake(q,k): raise bad
    monkeypatch.setattr(main,'call_model',fake)
    result=client.post('/api/classify',json={'query':'clean aluminium can','mode':'llm'})
    assert result.status_code==200 and result.json()['status']=='unavailable'
    assert result.json()['model_attempted']
    if isinstance(bad, httpx.ReadTimeout):
        assert 'in time' in result.json()['message']
    assert 'TEST_ONLY' not in result.text


def test_mocked_model_path(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','TEST_ONLY_NOT_A_KEY')
    async def fake(q,k):
        return {'status':'classified','parts':[{'part':'can','bin':'Metal','rule_id':'R03'}]}
    monkeypatch.setattr(main,'call_model',fake)
    data = client.post('/api/classify',json={'query':'a clean soda can','mode':'llm'}).json()
    assert data['parts'][0]['bin'] == 'Metal' and data['model_attempted']


def test_guard_prevents_model_call(monkeypatch):
    async def fake(q,k): raise AssertionError('Must not call model')
    monkeypatch.setattr(main,'call_model',fake)
    data = client.post('/api/classify',json={'query':'lithium battery','mode':'llm'}).json()
    assert data['status'] == 'refused' and not data['model_attempted']


@pytest.mark.parametrize('body', [{'query':''},{'query':'x'*401},{'query':'can','mode':'unknown'}])
def test_request_bounds(body):
    assert client.post('/api/classify',json=body).status_code==422


def test_expanded_part_limit():
    assert client.post('/api/classify',json={'query':'clean takeaway coffee cup set + clean takeaway coffee cup set + clean takeaway coffee cup set'}).json()['status']=='refused'


def test_model_transport(monkeypatch):
    seen=[]
    async def handler(request):
        data=json.loads(request.content);seen.append(data)
        assert request.url==httpx.URL('https://api.openai.com/v1/chat/completions')
        assert data['response_format']['type']=='json_object'
        assert 'R16' in data['messages'][0]['content']
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{"status":"refused","parts":[]}'}}]})
    original=httpx.AsyncClient
    monkeypatch.setattr(main.httpx,'AsyncClient',lambda **kwargs: original(transport=httpx.MockTransport(handler),**kwargs))
    monkeypatch.setenv('OPENAI_API_KEY','TEST_ONLY_NOT_A_KEY')
    data = client.post('/api/classify',json={'query':'unknown material','mode':'llm'}).json()
    assert data['status'] == 'refused' and data['model_attempted']
    assert len(seen)==1


def test_busy_queue_never_contacts_provider(monkeypatch):
    import asyncio

    monkeypatch.setenv('BAILIAN_API_KEY', 'test-only')
    monkeypatch.setattr(main, 'MODEL_LOCK', asyncio.Semaphore(0))
    monkeypatch.setattr(main, 'QUEUE_TIMEOUT_SECONDS', 0.01)
    async def unexpected_call(*args):
        pytest.fail('Queue timeout must precede provider access')
    monkeypatch.setattr(main, 'call_model', unexpected_call)
    result = client.post('/api/classify', json={'query': 'item', 'mode': 'llm'}).json()
    assert result['status'] == 'unavailable' and not result['model_attempted']
    assert result['parts'] == [] and 'still running' in result['message']


def test_deadline_releases_slot_without_retry(monkeypatch):
    import asyncio

    monkeypatch.setenv('BAILIAN_API_KEY', 'test-only')
    monkeypatch.setattr(main, 'MODEL_LOCK', asyncio.Semaphore(1))
    monkeypatch.setattr(main, 'MODEL_DEADLINE_SECONDS', 0.01)
    attempts = 0
    async def delayed_then_ready(*args):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            await asyncio.sleep(3)
        return {'status': 'refused', 'parts': []}
    monkeypatch.setattr(main, 'call_model', delayed_then_ready)
    query = {'query': 'item', 'mode': 'llm'}
    first = client.post('/api/classify', json=query).json()
    assert attempts == 1 and first['status'] == 'unavailable' and first['model_attempted']
    assert 'in time' in first['message'] and first['parts'] == []
    second = client.post('/api/classify', json=query).json()
    assert attempts == 2 and second['status'] == 'refused' and second['model_attempted']


@pytest.mark.parametrize(('status', 'expected'), [
    (401, 'authenticate'),
    (403, 'denied access'),
    (429, 'rate or quota limit'),
    (503, 'provider returned an error'),
])
def test_provider_http_error_messages(monkeypatch, status, expected):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(status, json={'error': 'PRIVATE_PROVIDER_DETAIL'})
    original = httpx.AsyncClient
    monkeypatch.setattr(main.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setenv('BAILIAN_API_KEY', 'TEST_PRIVATE_CREDENTIAL')
    response = client.post('/api/classify', json={'query': 'clean can', 'mode': 'llm'})
    result = response.json()
    assert response.status_code == 200 and result['status'] == 'unavailable'
    assert result['model_attempted'] and len(requests) == 1 and not result['parts']
    assert expected in result['message']
    assert 'PRIVATE' not in response.text
