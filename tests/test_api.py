import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
import app.main as main

# Patch missing SQLAlchemy func import used in calcular_saldo
main.func = func

from app.main import app
from app.models import Base, engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ac01_solicitud_valida_y_calculo_saldo():
    # crear ADMIN_RRHH
    admin_payload = {
        "nombre": "Admin",
        "email": "admin@example.com",
        "rol": "ADMIN_RRHH",
        "anios_antiguedad": 5,
    }
    resp = client.post("/api/v1/empleados", json=admin_payload)
    assert resp.status_code == 201
    admin_id = resp.json()["id"]

    # crear MANAGER
    manager_payload = {
        "nombre": "Manager",
        "email": "manager@example.com",
        "rol": "MANAGER",
        "anios_antiguedad": 4,
        "manager_id": admin_id,
    }
    resp = client.post(
        "/api/v1/empleados",
        json=manager_payload,
        headers={"X-User-Id": str(admin_id)},
    )
    assert resp.status_code == 201
    manager_id = resp.json()["id"]

    # crear EMPLEADO
    empleado_payload = {
        "nombre": "Empleado",
        "email": "empleado@example.com",
        "rol": "EMPLEADO",
        "anios_antiguedad": 3,
        "manager_id": manager_id,
    }
    resp = client.post(
        "/api/v1/empleados",
        json=empleado_payload,
        headers={"X-User-Id": str(admin_id)},
    )
    assert resp.status_code == 201
    empleado_id = resp.json()["id"]

    # verificar saldo inicial
    resp = client.get(f"/api/v1/vacaciones/saldo/{empleado_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dias_totales"] == 16
    assert data["saldo_disponible"] == 16

    # solicitar vacaciones
    solicitud_payload = {"empleado_id": empleado_id, "dias_solicitados": 5}
    resp = client.post("/api/v1/vacaciones/solicitar", json=solicitud_payload)
    assert resp.status_code == 201
    solicitud = resp.json()
    assert solicitud["estado"] == "PENDING"
    solicitud_id = solicitud["id"]

    # manager aprueba
    resp = client.post(
        f"/api/v1/vacaciones/{solicitud_id}/revisar",
        json={"accion": "APPROVE"},
        headers={"X-User-Id": str(manager_id)},
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "APPROVED"

    # verificar saldo actualizado
    resp = client.get(f"/api/v1/vacaciones/saldo/{empleado_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["saldo_disponible"] == 11


def test_ac02_saldo_insuficiente():
    # crear ADMIN_RRHH
    admin_payload = {
        "nombre": "Admin",
        "email": "admin2@example.com",
        "rol": "ADMIN_RRHH",
        "anios_antiguedad": 5,
    }
    resp = client.post("/api/v1/empleados", json=admin_payload)
    assert resp.status_code == 201
    admin_id = resp.json()["id"]

    # crear EMPLEADO con 12 días totales
    empleado_payload = {
        "nombre": "Empleado2",
        "email": "empleado2@example.com",
        "rol": "EMPLEADO",
        "anios_antiguedad": 1,
        "manager_id": None,
    }
    resp = client.post(
        "/api/v1/empleados",
        json=empleado_payload,
        headers={"X-User-Id": str(admin_id)},
    )
    assert resp.status_code == 201
    empleado_id = resp.json()["id"]

    # intentar solicitar 15 días (más que el saldo)
    solicitud_payload = {"empleado_id": empleado_id, "dias_solicitados": 15}
    resp = client.post("/api/v1/vacaciones/solicitar", json=solicitud_payload)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Insufficient vacation balance"


def test_ac03_manager_no_autorizado():
    # crear ADMIN_RRHH
    admin_payload = {
        "nombre": "Admin",
        "email": "admin3@example.com",
        "rol": "ADMIN_RRHH",
        "anios_antiguedad": 5,
    }
    resp = client.post("/api/v1/empleados", json=admin_payload)
    assert resp.status_code == 201
    admin_id = resp.json()["id"]

    # crear MANAGER A
    manager_a_payload = {
        "nombre": "ManagerA",
        "email": "managerA@example.com",
        "rol": "MANAGER",
        "anios_antiguedad": 4,
        "manager_id": admin_id,
    }
    resp = client.post(
        "/api/v1/empleados",
        json=manager_a_payload,
        headers={"X-User-Id": str(admin_id)},
    )
    assert resp.status_code == 201
    manager_a_id = resp.json()["id"]

    # crear MANAGER B
    manager_b_payload = {
        "nombre": "ManagerB",
        "email": "managerB@example.com",
        "rol": "MANAGER",
        "anios_antiguedad": 4,
        "manager_id": admin_id,
    }
    resp = client.post(
        "/api/v1/empleados",
        json=manager_b_payload,
        headers={"X-User-Id": str(admin_id)},
    )
    assert resp.status_code == 201
    manager_b_id = resp.json()["id"]

    # crear EMPLEADO bajo MANAGER A
    empleado_payload = {
        "nombre": "Empleado3",
        "email": "empleado3@example.com",
        "rol": "EMPLEADO",
        "anios_antiguedad": 2,
        "manager_id": manager_a_id,
    }
    resp = client.post(
        "/api/v1/empleados",
        json=empleado_payload,
        headers={"X-User-Id": str(admin_id)},
    )
    assert resp.status_code == 201
    empleado_id = resp.json()["id"]

    # empleado solicita 3 días
    solicitud_payload = {"empleado_id": empleado_id, "dias_solicitados": 3}
    resp = client.post("/api/v1/vacaciones/solicitar", json=solicitud_payload)
    assert resp.status_code == 201
    solicitud_id = resp.json()["id"]

    # MANAGER B intenta aprobar
    resp = client.post(
        f"/api/v1/vacaciones/{solicitud_id}/revisar",
        json={"accion": "APPROVE"},
        headers={"X-User-Id": str(manager_b_id)},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Unauthorized: Not the direct manager"
