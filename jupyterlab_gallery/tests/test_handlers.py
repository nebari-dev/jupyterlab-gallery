import json
from unittest import mock
import pytest
import tornado
import json

from jupyter_server.utils import url_path_join

from jupyterlab_gallery.manager import GalleryManager


@pytest.fixture
def exhibits_server(jp_asyncio_loop):
    async def run_server():
        content = {"exhibits": [
            {
                "git": "https://github.com/nebari-dev/jupyterlab-gallery.git",
                "homepage": "https://github.com/nebari-dev/nebari",
                "title": "jupyterlab-gallery"
            }
        ]}

        class ExhibitsJsonHandler(tornado.web.RequestHandler):
            def get(self):
                self.write(content)

        app = tornado.web.Application([(r"/exhibits.json", ExhibitsJsonHandler)])

        server = app.listen(8030)
        return server
        
    server = jp_asyncio_loop.run_until_complete(run_server())
    yield "http://127.0.0.1:8030"
    server.stop()


async def test_exhibits(jp_fetch):
    response = await jp_fetch("jupyterlab-gallery", "exhibits")
    assert response.code == 200
    payload = json.loads(response.body)
    assert isinstance(payload["exhibits"], list)

async def test_exhibits_with_exhibits_url(jp_fetch, exhibits_server):
    url = exhibits_server
    with mock.patch.object(GalleryManager, "exhibits_url", url + "/exhibits.json"):
        response = await jp_fetch("jupyterlab-gallery", "exhibits")
    assert response.code == 200
    payload = json.loads(response.body)
    assert len(payload["exhibits"]) == 1
    assert payload["exhibits"][0]["title"] == "jupyterlab-gallery"


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
