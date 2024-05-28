from datetime import datetime
from pathlib import Path

from traitlets.config.configurable import LoggingConfigurable
from traitlets import Dict, List, Unicode
from subprocess import run
import re


def extract_repository_owner(git_url: str) -> str:
    fragments = git_url.strip("/").split("/")
    return fragments[-2] if len(fragments) >= 2 else ""


def extract_repository_name(git_url: str) -> str:
    fragment = git_url.split("/")[-1]
    if fragment.endswith(".git"):
        return fragment[:-4]
    return fragment


def has_updates(repo_path: Path) -> bool:
    try:
        result = run(
            "git status -b --porcelain -u n --ignored n",
            cwd=repo_path,
            capture_output=True,
            shell=True,
        )
    except FileNotFoundError:
        return False
    data = re.match(
        r"^## (.*?)( \[(ahead (?P<ahead>\d+))?(, )?(behind (?P<behind>\d+))?\])?$",
        result.stdout.decode("utf-8"),
    )
    if not data:
        return False
    return data["behind"] is not None


class GalleryManager(LoggingConfigurable):
    root_dir = Unicode(
        config=False,
        allow_none=True,
    )

    exhibits = List(
        Dict(
            per_key_traits={
                "git": Unicode(
                    help="Git URL used for cloning  (can include branch, PAT) - not show to the user"
                ),
                "repository": Unicode(help="User-facing URL of the repository"),
                "title": Unicode(help="Name of the exhibit"),
                "description": Unicode(help="Short description"),
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
                "repository": "https://github.com/nebari-dev/nebari/",
                "title": "Nebari",
                "description": "🪴 Nebari - your open source data science platform",
            },
            {
                "git": "https://github.com/nebari-dev/nebari-docker-images.git",
                "repository": "https://github.com/nebari-dev/nebari-docker-images/",
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
            if exhibit["repository"].startswith("https://github.com/"):
                repository_name = extract_repository_name(exhibit["git"])
                repository_owner = extract_repository_owner(exhibit["repository"])
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
            data["updatesAvailable"] = has_updates(local_path)

        return data
