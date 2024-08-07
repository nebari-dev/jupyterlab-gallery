from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from threading import Thread

from traitlets.config.configurable import LoggingConfigurable
from traitlets import Dict, List, Unicode, Bool, Int

from .git_utils import (
    extract_repository_owner,
    extract_repository_name,
    git_credentials,
    has_updates,
)


class GalleryManager(LoggingConfigurable):
    _has_updates: dict[str, Optional[bool]] = defaultdict(lambda: None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._background_tasks = set()

    root_dir = Unicode(
        config=False,
        allow_none=True,
    )

    exhibits = List(
        Dict(
            per_key_traits={
                "git": Unicode(help="Git URL used for cloning"),
                "title": Unicode(help="Name of the exhibit"),
                "homepage": Unicode(
                    help="User-facing URL to open if any", allow_none=True
                ),
                "description": Unicode(help="Short description", allow_none=True),
                "token": Unicode(
                    help="Personal access token - required if the repository is private",
                    allow_none=True,
                ),
                "account": Unicode(
                    help="Username or name of application - required if the repository is private",
                    allow_none=True,
                ),
                # TODO: validate path exists
                "icon": Unicode(
                    help="Path to an svg or png, or base64 encoded string",
                    allow_none=True,
                ),
                "branch": Unicode(
                    default_value=None, help="Branch to use", allow_none=True
                ),
                "depth": Int(
                    default_value=None, help="Depth of the clone", allow_none=True
                ),
                # other ideas: `path_in_repository`, `documentation_url`
            }
        ),
        config=True,
        allow_none=False,
        default_value=[],
    )

    destination = Unicode(
        help="The directory into which the exhibits will be cloned",
        default_value="gallery",
        config=True,
    )

    title = Unicode(
        help="The the display name of the Gallery widget",
        default_value="Gallery",
        config=True,
    )

    hide_gallery_without_exhibits = Bool(
        help="Hide Gallery if no exhibits are configured",
        default_value=False,
        config=True,
    )

    def get_local_path(self, exhibit) -> Path:
        clone_destination = Path(self.destination)
        repository_name = extract_repository_name(exhibit["git"])
        return clone_destination / repository_name

    def _check_updates(self, exhibit):
        local_path = self.get_local_path(exhibit)
        with git_credentials(
            account=exhibit.get("account"), token=exhibit.get("token")
        ):
            self._has_updates[local_path] = has_updates(local_path)

    def get_exhibit_data(self, exhibit):
        data = {}

        if "icon" not in exhibit or not exhibit["icon"]:
            homepage = exhibit.get("homepage")
            if homepage and homepage.startswith("https://github.com/"):
                repository_name = extract_repository_name(exhibit["git"])
                repository_owner = extract_repository_owner(homepage)
                data["icon"] = (
                    f"https://opengraph.githubassets.com/1/{repository_owner}/{repository_name}"
                )

        local_path = self.get_local_path(exhibit)

        data["localPath"] = str(local_path)
        exists = local_path.exists()
        data["isCloned"] = exists
        if exists:
            fetch_head = local_path / ".git" / "FETCH_HEAD"
            head = local_path / ".git" / "HEAD"
            date_head = fetch_head if fetch_head.exists() else head
            if date_head.exists():
                data["lastUpdated"] = datetime.fromtimestamp(
                    date_head.stat().st_mtime
                ).isoformat()
            data["updatesAvailable"] = self._has_updates[local_path]

            def check_updates():
                self._check_updates(exhibit)

            Thread(target=check_updates).start()
        return data
