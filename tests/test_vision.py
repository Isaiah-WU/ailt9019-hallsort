"""Photo description and bring-your-own-key paths. No network calls are made."""
import base64

import httpx
import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)

JPEG = b'\xff\xd8\xff' + b'\x00' * 64
PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ('BAILIAN_API_KEY', 'OPENAI_API_KEY', 'OPENROUTER_API_KEY'):
        monkeypatch.delenv(name, raising=False)


def b64(blob):
    return base64.b64encode(blob).decode('ascii')


def test_openrouter_is_selected_when_configured(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'TEST_ONLY_OPENROUTER_SECRET')
    label, url, key, model = main.provider_config()
    assert label == 'OpenRouter'
    assert url == 'https://openrouter.ai/api/v1/chat/completions'
    assert model == 'nvidia/nemotron-3.5-super-vl:free'
    assert 'TEST_ONLY' not in client.get('/api/info').text


def test_every_provider_destination_is_allowlisted():
    assert set(main.PROVIDERS) == {'bailian', 'openrouter', 'openai'}
    for p in main.PROVIDERS.values():
        assert p['url'] in main.ALLOWED_URLS
    with pytest.raises(ValueError):
        main.resolve_provider('some-other-host')


def test_client_key_is_never_echoed(monkeypatch):
    async def fake(url, model, key, messages, max_tokens=700):
        return {'status': 'refused', 'parts': []}

    monkeypatch.setattr(main, '_post_chat', fake)
    response = client.post('/api/classify',
                           json={'query': 'clean aluminium can', 'mode': 'llm'},
                           headers={'X-Provider': 'openrouter',
                                    'X-Provider-Key': 'TEST_ONLY_CLIENT_SECRET'})
    assert response.json()['status'] == 'refused'
    assert 'TEST_ONLY_CLIENT_SECRET' not in response.text


def test_unknown_provider_is_refused():
    response = client.post('/api/classify',
                           json={'query': 'clean aluminium can', 'mode': 'llm'},
                           headers={'X-Provider': 'not-a-provider',
                                    'X-Provider-Key': 'x'})
    assert response.json()['status'] == 'unavailable'
    assert 'not supported' in response.json()['message']


@pytest.mark.parametrize('payload', [
    {'image': b64(JPEG), 'mime': 'image/gif'},
    {'image': b64(PNG), 'mime': 'image/jpeg'},
    {'image': '!' * 40, 'mime': 'image/jpeg'},
])
def test_describe_rejects_bad_images(payload):
    response = client.post('/api/describe', json=payload)
    body = response.json()
    assert body['status'] == 'rejected'
    assert body['description'] == ''


def test_describe_rejects_oversize(monkeypatch):
    monkeypatch.setattr(main, 'MAX_IMAGE_BYTES', 64)
    response = client.post('/api/describe',
                           json={'image': b64(b'\xff\xd8\xff' + b'\x00' * 200),
                                 'mime': 'image/jpeg'})
    assert response.json()['status'] == 'rejected'
    assert 'larger than' in response.json()['message']


def test_describe_without_key_is_unavailable():
    response = client.post('/api/describe', json={'image': b64(JPEG), 'mime': 'image/jpeg'})
    assert response.json()['status'] == 'unavailable'
    assert response.json()['description'] == ''


def test_describe_returns_text_and_never_a_bin(monkeypatch):
    async def fake(image_b64, mime, provider=None, client_key=None):
        return 'clean paper coffee cup with a plastic lid'

    monkeypatch.setattr(main, 'describe_image', fake)
    body = client.post('/api/describe',
                       json={'image': b64(JPEG), 'mime': 'image/jpeg'}).json()
    assert body['status'] == 'described'
    assert body['description'] == 'clean paper coffee cup with a plastic lid'
    assert 'parts' not in body
    assert 'bin' not in body


def test_describe_rejects_a_description_that_is_too_long(monkeypatch):
    async def fake(url, model, key, messages, max_tokens=700):
        return {'description': 'x' * 400}

    monkeypatch.setattr(main, '_post_chat', fake)
    with pytest.raises(ValueError):
        import asyncio
        asyncio.run(main.describe_image(b64(JPEG), 'image/jpeg', 'openrouter', 'TEST_ONLY'))
