from jupyterhub.singleuser.mixins import make_singleuser_app
from jupyter_server.serverapp import ServerApp
from .app import GalleryApp


class classproperty(property):
    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class HubGalleryApp(GalleryApp):
    # This is in a separate file because traitlets metaclass
    # will read from each property on start, including serverapp_class,
    # which will have side effects for the server if run outside of juypterhub

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
