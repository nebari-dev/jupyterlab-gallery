from jupyter_server.extension.application import ExtensionApp
from jupyter_server.serverapp import ServerApp
from .handlers import ExhibitsHandler, GalleryHandler, PullHandler
from .manager import GalleryManager


try:
    from jupyterhub.singleuser.mixins import make_singleuser_app
except ImportError:

    def make_singleuser_app(cls):
        return cls


class classproperty(property):
    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


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

    @classproperty
    def serverapp_class(cls):
        """If jupyterhub is installed, apply the jupyterhub patches,

        but only do this when this property is accessed, which is when
        the gallery is used as a standalone app.
        """
        if cls._server_cls is None:
            cls._server_cls = make_singleuser_app(ServerApp)
        return cls._server_cls

    _server_cls = None

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
