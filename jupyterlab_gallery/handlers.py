import json
from pathlib import Path

from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join
import tornado


exhibits = [
    {
        # repository URL can include branch, PAT, basically anything that git will digest
        # TODO: if we embed PAT in repository URL we need another repository URL that is
        "git": "git@github.com:nebari-dev/nebari.git",
        "repository": "https://github.com/nebari-dev/nebari/",
        # "documentation": "https://github.com/nebari-dev/nebari/",
        "title": "My test repository",
        "description": "Test repository",
        # we may want to pin the repository to specific revision?
        # "revision": "2a2f2ee779ac21b70339da6551c2f6b0b00f6efe",
        # icon should be optional to allow for fast prototyping; we may want to allow allow relative paths and then host the assets from `/static`
        "icon": "test.svg",
        # we may want to allow checking in a single directory from a repo
        # "path_in_repository": ""
        # ""
    }
]

# We do not want to expose `git_url` as it may contain PAT;
# we want an allow-list over block-list to avoid exposing PAT in case
# if the author of the config makes a typo like `giit` instead of `git`.
EXPOSED_EXHIBIT_KEYS = ["repository", "title", "description", "icon"]


def extract_repository_name(git_url: str) -> str:
    fragment = git_url.split("/")[-1]
    if fragment.endswith(".git"):
        return fragment[:-4]
    return fragment


def prepare_exhibit(exhibit_config) -> dict:
    exposed_config = {
        k: v for k, v in exhibit_config.items() if k in EXPOSED_EXHIBIT_KEYS
    }
    clone_destination = Path("examples")
    repository_name = extract_repository_name(exhibit_config["git"])
    local_path = clone_destination / repository_name

    # we probably want a tratilet to configure path into which the exhibits should be cloned
    # path/relative/to/root/if/cloned
    exposed_config["localPath"] = local_path  # e.g. "examples/nebari"
    exposed_config["revision"] = "2a2f2ee779ac21b70339da6551c2f6b0b00f6efe"
    # timestamp from .git/FETCH_HEAD of the cloned repo
    exposed_config["lastUpdated"] = "2024-05-01"
    exposed_config["currentTag"] = "v3.2.4"
    # the UI can show that there are X updates available; it could also show
    # a summary of the commits available, or tags available; possibly the name
    # of the most recent tag and would be sufficient over sending the list of commits,
    # which can be long and delay the initialization.
    exposed_config["updatesAvailable"] = True
    exposed_config["newestTag"] = "v3.2.5"
    exposed_config["updates"] = [
        {
            "revision": "02f04c339f880540064d2223176830afdd02f5fa",
            "title": "commit description",
            "description": "long commit description",
            "date": "date in format returned by git",
        }
    ]
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
                        prepare_exhibit(exhibit_config) for exhibit_config in exhibits
                    ],
                    "api_version": "1.0",
                }
            )
        )


def setup_handlers(web_app):
    host_pattern = ".*$"

    base_url = web_app.settings["base_url"]
    exhibits_pattern = url_path_join(base_url, "jupyterlab-gallery", "exhibits")
    handlers = [(exhibits_pattern, ExhibitsHandler)]
    web_app.add_handlers(host_pattern, handlers)
