"""Triage: sorts newly requested movies into the right Radarr library."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("triage")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"
