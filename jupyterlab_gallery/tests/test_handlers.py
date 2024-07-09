import json
from unittest import mock
import pytest

from jupyter_server.utils import url_path_join

from jupyterlab_gallery.manager import GalleryManager


async def test_exhibits(jp_fetch):
    response = await jp_fetch("jupyterlab-gallery", "exhibits")
    assert response.code == 200
    payload = json.loads(response.body)
    assert isinstance(payload["exhibits"], list)


@pytest.mark.parametrize(
    "exhibit",
    [
        {
            "git": "https://github.com/nebari-dev/nebari.git",
            "homepage": "https://github.com/nebari-dev/nebari",
        },
        {
            "git": "https://github.com/nebari-dev/nebari.git",
            "homepage": "https://github.com/nebari-dev/nebari",
            "icon": None,
        },
    ],
)
async def test_exhibit_generate_github_icon(jp_serverapp, jp_fetch, exhibit):
    with mock.patch.object(GalleryManager, "exhibits", [exhibit]):
        response = await jp_fetch("jupyterlab-gallery", "exhibits")
    assert response.code == 200
    payload = json.loads(response.body)
    assert len(payload["exhibits"]) == 1
    assert (
        payload["exhibits"][0]["icon"]
        == "https://opengraph.githubassets.com/1/nebari-dev/nebari"
    )


async def test_gallery(jp_fetch):
    response = await jp_fetch("jupyterlab-gallery", "gallery")
    assert response.code == 200
    payload = json.loads(response.body)
    assert payload["apiVersion"] == "1.0"


async def test_pull_token_can_be_used_instead_of_xsrf(
    jp_serverapp, jp_base_url, http_server_client
):
    token = jp_serverapp.identity_provider.token
    response = await http_server_client.fetch(
        url_path_join(jp_base_url, "jupyterlab-gallery", "pull"),
        body=b'{"exhibit_id": 100}',
        method="POST",
        headers={"Authorization": f"token {token}", "Cookie": ""},
        raise_error=False,
    )
    assert response.code == 406
    payload = json.loads(response.body)
    assert payload["message"] == "exhibit_id 100 not found"
