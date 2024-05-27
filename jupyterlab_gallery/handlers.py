import json
from typing import cast

from jupyter_server.base.handlers import APIHandler
from .gitpuller import SyncHandlerBase
from .manager import ExhibitManager
import tornado


# We do not want to expose `git_url` as it may contain PAT;
# we want an allow-list over block-list to avoid exposing PAT in case
# if the author of the config makes a typo like `giit` instead of `git`.
EXPOSED_EXHIBIT_KEYS = ["repository", "title", "description", "icon"]


class ExhibitsHandler(APIHandler):
    @property
    def exhibit_manager(self) -> ExhibitManager:
        return cast(ExhibitManager, self.settings["exhibit_manager"])

    # The following decorator should be present on all verb methods (head, get, post,
    # patch, put, delete, options) to ensure only authorized user can request the
    # Jupyter server
    @tornado.web.authenticated
    def get(self):
        self.finish(
            json.dumps(
                {
                    "exhibits": [
                        self._prepare_exhibit(exhibit_config, exhibit_id=i)
                        for i, exhibit_config in enumerate(
                            self.exhibit_manager.exhibits
                        )
                    ],
                    "apiVersion": "1.0",
                }
            )
        )

    def _prepare_exhibit(self, exhibit, exhibit_id: int) -> dict:
        exposed_config = {k: v for k, v in exhibit.items() if k in EXPOSED_EXHIBIT_KEYS}
        return {
            **self.exhibit_manager.get_exhibit_data(exhibit),
            **exposed_config,
            "id": exhibit_id,
        }


class PullHandler(SyncHandlerBase):
    @property
    def exhibit_manager(self) -> ExhibitManager:
        return cast(ExhibitManager, self.settings["exhibit_manager"])

    @tornado.web.authenticated
    async def post(self):
        data = self.get_json_body()
        exhibit_id = data["exhibit_id"]
        exhibit = self.exhibit_manager.exhibits[exhibit_id]
        return await super()._pull(
            repo=exhibit["git"],
            exhibit_id=exhibit_id,
            # branch
            # depth
            targetpath=str(self.exhibit_manager.get_local_path(exhibit)),
        )

    @tornado.web.authenticated
    async def get(self):
        return await super()._stream()
