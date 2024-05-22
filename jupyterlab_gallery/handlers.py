import json
from pathlib import Path

from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join
from .gitpuller import SyncHandlerBase
import tornado


exhibits = [
    {
        # repository URL can include branch, PAT, basically anything that git will digest
        # TODO: if we embed PAT in repository URL we need another repository URL that is
        "git": "git@github.com:nebari-dev/nebari.git",
        "repository": "https://github.com/nebari-dev/nebari/",
        # "documentation": "https://github.com/nebari-dev/nebari/",
        "title": "Nebari",
        "description": "🪴 Nebari - your open source data science platform",
        # we may want to pin the repository to specific revision?
        # "revision": "2a2f2ee779ac21b70339da6551c2f6b0b00f6efe",
        # icon should be optional to allow for fast prototyping; we may want to allow allow relative paths and then host the assets from `/static`
        #"icon": "test.svg",
        # we may want to allow checking in a single directory from a repo
        # "path_in_repository": ""
        # ""
    },
  {
        "git": "git@github.com:nebari-dev/nebari-docker-images.git",
        "repository": "https://github.com/nebari-dev/nebari-docker-images/",
        "title": "Nebari docker images",
        "description": "Nebari Docker images",
    }
]

# We do not want to expose `git_url` as it may contain PAT;
# we want an allow-list over block-list to avoid exposing PAT in case
# if the author of the config makes a typo like `giit` instead of `git`.
EXPOSED_EXHIBIT_KEYS = ["repository", "title", "description", "icon"]


def extract_repository_owner(git_url: str) -> str:
    fragments = git_url.strip("/").split("/")
    return fragments[-2] if len(fragments) >= 2 else ''


def extract_repository_name(git_url: str) -> str:
    fragment = git_url.split("/")[-1]
    if fragment.endswith(".git"):
        return fragment[:-4]
    return fragment


def prepare_exhibit(exhibit_config, exhibit_id: int) -> dict:
    exposed_config = {
        k: v for k, v in exhibit_config.items() if k in EXPOSED_EXHIBIT_KEYS
    }
    clone_destination = Path("examples")
    repository_name = extract_repository_name(exhibit_config["git"])
    repository_owner = extract_repository_owner(exhibit_config["repository"])
    local_path = clone_destination / repository_name

    if "icon" not in exposed_config:
        if exposed_config["repository"].startswith('https://github.com/'):
            exposed_config["icon"] = f"https://opengraph.githubassets.com/1/{repository_owner}/{repository_name}"

    # we probably want a tratilet to configure path into which the exhibits should be cloned
    # path/relative/to/root/if/cloned
    exposed_config["localPath"] = str(local_path)  # e.g. "examples/nebari"
    exposed_config["revision"] = "2a2f2ee779ac21b70339da6551c2f6b0b00f6efe"
    # timestamp from .git/FETCH_HEAD of the cloned repo
    exposed_config["lastUpdated"] = "2024-05-01"
    exposed_config["currentTag"] = "v3.2.4"
    # the UI can show that there are X updates available; it could also show
    # a summary of the commits available, or tags available; possibly the name
    # of the most recent tag and would be sufficient over sending the list of commits,
    # which can be long and delay the initialization.
    exposed_config["updatesAvailable"] = False
    exposed_config["isCloned"] = local_path.exists()
    exposed_config["newestTag"] = "v3.2.5"
    exposed_config["updates"] = [
        {
            "revision": "02f04c339f880540064d2223176830afdd02f5fa",
            "title": "commit description",
            "description": "long commit description",
            "date": "date in format returned by git",
        }
    ]
    exposed_config["id"] = exhibit_id

    return exposed_config


class ExhibitsHandler(APIHandler):
    # The following decorator should be present on all verb methods (head, get, post,
    # patch, put, delete, options) to ensure only authorized user can request the
    # Jupyter server
    @tornado.web.authenticated
    def get(self):
        # TODO:
        # - move it to a configurable app?
        # - decide if we want to read the config from a file (json/yaml) or just use traitlets (so we could read in from the same json/py as used to configure jupyter-server)
        # - populate PATs in he repository url field by using env variables
        # - implement validation on file reading (either with traitlets or schema)
        self.finish(
            json.dumps(
                {
                    "exhibits": [
                        prepare_exhibit(exhibit_config, exhibit_id=i)
                        for i, exhibit_config in enumerate(exhibits)
                    ],
                    "api_version": "1.0",
                }
            )
        )


class PullHandler(SyncHandlerBase):
    @tornado.web.authenticated
    async def post(self):
        data = self.get_json_body()
        exhibit_id = data['exhibit_id']
        raw_exhibit = exhibits[exhibit_id]
        exhibit = prepare_exhibit(raw_exhibit, exhibit_id=exhibit_id)
        return await super()._pull(
            repo=raw_exhibit["git"],
            exhibit_id=exhibit_id,
            # branch
            # depth
            targetpath=exhibit["localPath"]
        )

    @tornado.web.authenticated
    async def get(self):
        return await super()._stream()


def setup_handlers(web_app, server_app):
    host_pattern = ".*$"

    base_url = web_app.settings["base_url"]
    exhibits_pattern = url_path_join(base_url, "jupyterlab-gallery", "exhibits")
    download_pattern = url_path_join(base_url, "jupyterlab-gallery", "pull")
    handlers = [
        (exhibits_pattern, ExhibitsHandler),
        (download_pattern, PullHandler)
    ]
    web_app.settings['nbapp'] = server_app
    web_app.add_handlers(host_pattern, handlers)
