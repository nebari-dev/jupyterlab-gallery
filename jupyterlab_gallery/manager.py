from datetime import datetime
from pathlib import Path

from traitlets.config.configurable import LoggingConfigurable
from traitlets import Dict, List, Unicode

from .git_utils import (
    extract_repository_owner,
    extract_repository_name,
    git_credentials,
    has_updates,
)


class GalleryManager(LoggingConfigurable):
    root_dir = Unicode(
        config=False,
        allow_none=True,
    )

    exhibits = List(
        Dict(
            per_key_traits={
                "git": Unicode(help="Git URL used for cloning"),
                "homepage": Unicode(help="User-facing URL to open if any"),
                "title": Unicode(help="Name of the exhibit"),
                "description": Unicode(help="Short description"),
                "token": Unicode(
                    help="Personal access token - required if the repository is private"
                ),
                "account": Unicode(
                    help="Username or name of application - required if the repository is private"
                ),
                # TODO: validate path exists
                "icon": Unicode(help="Path to an svg or png, or base64 encoded string"),
                # other ideas: `path_in_repository`, `documentation_url`
            }
        ),
        config=True,
        allow_none=False,
        default_value=[
            {
                "git": "https://github.com/nebari-dev/nebari.git",
                "homepage": "https://github.com/nebari-dev/nebari/",
                "title": "Nebari",
                "description": "🪴 Nebari - your open source data science platform",
            },
            {
                "git": "https://github.com/nebari-dev/nebari-docker-images.git",
                "homepage": "https://github.com/nebari-dev/nebari-docker-images/",
                "title": "Nebari docker images",
                "description": "Nebari Docker images",
            },
        ],
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

    def get_local_path(self, exhibit) -> Path:
        clone_destination = Path(self.destination)
        repository_name = extract_repository_name(exhibit["git"])
        return clone_destination / repository_name

    def get_exhibit_data(self, exhibit):
        data = {}

        if "icon" not in exhibit:
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
            if fetch_head.exists():
                data["lastUpdated"] = datetime.fromtimestamp(
                    fetch_head.stat().st_mtime
                ).isoformat()
            with git_credentials(
                account=exhibit.get("account"), token=exhibit.get("token")
            ):
                # TODO: this is blocking initial load; can we make it async?
                data["updatesAvailable"] = has_updates(local_path)

        return data
