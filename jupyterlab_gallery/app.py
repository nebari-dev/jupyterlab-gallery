from jupyter_server.extension.application import ExtensionApp
from .handlers import ExhibitsHandler, PullHandler
from .manager import ExhibitManager


class GalleryApp(ExtensionApp):
    name = "jupyterlab-gallery"

    handlers = [
        ("jupyterlab-gallery/exhibits", ExhibitsHandler),
        ("jupyterlab-gallery/pull", PullHandler),
    ]

    # default_url = "/jupyterlab-gallery"
    # load_other_extensions = True
    # file_url_prefix = "/gallery"

    def initialize_settings(self):
        self.log.info("Configured gallery manager")
        exhibit_manager = ExhibitManager(
            log=self.log, root_dir=self.serverapp.root_dir, config=self.config
        )
        self.settings.update({"exhibit_manager": exhibit_manager})

    def initialize_handlers(self):
        # setting nbapp is needed for nbgitpuller
        self.serverapp.web_app.settings["nbapp"] = self.serverapp

        self.log.info(f"Registered {self.name} server extension")
