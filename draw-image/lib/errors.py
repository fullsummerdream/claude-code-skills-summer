"""Custom exceptions and error classification for image generation."""

from __future__ import annotations

from typing import Optional


class GenerateError(RuntimeError):
    """Base error. Carries the provider error code when available."""

    def __init__(self, message: str, *, code: Optional[str] = None, http_status: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class InvalidParameterError(GenerateError):
    """400-class: request payload rejected."""


class AuthenticationError(GenerateError):
    """401/403-class: API key invalid or model not authorized."""


class NotFoundError(GenerateError):
    """404-class: model id / endpoint not found."""


class QuotaExceededError(GenerateError):
    """402/403-class: out of credits."""


class RateLimitError(GenerateError):
    """429-class: too many requests."""


class SensitiveContentError(GenerateError):
    """Prompt or output blocked by content moderation."""


class InternalServerError(GenerateError):
    """5xx-class: provider internal error, safe to retry."""


# Common error-code prefixes (covers volcengine ARK + OpenAI + Aliyun bailian).
# Adding a new provider? Append its prefixes here.
_CODE_MAP = [
    ("InvalidEndpointOrModel", NotFoundError),
    ("ModelNotFound", NotFoundError),
    ("InvalidParameter", InvalidParameterError),
    ("Authentication", AuthenticationError),
    ("Unauthorized", AuthenticationError),
    ("AccessDenied", AuthenticationError),
    ("Forbidden", AuthenticationError),
    ("QuotaExceeded", QuotaExceededError),
    ("InsufficientBalance", QuotaExceededError),
    ("RateLimit", RateLimitError),
    ("Throttling", RateLimitError),
    ("TooManyRequests", RateLimitError),
    ("Sensitive", SensitiveContentError),
    ("ContentBlocked", SensitiveContentError),
    ("content_policy_violation", SensitiveContentError),
]


def classify(code: str, message: str, *, http_status: Optional[int] = None) -> GenerateError:
    """Pick the right exception class for an upstream error code."""
    for prefix, cls in _CODE_MAP:
        if code and code.startswith(prefix):
            return cls(message, code=code, http_status=http_status)
    if http_status and 500 <= http_status < 600:
        return InternalServerError(message, code=code, http_status=http_status)
    if http_status == 429:
        return RateLimitError(message, code=code, http_status=http_status)
    if http_status in (401, 403):
        return AuthenticationError(message, code=code, http_status=http_status)
    if http_status == 404:
        return NotFoundError(message, code=code, http_status=http_status)
    return GenerateError(message, code=code, http_status=http_status)
