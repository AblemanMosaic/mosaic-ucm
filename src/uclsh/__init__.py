"""Experimental self-hosting profile for the Universal Constitutional Language."""

from .bootstrap import bootstrap_compiler, bootstrap_corpus
from .canonical import canonical_bytes, root, sha256_bytes, strict_loads
from .compiler import compile_module_text
from .errors import UCLSHRefusal
from .vm import Machine

__all__ = [
    "Machine",
    "UCLSHRefusal",
    "bootstrap_compiler",
    "bootstrap_corpus",
    "canonical_bytes",
    "compile_module_text",
    "root",
    "sha256_bytes",
    "strict_loads",
]

