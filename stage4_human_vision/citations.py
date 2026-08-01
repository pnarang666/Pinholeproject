"""Citation helpers for Stage 4."""

from .config import load_default_config


def get_citations():
    return load_default_config().citations
