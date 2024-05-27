from pathlib import Path

from traitlets.config.configurable import LoggingConfigurable
from traitlets import Dict, List, Unicode


def extract_repository_owner(git_url: str) -> str:
    fragments = git_url.strip("/").split("/")
    return fragments[-2] if len(fragments) >= 2 else ""


def extract_repository_name(git_url: str) -> str:
    fragment = git_url.split("/")[-1]
    if fragment.endswith(".git"):
        return fragment[:-4]
    return fragment


class ExhibitManager(LoggingConfigurable):
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
        data["revision"] = "2a2f2ee779ac21b70339da6551c2f6b0b00f6efe"
        # timestamp from .git/FETCH_HEAD of the cloned repo
        data["lastUpdated"] = "2024-05-01"
        data["currentTag"] = "v3.2.4"
        # the UI can show that there are X updates available; it could also show
        # a summary of the commits available, or tags available; possibly the name
        # of the most recent tag and would be sufficient over sending the list of commits,
        # which can be long and delay the initialization.
        data["updatesAvailable"] = False
        data["isCloned"] = local_path.exists()
        data["newestTag"] = "v3.2.5"
        data["updates"] = [
            {
                "revision": "02f04c339f880540064d2223176830afdd02f5fa",
                "title": "commit description",
                "description": "long commit description",
                "date": "date in format returned by git",
            }
        ]
        return data
