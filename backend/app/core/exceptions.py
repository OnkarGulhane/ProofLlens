"""Domain exception definitions and standardized error responses."""

from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class ProofLensException(Exception):
    """Base exception for all ProofLens domain errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details


class DocumentValidationError(ProofLensException):
    """Raised when an uploaded document fails validation."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="DOCUMENT_VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class DocumentNotFoundError(ProofLensException):
    """Raised when a requested document does not exist."""

    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document with ID '{document_id}' was not found.",
            error_code="DOCUMENT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class WorkspaceNotFoundError(ProofLensException):
    """Raised when a requested workspace does not exist."""

    def __init__(self, workspace_id: str):
        super().__init__(
            message=f"Workspace with ID '{workspace_id}' was not found.",
            error_code="WORKSPACE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InsufficientEvidenceError(ProofLensException):
    """Raised when retrieval yields zero evidence above similarity threshold."""

    def __init__(self, message: str = "Insufficient evidence to answer query.", details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_EVIDENCE",
            status_code=status.HTTP_200_OK,  # 200 OK with abstention payload
            details=details,
        )


async def prooflens_exception_handler(request: Request, exc: ProofLensException) -> JSONResponse:
    """FastAPI exception handler for ProofLens domain exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )
