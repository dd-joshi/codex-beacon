"""Scene protocol v1 reference types and cryptography."""

from .crypto import (
    SessionKeys,
    auth_proof,
    b64url_decode,
    b64url_encode,
    derive_session_keys,
    open_envelope,
    seal_envelope,
)
from .compiler import compile_proposal
from .model import (
    DEFAULT_CAPABILITIES,
    Capabilities,
    DeviceScene,
    Keyframe,
    ProtocolValidationError,
    RGB,
)

__all__ = [
    "DEFAULT_CAPABILITIES",
    "Capabilities",
    "DeviceScene",
    "Keyframe",
    "ProtocolValidationError",
    "RGB",
    "SessionKeys",
    "auth_proof",
    "b64url_decode",
    "b64url_encode",
    "compile_proposal",
    "derive_session_keys",
    "open_envelope",
    "seal_envelope",
]
