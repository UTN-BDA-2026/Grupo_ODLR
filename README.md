# pdf_extractext

API REST para extracción de texto y resumen inteligente de archivos PDF, construida con FastAPI y MongoDB.

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| Base de datos | MongoDB 7.0 |
| Driver async | Motor + Beanie |
| Autenticación | JWT (PyJWT) + pbkdf2_sha256 |
| Extracción PDF | PyMuPDF (fitz) |
| IA / Resumen | Ollama (llama3.2:3b) |
| Contenedores | Docker + Docker Compose |
| Migraciones | Sistema custom con lock distribuido |

## Temas implementados

- **Seguridad** — JWT, pbkdf2, validación de SECRET_KEY, capas de defensa
- **Índices** — B-Tree en MongoDB, unique, compuesto, parcial, sparse
- **Backup & Restore** — mongodump/mongorestore, scripts Python, endpoint REST
- **Transacciones** — ACID multi-documento con audit log atómico
- **Inteligencia Artificial** — Resumen automático de PDFs con LLM local (Ollama)

---

## Instalación y puesta en marcha

### Requisitos previos

- Docker Desktop (corriendo)
- Python 3.11+
- `uv` (gestor de paquetes)
- Git

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/UTN-BDA-2026/Grupo_ODLR
```

### Paso 2 — Crear el archivo `.env`

```bash
Copy-Item .env.example .env   # Windows
cp .env.example .env          # Linux/Mac
```

Editar `.env` y configurar al menos estas variables:

```env
MONGODB_URL=mongodb://mongodb:27017
MONGODB_DB_NAME=pdf_extract_db
SECRET_KEY=<clave-aleatoria-de-al-menos-32-caracteres>
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
```

Generar una `SECRET_KEY` segura:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Paso 3 — Levantar los containers

```bash
docker compose up -d
docker compose ps
```

Los tres containers deben aparecer en estado `Up`:

```
grupo_odlr-app-1       ...   Up   0.0.0.0:8000->8000/tcp
grupo_odlr-mongodb-1   ...   Up   0.0.0.0:27017->27017/tcp
grupo_odlr-ollama-1    ...   Up   0.0.0.0:11434->11434/tcp
```

### Paso 4 — Descargar el modelo de IA (solo la primera vez)

```bash
docker exec grupo_odlr-ollama-1 ollama pull llama3.2:3b
```

Esto descarga ~2GB. Solo es necesario hacerlo una vez; el modelo queda guardado en el volumen `ollama_data`.

### Paso 5 — Aplicar las migraciones

Las migraciones se ejecutan desde fuera del container, por lo que necesitás que `MONGODB_URL` apunte a `localhost` temporalmente:

```env
# En .env, cambiar a:
MONGODB_URL=mongodb://localhost:27017
```

```bash
uv sync
python -m migrations migrate
```

Después volver a dejar `MONGODB_URL=mongodb://mongodb:27017` y reiniciar:

```bash
docker compose restart app
```

### Paso 6 — Crear un usuario inicial

Abrir el Swagger en `http://localhost:8000/api/docs` y ejecutar `POST /api/v1/users/`:

```json
{
  "username": "admin",
  "email": "admin@test.com",
  "password": "admin123"
}
```

### Paso 7 — Verificar que todo funciona

```bash
curl http://localhost:8000/health
# Respuesta esperada: {"status": "healthy"}
```

---

## Referencia de endpoints

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| POST | `/api/v1/auth/login` | No | Obtener JWT token |
| GET | `/api/v1/auth/me` | Sí | Usuario actual |
| POST | `/api/v1/users/` | No | Crear usuario |
| POST | `/api/v1/pdf/upload` | Sí | Subir PDF |
| POST | `/api/v1/pdf/upload-audited` | Sí | Subir PDF con transacción ACID |
| GET | `/api/v1/pdf/` | Sí | Listar documentos |
| GET | `/api/v1/pdf/{id}` | Sí | Obtener documento |
| PUT | `/api/v1/pdf/{id}` | Sí | Actualizar documento |
| DELETE | `/api/v1/pdf/{id}` | Sí | Eliminar documento |
| POST | `/api/v1/pdf/{id}/summary` | Sí | Generar resumen con IA |
| POST | `/api/v1/admin/backup` | Sí | Triggear backup manual |
| GET | `/api/v1/admin/backups` | Sí | Listar backups disponibles |
| GET | `/api/v1/health/` | No | Health check |

---

## Tema 1: Índices

### Concepto

Un índice en MongoDB es una estructura B-Tree que permite resolver queries sin hacer un collection scan (COLLSCAN). Sin índice MongoDB recorre todos los documentos en O(n). Con índice va directo al resultado en O(log n).

### Índices creados

| Nombre | Campo | Tipo | Propósito |
|---|---|---|---|
| `idx_users_email_unique` | email | Único | Login rápido + integridad |
| `idx_users_username_unique` | username | Único | Integridad de datos |
| `idx_users_email_active` | (email, is_active) | Compuesto | Queries de autenticación |
| `idx_docs_checksum_unique` | checksum | Único + Sparse | Detección de duplicados |
| `idx_docs_filename` | filename | Simple | Búsqueda por nombre |
| `idx_docs_created_at_desc` | (created_at, -1) | Descendente | Paginación por fecha |
| `idx_docs_owner_active` | owner_id | Parcial | Solo docs activos en RAM |

### Cómo probar

**Verificar que los índices existen:**

```bash
docker compose exec mongodb mongosh --eval \
  "db.getSiblingDB('pdf_extract_db').documents.getIndexes().forEach(i => print(i.name))"
```

Resultado esperado:
```
_id_
idx_filename
idx_created_at_desc
idx_status_created_at
idx_docs_checksum_unique
idx_docs_owner_active
```

**Demostrar COLLSCAN vs IXSCAN:**

```bash
python scripts/demo_indexes.py
```

Resultado esperado:
```
=======================================================
  DEMO: explain() - COLLSCAN vs IXSCAN
=======================================================

  [✓] Detección de PDF duplicado
      Stage: IXSCAN — O(log n) — acceso directo

  [✓] Búsqueda por filename
      Stage: IXSCAN — O(log n) — acceso directo

  [✓] Login por email
      Stage: IXSCAN — O(log n) — acceso directo
```

---

## Tema 2: Backup & Restore

### Concepto

Un sistema de backup profesional cubre frecuencia, retención, verificación y restauración. Los dos KPIs clave son:

- **RPO** (Recovery Point Objective): cuánto dato se puede perder — depende de la frecuencia del backup
- **RTO** (Recovery Time Objective): cuánto tarda en recuperar — en este proyecto, segundos con mongorestore

### Archivos

| Archivo | Descripción |
|---|---|
| `scripts/backup.py` | Genera dump comprimido con timestamp |
| `scripts/restore.py` | Restaura desde backup específico o el más reciente |
| `backups/<timestamp>/` | Directorio con archivos `.bson.gz` y `manifest.json` |

### Cómo probar el ciclo completo

```bash
# 1. Verificar que hay documentos
docker compose exec mongodb mongosh --eval \
  "db.getSiblingDB('pdf_extract_db').documents.countDocuments()"

# 2. Hacer el backup
python scripts/backup.py

# 3. Simular pérdida de datos
docker compose exec mongodb mongosh --eval \
  "db.getSiblingDB('pdf_extract_db').documents.deleteMany({})"

# 4. Verificar que la DB está vacía
docker compose exec mongodb mongosh --eval \
  "db.getSiblingDB('pdf_extract_db').documents.countDocuments()"
# Debe mostrar: 0

# 5. Restaurar
python scripts/restore.py

# 6. Verificar que los datos volvieron
docker compose exec mongodb mongosh --eval \
  "db.getSiblingDB('pdf_extract_db').documents.countDocuments()"
# Debe mostrar el número original
```

### Desde Swagger

1. Abrir `http://localhost:8000/api/docs`
2. Login con `POST /api/v1/auth/login` y copiar el token
3. Click en **Authorize** y pegar el token
4. Ejecutar `POST /api/v1/admin/backup`
5. Ejecutar `GET /api/v1/admin/backups` para ver la lista

---

## Tema 3: Transacciones ACID

### Concepto

MongoDB soporta transacciones multi-documento desde la versión 4.0. Requiere replica set, configurado en este proyecto como `rs0` de un nodo.

| Propiedad | Significado | En MongoDB |
|---|---|---|
| Atomicidad | Todo o nada | Multi-document transactions |
| Consistencia | Estado válido a válido | Validators + transacciones |
| Isolation | Transacciones aisladas | Snapshot isolation |
| Durabilidad | Lo commiteado persiste | Write concern majority |

### Caso de uso implementado

El endpoint `POST /api/v1/pdf/upload-audited` realiza dos operaciones en una transacción atómica:

1. Insertar el documento PDF en la colección `documents`
2. Registrar el evento en la colección `audit_log`

Si cualquiera de las dos falla, **ambas se revierten**.

### Cómo probar

**Prueba 1 — Flujo normal:**

1. Autenticarse en Swagger
2. Ejecutar `POST /api/v1/pdf/upload-audited` con un archivo PDF
3. Verificar que el documento se creó:

```bash
docker compose exec mongodb mongosh --eval \
  "db.getSiblingDB('pdf_extract_db').documents.find({},{filename:1,_id:0}).pretty()"
```

4. Verificar que el audit log se creó:

```bash
docker compose exec mongodb mongosh --eval \
  "db.getSiblingDB('pdf_extract_db').audit_log.find().pretty()"
```

**Prueba 2 — Demostrar rollback (atomicidad):**

Agregar temporalmente en `upload_pdf_with_audit` después del primer insert:

```python
raise Exception("Error simulado para demostrar rollback")
```

Luego reiniciar y ejecutar `POST /api/v1/pdf/upload-audited` — debe devolver error 500 y el documento NO debe quedar en la DB.

---

## Tema 4: Seguridad

### Capas implementadas

| Capa | Implementación | Protege contra |
|---|---|---|
| Transporte | HTTPS/TLS en producción | Intercepción de tráfico |
| Autenticación | JWT HS256, expiración 30 min | Acceso no autorizado |
| Contraseñas | pbkdf2_sha256 con salt | Fuerza bruta offline |
| Configuración | `.env` nunca commiteado | Exposición de secretos |
| Validación | Pydantic + Motor ODM | Inyección NoSQL |

### Cómo probar

**Sin token debe dar 401:**

```bash
curl http://localhost:8000/api/v1/pdf/
# {"detail": "Not authenticated"}
```

**Con token debe dar 200:**

```bash
# Obtener token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier": "admin", "password": "admin123"}'

# Usar el token
curl http://localhost:8000/api/v1/pdf/ \
  -H "Authorization: Bearer <TOKEN>"
```

**SECRET_KEY inválida impide arrancar:**

```bash
# Cambiar en .env: SECRET_KEY=change-me-in-production
docker compose restart app
docker compose logs app --tail=5
# La app falla en startup con error de validación
```

---

## Tema 5: Inteligencia Artificial — Resumen de PDFs

### Concepto

El proyecto integra [Ollama](https://ollama.com/) como motor de inferencia local, usando el modelo **llama3.2:3b**. Toda la inferencia ocurre dentro del entorno Docker, sin enviar datos a servicios externos — lo que garantiza privacidad total del contenido de los PDFs.

### Arquitectura

```
Cliente → POST /api/v1/pdf/{id}/summary
              ↓
         Verifica JWT
              ↓
         Busca documento en MongoDB
              ↓
         OllamaService.summarize(text)
              ↓
         POST http://ollama:11434/api/generate
              ↓
         Devuelve JSON con resumen
```

### Modelo utilizado

| Parámetro | Valor |
|---|---|
| Modelo | llama3.2:3b |
| Tamaño | ~2GB |
| Inferencia | CPU (sin GPU requerida) |
| Timeout | 300 segundos |
| Contexto máximo | 3000 caracteres de texto fuente |

### Cómo probar

1. Autenticarse en Swagger (`POST /api/v1/auth/login`)
2. Subir un PDF (`POST /api/v1/pdf/upload`)
3. Copiar el `id` del documento devuelto
4. Ejecutar `POST /api/v1/pdf/{id}/summary`

Respuesta esperada:

```json
{
  "document_id": "6a0dc3eb605a2fbb0c5546c1",
  "summary": "El documento trata sobre..."
}
```

> **Nota:** la primera inferencia puede tardar 1-2 minutos mientras Ollama carga el modelo en RAM. Las siguientes son significativamente más rápidas.

---

## Checklist de verificación

### Infraestructura

- [ ] `docker compose ps` muestra los tres containers en estado `Up`
- [ ] `docker compose logs app --tail=5` muestra `Successfully connected to MongoDB`
- [ ] `http://localhost:8000/health` devuelve `{"status": "healthy"}`
- [ ] `http://localhost:8000/api/docs` carga el Swagger UI

### Seguridad

- [ ] `GET /api/v1/pdf/` sin token devuelve 401
- [ ] `POST /api/v1/auth/login` con credenciales correctas devuelve token JWT
- [ ] `GET /api/v1/pdf/` con token devuelve 200

### Índices

- [ ] `db.documents.getIndexes()` muestra `idx_docs_checksum_unique`
- [ ] `db.users.getIndexes()` muestra `idx_users_email_unique`
- [ ] `python scripts/demo_indexes.py` muestra `IXSCAN` en todas las queries

### Backup & Restore

- [ ] `python scripts/backup.py` genera carpeta en `backups/`
- [ ] `deleteMany({})` vacía la colección
- [ ] `python scripts/restore.py` restaura los documentos
- [ ] `countDocuments()` vuelve al número original

### Transacciones

- [ ] `POST /api/v1/pdf/upload-audited` crea documento y registro en `audit_log`
- [ ] `db.audit_log.find()` muestra el registro con `action: 'upload'`
- [ ] Con `raise Exception` forzado, el documento NO queda en la DB (rollback)

### Inteligencia Artificial

- [ ] `docker exec grupo_odlr-ollama-1 ollama list` muestra `llama3.2:3b`
- [ ] `POST /api/v1/pdf/{id}/summary` devuelve un resumen en español
- [ ] El resumen se genera correctamente para distintos tipos de PDF

---

## Estructura del proyecto

```
pdf_extractext/
├── app/
│   ├── main.py
│   ├── api/v1/
│   │   ├── router.py
│   │   └── endpoints/
│   │       ├── auth.py
│   │       ├── pdf.py            # CRUD + /summary
│   │       ├── users.py
│   │       ├── admin.py          # Backup & Restore endpoints
│   │       └── health.py
│   ├── services/
│   │   ├── document_service.py   # upload_pdf_with_audit (transacciones)
│   │   ├── ollama_service.py     # Integración con Ollama
│   │   ├── pdf_service.py
│   │   └── auth_service.py
│   ├── repositories/
│   │   ├── document_repo.py
│   │   ├── audit_repository.py   # Audit log
│   │   └── user_repository.py
│   ├── core/
│   │   ├── config.py             # SECRET_KEY validator + OLLAMA settings
│   │   └── security.py
│   └── db/
│       └── database.py           # start_transaction()
├── migrations/
│   └── versions/
│       ├── 001_create_indexes.py
│       ├── 007_add_security_indexes.py   # Índices únicos y parciales
│       └── 008_add_audit_log.py          # Colección audit_log
├── scripts/
│   ├── backup.py                 # Script de backup
│   ├── restore.py                # Script de restore
│   └── demo_indexes.py           # Demo explain() para la defensa
├── backups/                      # Backups generados (en .gitignore)
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```
