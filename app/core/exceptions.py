class SchedulingConflictError(Exception):
    """Raised when an appointment overlaps an existing local appointment."""


class ExternalServiceNotConfiguredError(Exception):
    """Raised when an integration method needs credentials that are not configured."""


class ExternalServiceError(Exception):
    """Raised when an external API call fails."""

