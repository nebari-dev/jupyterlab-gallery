from jupyter_server.extension.application import ExtensionApp
from .handlers import ExhibitsHandler, GalleryHandler, PullHandler
from .manager import GalleryManager


class GalleryApp(ExtensionApp):
    name = "gallery"

    handlers = [
        ("jupyterlab-gallery/gallery", GalleryHandler),
        ("jupyterlab-gallery/exhibits", ExhibitsHandler),
        ("jupyterlab-gallery/pull", PullHandler),
    ]

    # default_url = "/jupyterlab-gallery"
    # load_other_extensions = True
    # file_url_prefix = "/gallery"

    def initialize_settings(self):
        self.log.info("Configured gallery manager")
        gallery_manager = GalleryManager(
            log=self.log, root_dir=self.serverapp.root_dir, config=self.config
        )
        self.settings.update({"gallery_manager": gallery_manager})

    def initialize_handlers(self):
        # setting nbapp is needed for nbgitpuller
        self.serverapp.web_app.settings["nbapp"] = self.serverapp

        self.log.info(f"Registered {self.name} server extension")
