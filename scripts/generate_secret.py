"""Genera una SECRET_KEY criptográficamente aleatoria para el archivo .env."""

import secrets


if __name__ == "__main__":
    print(secrets.token_urlsafe(48))
