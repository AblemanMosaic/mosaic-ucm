from .label import build, sync
from .base import ComponentHandler

HANDLER = ComponentHandler("STATUS", build=build, sync=sync)
