import json


async def test_exhibits(jp_fetch):
    response = await jp_fetch("jupyterlab-gallery", "exhibits")
    assert response.code == 200
    payload = json.loads(response.body)
    assert isinstance(payload["exhibits"], list)


async def test_gallery(jp_fetch):
    response = await jp_fetch("jupyterlab-gallery", "gallery")
    assert response.code == 200
    payload = json.loads(response.body)
    assert payload["apiVersion"] == "1.0"
