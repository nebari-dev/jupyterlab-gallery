from contextlib import contextmanager
from pathlib import Path
from subprocess import run
from threading import Lock
from typing import Optional
import re
import os


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
        run(
            "git fetch origin $(git branch --show-current) --quiet",
            cwd=repo_path,
            shell=True,
        )
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


_git_credential_lock = Lock()


@contextmanager
def git_credentials(token: Optional[str], account: Optional[str]):
    if token and account:
        _git_credential_lock.acquire()
        try:
            path = Path(__file__).parent
            os.environ["GIT_ASKPASS"] = str(path / "git_askpass.py")
            os.environ["GIT_PULLER_ACCOUNT"] = account
            os.environ["GIT_PULLER_TOKEN"] = token
            # do not prompt user if askpass fails as this would
            # dead lock execution!
            os.environ["GIT_TERMINAL_PROMPT"] = "0"
            yield
        finally:
            del os.environ["GIT_PULLER_ACCOUNT"]
            del os.environ["GIT_PULLER_TOKEN"]
            del os.environ["GIT_TERMINAL_PROMPT"]
            del os.environ["GIT_ASKPASS"]
            _git_credential_lock.release()
    else:
        yield
