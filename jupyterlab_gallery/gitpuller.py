# Based on https://github.com/jupyterhub/nbgitpuller/blob/main/nbgitpuller/handlers.py
# which is distributed under BSD 3-Clause License
# Copyright (c) 2017, YuviPanda, Peter Veerman
#
# Modified to allow:
# - restricting which repositories can be cloned
# - reconnecting to the event stream when refreshing the browser
# - handling multiple waiting pulls
from tornado import gen, web, locks
import asyncio
import logging
import traceback

import threading
import json
import os
from queue import Queue, Empty
from collections import defaultdict
from typing import Optional, TypedDict

import git
from jupyter_server.base.handlers import JupyterHandler
from nbgitpuller.pull import GitPuller
from tornado.iostream import StreamClosedError

from .git_utils import git_credentials


class CloneProgress(git.RemoteProgress):
    def __init__(self):
        self.queue = Queue()
        self.max_stage = 0.01
        self.prev_stage = 0
        super().__init__()

    def update(self, op_code: int, cur_count, max_count=None, message=""):
        if op_code & git.RemoteProgress.BEGIN:
            new_stage = None
            if op_code & git.RemoteProgress.COUNTING:
                new_stage = 0.05
            elif op_code & git.RemoteProgress.COMPRESSING:
                new_stage = 0.10
            elif op_code & git.RemoteProgress.RECEIVING:
                new_stage = 0.90
            elif op_code & git.RemoteProgress.RESOLVING:
                new_stage = 1

            if new_stage:
                self.prev_stage = self.max_stage
                self.max_stage = new_stage

        if isinstance(cur_count, (int, float)) and isinstance(max_count, (int, float)):
            progress = self.prev_stage + cur_count / max_count * (
                self.max_stage - self.prev_stage
            )
            self.queue.put(
                Update(
                    progress=progress,
                    message=message,
                )
            )
            # self.queue.join()


class ProgressGitPuller(GitPuller):
    def __init__(
        self, git_url, repo_dir, token: Optional[str], account: Optional[str], **kwargs
    ):
        self._token = token
        self._account = account
        # it will attempt to resolve default branch which requires credentials too
        with git_credentials(token=self._token, account=self._account):
            super().__init__(git_url, repo_dir, **kwargs)

    def initialize_repo(self):
        logging.info("Repo {} doesn't exist. Cloning...".format(self.repo_dir))
        progress = CloneProgress()

        def clone_task():
            with git_credentials(token=self._token, account=self._account):
                try:
                    git.Repo.clone_from(
                        self.git_url,
                        self.repo_dir,
                        branch=self.branch_name,
                        progress=progress,
                    )
                except Exception as e:
                    progress.queue.put(e)
                finally:
                    progress.queue.put(None)

        threading.Thread(target=clone_task).start()
        # TODO: add configurable timeout
        # timeout = 60

        while True:
            item = progress.queue.get(True)  # , timeout)
            if item is None:
                break
            yield item

        logging.info("Repo {} initialized".format(self.repo_dir))

    def update(self):
        with git_credentials(token=self._token, account=self._account):
            yield from super().update()


class Update(TypedDict):
    progress: float
    message: str


class SyncHandlerBase(JupyterHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "pull_status_queues" not in self.settings:
            self.settings["pull_status_queues"] = defaultdict(Queue)

        if "last_message" not in self.settings:
            self.settings["last_message"] = {}

        # We use this lock to make sure that only one sync operation
        # can be happening at a time. Git doesn't like concurrent use!
        if "git_lock" not in self.settings:
            self.settings["git_lock"] = locks.Lock()

        if "enqueue_task" not in self.settings:
            task = asyncio.create_task(self._enqueue_messages())
            self.settings["enqueue_task"] = task
            task.add_done_callback(lambda task: self.settings.pop("enqueue_task"))

    def get_login_url(self):
        # raise on failed auth, not redirect
        # can't redirect EventStream to login
        # same as Jupyter's APIHandler
        raise web.HTTPError(403)

    @property
    def git_lock(self):
        return self.settings["git_lock"]

    async def _pull(
        self,
        repo: str,
        targetpath: str,
        exhibit_id: int,
        token: Optional[str],
        account: Optional[str],
    ):
        q = self.settings["pull_status_queues"][exhibit_id]
        try:
            q.put_nowait(Update(progress=0.01, message="Waiting for a lock"))
            await self.git_lock.acquire(5)
            q.put_nowait(Update(progress=0.02, message="Lock acquired"))
        except gen.TimeoutError:
            q.put_nowait(
                gen.TimeoutError(
                    "Another git operations is currently running, try again in a few minutes"
                )
            )
            return

        try:
            branch = self.get_argument("branch", None)
            depth = self.get_argument("depth", None)
            if depth:
                depth = int(depth)
            # The default working directory is the directory from which Jupyter
            # server is launched, which is not the same as the root notebook
            # directory assuming either --notebook-dir= is used from the
            # command line or c.NotebookApp.notebook_dir is set in the jupyter
            # configuration. This line assures that all repos are cloned
            # relative to server_root_dir/<optional NBGITPULLER_PARENTPATH>,
            # so that all repos are always in scope after cloning. Sometimes
            # server_root_dir will include things like `~` and so the path
            # must be expanded.
            repo_parent_dir = os.path.join(
                os.path.expanduser(self.settings["server_root_dir"]),
                os.getenv("NBGITPULLER_PARENTPATH", ""),
            )
            repo_dir = os.path.join(repo_parent_dir, targetpath or repo.split("/")[-1])

            gp = ProgressGitPuller(
                repo,
                repo_dir,
                branch=branch,
                depth=depth,
                parent=self.settings["nbapp"],
                # our additions
                token=token,
                account=account,
            )

            def pull():
                try:
                    for update in gp.pull():
                        q.put_nowait(update)
                    # Sentinel when we're done
                    q.put_nowait(None)
                except Exception as e:
                    raise e

            self.gp_thread = threading.Thread(target=pull)
            self.gp_thread.start()
        except Exception as e:
            q.put_nowait(e)
        finally:
            self.git_lock.release()

    async def emit(self, data: dict):
        serialized_data = json.dumps(data)
        self.write("data: {}\n\n".format(serialized_data))
        await self.flush()

    async def _enqueue_messages(self):
        last_message = self.settings["last_message"]
        queues = self.settings["pull_status_queues"]
        while True:
            empty_queues = 0
            # copy to avoid error due to size change during iteration:
            queues_view = queues.copy()
            for exhibit_id, q in queues_view.items():
                # try to consume next message
                try:
                    progress = q.get_nowait()
                except Empty:
                    empty_queues += 1
                    continue

                if progress is None:
                    msg = {"phase": "finished", "exhibit_id": exhibit_id}
                    del self.settings["pull_status_queues"][exhibit_id]
                elif isinstance(progress, dict):
                    msg = {
                        "output": progress,
                        "phase": "progress",
                        "exhibit_id": exhibit_id,
                    }
                elif isinstance(progress, Exception):
                    msg = {
                        "phase": "error",
                        "exhibit_id": exhibit_id,
                        "message": str(progress),
                        "output": "\n".join(
                            [
                                line.strip()
                                for line in traceback.format_exception(
                                    type(progress), progress, progress.__traceback__
                                )
                            ]
                        ),
                    }
                else:
                    msg = {
                        "output": progress,
                        "phase": "syncing",
                        "exhibit_id": exhibit_id,
                    }

                last_message[exhibit_id] = msg

            if empty_queues == len(queues_view):
                await gen.sleep(0.1)

    async def _stream(self):
        # We gonna send out event streams!
        self.set_header("content-type", "text/event-stream")
        self.set_header("cache-control", "no-cache")

        # https://bugzilla.mozilla.org/show_bug.cgi?id=833462
        await self.emit({"phase": "connected"})

        last_message = self.settings["last_message"]
        last_message_sent = {}

        # stream new messages as they are put on respective queues
        while True:
            messages_view = last_message.copy()
            unchanged = 0
            for exhibit_id, msg in messages_view.items():
                # emit an update if anything changed
                if last_message_sent.get(exhibit_id) == msg:
                    unchanged += 1
                    continue
                last_message_sent[exhibit_id] = msg
                try:
                    await self.emit(msg)
                except StreamClosedError as e:
                    # this is expected to happen whenever client closes (e.g. user
                    # closes the browser or refreshes the tab with JupterLab)
                    if e.real_error:
                        self.warn.info(
                            f"git puller stream got closed with error {e.real_error}"
                        )
                    else:
                        self.log.info("git puller stream closed")
                    # return to stop reading messages, so that the next
                    # client who connects can consume them
                    return
            if unchanged == len(messages_view):
                await gen.sleep(0.1)
