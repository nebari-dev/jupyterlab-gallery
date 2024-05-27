try:
    from ._version import __version__
except ImportError:
    # Fallback when using the package in dev mode without installing
    # in editable mode with pip. It is highly recommended to install
    # the package from a stable release or in editable mode: https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs
    import warnings

    warnings.warn("Importing 'jupyterlab_gallery' outside a proper installation.")
    __version__ = "dev"
from .app import GalleryApp


def _jupyter_labextension_paths():
    return [{"src": "labextension", "dest": "jupyterlab-gallery"}]


def _jupyter_server_extension_points():
    return [{"module": "jupyterlab_gallery", "app": GalleryApp}]
