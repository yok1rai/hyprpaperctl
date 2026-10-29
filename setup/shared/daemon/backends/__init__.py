from .openrc import OpenRC
from .runit import Runit
from .systemd import Systemd
from ..models import Installation, Layout


def backend(installation: Installation, layout: Layout):
    match installation.manager:
        case "systemd":
            return Systemd(installation, layout)
        case "openrc":
            return OpenRC(installation, layout)
        case "runit":
            return Runit(installation, layout)
        case _:
            raise ValueError("Unsupported service manager.")
