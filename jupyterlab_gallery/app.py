from jupyter_server.extension.application import ExtensionApp
from jupyter_server.serverapp import ServerApp
from .handlers import ExhibitsHandler, GalleryHandler, PullHandler
from .manager import GalleryManager


class GalleryApp(ExtensionApp):
    name = "gallery"

    handlers = [
        ("jupyterlab-gallery/gallery", GalleryHandler),
        ("jupyterlab-gallery/exhibits", ExhibitsHandler),
        ("jupyterlab-gallery/pull", PullHandler),
    ]

    default_url = "/jupyterlab-gallery/gallery"
    load_other_extensions = False

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

    @classmethod
    def make_serverapp(cls, **kwargs) -> ServerApp:
        """Instantiate the ServerApp

        Override to disable default_services which would give access
        to files on the disk (`contents` service) or allow execution
        code (`kernels` service).
        """
        server_app = super().make_serverapp(**kwargs)
        assert isinstance(server_app, cls.serverapp_class)
        assert len(server_app.default_services) > 1
        server_app.default_services = ("auth", "security")
        return server_app
