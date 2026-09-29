from __future__ import annotations

from typing import Any


class StemLabError(Exception):
    """Expected engine failure that is safe to expose as structured data."""

    code = "stemlab_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InputNotFoundError(StemLabError):
    code = "input_not_found"


class InputValidationError(StemLabError):
    code = "input_validation"


class ModelMissingError(StemLabError):
    code = "model_missing"


class ModelIntegrityError(StemLabError):
    code = "model_integrity"


class DeviceUnavailableError(StemLabError):
    code = "device_unavailable"


class BackendSeparationError(StemLabError):
    code = "backend_separation"


class OutputPathError(StemLabError):
    code = "output_path"


class OutputValidationError(StemLabError):
    code = "output_validation"


class InputModifiedError(StemLabError):
    code = "input_modified"
