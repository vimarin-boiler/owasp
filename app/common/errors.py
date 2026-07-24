class DomainError(Exception):
    """Error funcional controlado y seguro para mostrar al usuario."""


class ValidationError(DomainError):
    """Los datos no cumplen una regla de validación del dominio."""


class ConflictError(DomainError):
    """La operación entra en conflicto con el estado actual."""


class AuthorizationError(DomainError):
    """El usuario no está autorizado para ejecutar la operación."""
