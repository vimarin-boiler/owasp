class DomainError(Exception):
    """Error funcional controlado y seguro para mostrar al usuario."""


class ValidationError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class AuthorizationError(DomainError):
    pass
