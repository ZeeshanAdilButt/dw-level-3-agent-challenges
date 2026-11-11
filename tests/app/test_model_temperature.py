"""A hosted model that refuses `temperature` is asked again without it, and the refusal is remembered."""
import io
import json
import urllib.error

from app import model as M
from app.settings import validate


def test_a_model_that_refuses_temperature_is_asked_again_without_it(monkeypatch):
    monkeypatch.setenv("DW_HOSTED_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("DW_HOSTED_API_KEY", "test-key")
    M._NO_TEMPERATURE.clear()
    bodies = []

    def fake_urlopen(req, timeout=0):
        body = json.loads(req.data)
        bodies.append(body)
        if "temperature" in body:
            raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {},
                                         io.BytesIO(b'{"error":{"message":"`temperature` is deprecated for this model."}}'))
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": "ok"}}], "usage": {}}).encode())

    monkeypatch.setattr(M.urllib.request, "urlopen", fake_urlopen)
    client = M.ModelClient(validate({"pack": "quillon", "model_path": "hosted", "hosted_model": "some-model"}))
    assert client._http([{"role": "user", "content": "hi"}], None, 1).text == "ok"
    assert "temperature" in bodies[0] and "temperature" not in bodies[1]
    client._http([{"role": "user", "content": "hi"}], None, 2)
    assert "temperature" not in bodies[2]                     # remembered: no failed call the second time
