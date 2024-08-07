import json
from typing import cast

from jupyter_server.base.handlers import APIHandler
from .gitpuller import SyncHandlerBase
from .manager import GalleryManager
import tornado


# We do not want to expose `git_url` as it may contain PAT;
# we want an allow-list over block-list to avoid exposing PAT in case
# if the author of the config makes a typo like `giit` instead of `git`.
EXPOSED_EXHIBIT_KEYS = ["homepage", "title", "description", "icon"]


class BaseHandler(APIHandler):
    @property
    def gallery_manager(self) -> GalleryManager:
        return cast(GalleryManager, self.settings["gallery_manager"])


class GalleryHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.finish(
            json.dumps(
                {
                    "title": self.gallery_manager.title,
                    "exhibitsConfigured": len(self.gallery_manager.exhibits) != 0,
                    "hideGalleryWithoutExhibits": self.gallery_manager.hide_gallery_without_exhibits,
                    "apiVersion": "1.0",
                }
            )
        )


class ExhibitsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.finish(
            json.dumps(
                {
                    "exhibits": [
                        self._prepare_exhibit(exhibit_config, exhibit_id=i)
                        for i, exhibit_config in enumerate(
                            self.gallery_manager.exhibits
                        )
                    ]
                }
            )
        )

    def _prepare_exhibit(self, exhibit, exhibit_id: int) -> dict:
        exposed_config = {k: v for k, v in exhibit.items() if k in EXPOSED_EXHIBIT_KEYS}
        return {
            **exposed_config,
            **self.gallery_manager.get_exhibit_data(exhibit),
            "id": exhibit_id,
        }


class PullHandler(BaseHandler, SyncHandlerBase):
    @tornado.web.authenticated
    async def post(self):
        data = self.get_json_body()
        exhibit_id = data["exhibit_id"]
        try:
            exhibit = self.gallery_manager.exhibits[exhibit_id]
        except IndexError:
            self.set_status(406)
            self.finish(json.dumps({"message": f"exhibit_id {exhibit_id} not found"}))
            return

        branch = exhibit.get("branch")
        depth = exhibit.get("depth")

        if depth:
            depth = int(depth)

        return await super()._pull(
            repo=exhibit["git"],
            targetpath=str(self.gallery_manager.get_local_path(exhibit)),
            exhibit_id=exhibit_id,
            account=exhibit.get("account"),
            token=exhibit.get("token"),
            branch=branch,
            depth=depth,
        )

    @tornado.web.authenticated
    async def get(self):
        return await super()._stream()
