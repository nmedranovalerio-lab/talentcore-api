https://talentcore-api-3cj5.onrender.com/docs

Sirve para gestionar empleados y sus vacaciones.
Construido con FastAPI, SQLAlchemy y SQLite, y desarrollado con un flujo de
agentes de IA (Product Owner, Arquitecto, Developer y QA).

Casos de uso

- Registrar empleados con su rol (Empleado, Manager o Admin_rhh).
- Consultar el saldo de vacaciones según los años de antigüedad:
  12 días el primer año, +2 por cada año adicional, con un límite de 20.
- Solicitar días libres, validando que no se pida más que el saldo disponible.
- Aprobar o rechazar solicitudes valida que únicamente  el jefe directo puede hacerlo.

5 endpoints
Método	Ruta	Nombre en Swagger
POST	Crear Empleado
GET		Obtener Saldo
POST	Solicitar Vacaciones
POST	Revisar Solicitud
