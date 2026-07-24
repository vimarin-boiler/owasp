"""Verificación mínima de inicialización, rutas y esquema de la aplicación."""

from app import create_app
from app.extensions import db


app = create_app(
    "testing",
    {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "RATELIMIT_ENABLED": False,
    },
)

with app.app_context():
    db.create_all()
    assert len(db.metadata.tables) == 31
    client = app.test_client()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    openapi = client.get("/api/v1/openapi.yaml")
    assert openapi.status_code == 200
    print("Smoke check OK: aplicación, API y 31 tablas inicializadas.")
