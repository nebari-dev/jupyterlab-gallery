import json


async def test_exhibits(jp_fetch):
    response = await jp_fetch("jupyterlab-gallery", "exhibits")
    assert response.code == 200
    payload = json.loads(response.body)
    assert payload["exhibits"]
    assert payload["apiVersion"] == "1.0"
