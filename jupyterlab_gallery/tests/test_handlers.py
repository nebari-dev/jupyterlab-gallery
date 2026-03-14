import json
from unittest import mock
from pathlib import Path
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
            "isCloned": True
        },
    ],
)
async def test_exhibits_post(jp_fetch, exhibit):
    update = {
        "new_path": "gallery",
        "old_path": "examples"
    }

    def mocked_exists(path_instance):
        if str(path_instance) in ["gallery", "gallery/nebari"]:
            return True
        else:
            return False

    def mocked_get_exhibit_data(_, exhibit):
        output = {
            "homepage": exhibit["homepage"],
            "icon": None,
            "localPath": exhibit["destination"],
            "isCloned": True,
        }
        return output
    with mock.patch.multiple(GalleryManager, 
                        exhibits=[exhibit],
                        destination=Path("example"),
                        get_exhibit_data=mocked_get_exhibit_data):
        with mock.patch.object(Path, "exists", mocked_exists):
            response = await jp_fetch("jupyterlab-gallery", "exhibits", method="POST", body=json.dumps(update))
    assert response.code == 200
    payload = json.loads(response.body)
    assert payload["exhibits"][0]["localPath"] == "gallery"


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
