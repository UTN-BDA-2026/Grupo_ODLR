# pdf_extractext

API REST para extracción de texto y resumen inteligente de archivos PDF, construida con FastAPI y MongoDB. Incluye un frontend web (dashboard) servido con nginx.

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| Base de datos | MongoDB 7.0 (replica set `rs0`) con **auth SCRAM + TLS** |
| Driver async | Motor + patrón Repository |
| Autenticación | JWT (PyJWT) + pbkdf2_sha256 |
| Extracción PDF | PyMuPDF (fitz) |
| IA / Resumen | Ollama (llama3.2:3b) |
| Frontend | HTML + JS vanilla, servido con nginx |
| Contenedores | Docker + Docker Compose |
| Migraciones | Sistema custom con lock distribuido |

## Temas implementados

- **Seguridad** — JWT, pbkdf2, aislamiento por `owner_id`, **RBAC (rol de superusuario + panel de administración)**, **conexión a MongoDB cifrada (TLS) y autenticada (SCRAM) con usuario de menor privilegio**
- **Índices** — B-Tree en MongoDB: únicos, compuestos y sparse, auditados contra las queries reales
- **Backup & Restore** — mongodump/mongorestore, scripts Python, endpoint REST
- **Transacciones** — ACID multi-documento con audit log atómico
- **Inteligencia Artificial** — Resumen automático de PDFs con LLM local (Ollama)

---

## Instalación y puesta en marcha

### Requisitos previos

- Docker Desktop (corriendo)
- Python 3.11+
- `uv` (gestor de paquetes) — solo para correr scripts desde el host
- Git

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/UTN-BDA-2026/Grupo_ODLR
cd Grupo_ODLR
```

### Paso 2 — Crear el archivo `.env`

```powershell
Copy-Item .env.example .env   # Windows
```
```bash
cp .env.example .env          # Linux/Mac
```

El `.env.example` ya trae la estructura. Como mínimo revisá / generá valores fuertes para:

```env
MONGODB_DB_NAME=pdf_extract_db
SECRET_KEY=<clave-aleatoria-de-al-menos-32-caracteres>

# Credenciales de MongoDB (las usa docker-compose para auth)
MONGO_ROOT_USER=root
MONGO_ROOT_PASSWORD=<password-fuerte-root>
MONGO_APP_USER=appuser
MONGO_APP_PASSWORD=<password-fuerte-app>

OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
```

> La `MONGODB_URL` **no** se setea a mano para Docker: cada servicio (`app`, `migrate`, `seed`) la arma en `docker-compose.yml` con las credenciales de arriba + TLS (`tls=true&tlsCAFile=...`). El valor de `MONGODB_URL` del `.env` solo se usa si corrés la app fuera de Docker.

Generar secretos seguros:

```bash
python -c "import secrets; print(secrets.token_hex(32))"   # SECRET_KEY
# o, para las passwords de Mongo:
openssl rand -hex 24
```

### Paso 3 — Levantar los containers

```bash
docker compose up -d
docker compose ps
```

El arranque es automático y ordenado. Docker Compose levanta, en orden:

```
cert-init    (one-shot)           → genera keyfile + certificados TLS (CA + server)
mongodb      (healthy)             → base de datos con auth (keyFile + root) y TLS requerido
mongo-init   (one-shot)           → inicializa el replica set rs0 y crea el usuario de app
migrate      (one-shot)           → aplica TODAS las migraciones (001 → 014)
seed         (one-shot)           → inserta 500 documentos de ejemplo
app          (Up, :8000)          → la API
frontend     (Up, :8080)          → el dashboard web
ollama       (Up, :11434)         → motor de IA
```

Los servicios `cert-init`, `mongo-init`, `migrate` y `seed` corren una vez y terminan (es normal verlos en estado `Exited (0)`). **Las migraciones se aplican solas** — no hay que correrlas a mano.

> **Importante — primer arranque con seguridad activa:** MongoDB solo crea el usuario root cuando el volumen de datos está **vacío**. Si ya levantaste el stack antes (con un volumen `mongodb_data` sin auth), tenés que recrearlo una vez para que se bootstrapee el root:
>
> ```bash
> docker compose down
> docker volume rm grupo_odlr_mongodb_data
> docker compose up -d --build
> ```
>
> Esto borra los datos, pero el servicio `seed` regenera los 500 documentos y los 4 usuarios demo.

Servicios que quedan corriendo:

```
grupo_odlr-app-1        ...   Up   0.0.0.0:8000->8000/tcp
grupo_odlr-frontend-1   ...   Up   0.0.0.0:8080->80/tcp
grupo_odlr-mongodb-1    ...   Up   0.0.0.0:27017->27017/tcp
grupo_odlr-ollama-1     ...   Up   0.0.0.0:11434->11434/tcp
```

### Paso 4 — Descargar el modelo de IA (solo la primera vez)

```bash
docker exec grupo_odlr-ollama-1 ollama pull llama3.2:3b
```

Esto descarga ~2GB. Solo es necesario hacerlo una vez; el modelo queda guardado en el volumen `ollama_data`.

### Paso 5 — Usuarios (el seed ya crea los demo)

El servicio `seed` crea **4 usuarios demo** junto con los 500 documentos. El único **superusuario** (con acceso al panel de administración) es `admin`:

| Usuario | Password | Rol |
|---|---|---|
| `admin` | `admin123` | **Superusuario** (acceso a `/admin/*` y `admin.html`) |
| `usuario` | `usuario123` | Usuario común |
| `santino` | `santino123` | Usuario común |
| `juani` | `juani123` | Usuario común |

Para crear un usuario nuevo, abrir el Swagger en `http://localhost:8000/api/docs` y ejecutar `POST /api/v1/users/` (queda como usuario común):

```json
{
  "username": "nuevo",
  "email": "nuevo@test.com",
  "password": "nuevo123"
}
```

### Paso 6 — Verificar que todo funciona

```bash
curl http://localhost:8000/health
# Respuesta esperada: {"status": "healthy"}
```

- **API / Swagger:** `http://localhost:8000/api/docs`
- **Frontend (dashboard):** `http://localhost:8080`

---

## Frontend

El servicio `frontend` sirve un dashboard web estático en `http://localhost:8080`:

| Página | Descripción |
|---|---|
| `index.html` | Login |
| `register.html` | Registro de usuario |
| `dashboard.html` | Listado de documentos: buscador por nombre + orden por fecha + resúmenes |
| `upload.html` | Subida de PDFs |
| `backup.html` | Gestión de backups |
| `admin.html` | Panel de administración (solo superusuarios): stats globales, listado de todos los usuarios y documentos |

El buscador y el ordenamiento del dashboard se resuelven **en el backend** (server-side): el frontend envía `?search=` y `?order=` al endpoint `GET /api/v1/pdf/`, y MongoDB filtra y ordena usando sus índices.

El panel `admin.html` está protegido a doble capa: el frontend valida `is_superuser` (y redirige al dashboard si no lo es), pero la autorización real la impone el backend — todos los endpoints `/admin/*` exigen rol de superusuario (403 en caso contrario).

---

## Referencia de endpoints

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| POST | `/api/v1/auth/login` | No | Obtener JWT token (body: `identifier`, `password`) |
| GET | `/api/v1/auth/me` | Sí | Usuario actual |
| POST | `/api/v1/users/` | No | Crear usuario (registro) |
| GET | `/api/v1/users/` | Admin | Listar usuarios |
| GET | `/api/v1/users/{id}` | Admin | Obtener usuario |
| PUT | `/api/v1/users/{id}` | Sí | Actualizar usuario (propio; el superusuario puede editar cualquiera) |
| DELETE | `/api/v1/users/{id}` | Admin | Eliminar usuario |
| POST | `/api/v1/pdf/upload` | Sí | Subir PDF |
| POST | `/api/v1/pdf/upload-audited` | Sí | Subir PDF con transacción ACID |
| GET | `/api/v1/pdf/` | Sí | Listar documentos propios (`?search=`, `?order=`, `?skip=`, `?limit=`) |
| GET | `/api/v1/pdf/{id}` | Sí | Obtener documento |
| PUT | `/api/v1/pdf/{id}` | Sí | Actualizar documento |
| DELETE | `/api/v1/pdf/{id}` | Sí | Eliminar documento |
| POST | `/api/v1/pdf/{id}/summary` | Sí | Generar resumen con IA |
| POST | `/api/v1/admin/backup` | Admin | Triggear backup manual |
| GET | `/api/v1/admin/backups` | Admin | Listar backups disponibles |
| GET | `/api/v1/admin/users` | Admin | Listar todos los usuarios (`?order=`, `?skip=`, `?limit=`) |
| GET | `/api/v1/admin/documents` | Admin | Listar documentos de todos los usuarios (`?owner_id=`, `?search=`, `?order=`) |
| GET | `/api/v1/admin/stats` | Admin | Contadores globales (usuarios y documentos) |
| GET | `/api/v1/health/` | No | Health check (incluye estado de migraciones) |

> **Auth:** *No* = público · *Sí* = requiere JWT · *Admin* = requiere JWT **y** rol de superusuario (`is_superuser`). Un usuario común autenticado recibe `403` en los endpoints marcados como *Admin*.

---

## Conectarse a MongoDB con `mongosh`

Como la base ahora exige **TLS + autenticación**, los comandos `mongosh` de los temas siguientes ya no funcionan "pelados": hay que pasar el CA y las credenciales. La forma más simple es con la connection string (funciona igual en Git Bash y PowerShell):

```bash
docker compose exec mongodb mongosh \
  "mongodb://appuser:<MONGO_APP_PASSWORD>@localhost:27017/pdf_extract_db?authSource=pdf_extract_db&tls=true&tlsCAFile=/etc/mongo-certs/ca.crt" \
  --eval "db.documents.countDocuments()"
```

Reemplazá `<MONGO_APP_PASSWORD>` por el valor de tu `.env`. En los ejemplos de abajo se abrevia esa URI como **`"<MONGO_URI>"`**.

---

## Tema 1: Índices

### Concepto

Un índice en MongoDB es una estructura B-Tree que permite resolver queries sin hacer un *collection scan* (`COLLSCAN`). Sin índice, MongoDB recorre todos los documentos en O(n). Con índice va directo al resultado en O(log n). El costo es que cada índice ocupa espacio y ralentiza las escrituras, así que **solo se indexa lo que las queries realmente usan**.

### Metodología: índices auditados contra el código

Los índices de este proyecto no se crearon "por las dudas": se auditaron cruzando cada índice contra las queries reales de los repositorios (`app/repositories/`). Como resultado se eliminaron índices muertos, duplicados y uno "fantasma" (sobre un campo inexistente), y se agregó el índice compuesto que faltaba para el listado de documentos.

### Índices en uso

| Colección | Índice | Campos | Tipo | Query que lo usa |
|---|---|---|---|---|
| documents | `ux_documents_checksum_owner` | (checksum, owner_id) | Único compuesto | Evitar PDF duplicado por usuario (`find_by_checksum_and_owner`) |
| documents | `ix_documents_owner_created` | (owner_id, created_at ↓) | Compuesto | Listar documentos de un usuario ordenados por fecha (`get_by_owner`) |
| users | `idx_users_email_unique` | email | Único | Login + integridad (`get_by_email`) |
| users | `idx_users_username_unique` | username | Único | Login + integridad (`get_by_username`) |
| users | `idx_users_created_at_desc` | created_at ↓ | Descendente | Listado de usuarios recientes |
| roles | `idx_roles_name_unique` | name | Único | Buscar rol por nombre (`get_by_name`) |
| audit_log | `idx_audit_timestamp_desc` | timestamp ↓ | Descendente | Últimos eventos de auditoría (`get_recent`) |

> El índice estrella es `ix_documents_owner_created`: al ser **compuesto** `{owner_id: 1, created_at: -1}`, resuelve dos cosas con una sola estructura — el filtro por `owner_id` (prefijo) y el ordenamiento por `created_at` (evita un *sort* en memoria). Sigue la regla **ESR** (Equality, Sort, Range).

### Cómo probar

**Verificar los índices de una colección:**

```bash
docker compose exec mongodb mongosh "<MONGO_URI>" --eval "db.documents.getIndexes().forEach(i => print(i.name))"
```

Resultado esperado para `documents`:
```
_id_
ux_documents_checksum_owner
ix_documents_owner_created
```

**Demostrar COLLSCAN vs IXSCAN sobre los índices reales (antes/después):**

```bash
uv run python scripts/demo_indexes_all.py --count 30000
```

> **Pendiente con la seguridad activa:** este script se corre desde el host y asume una conexión plana a `localhost:27017`. Con TLS + auth activos necesita la URI segura (credenciales + `tlsCAFile` apuntando al CA, que vive en el volumen `mongo_certs`), todavía no contemplado.

Inserta documentos de prueba en una colección aparte (`demo_bench`, se borra al final), mide la misma query forzando `COLLSCAN` vs usando el índice, y muestra una tabla:

```
┌────────────────────────────────┬─────────────────────────┬─────────────────────────┬───────────┐
│ Consulta                       │              Sin índice │              Con índice │    Mejora │
│                                │              (COLLSCAN) │                (IXSCAN) │    tiempo │
├────────────────────────────────┼─────────────────────────┼─────────────────────────┼───────────┤
│ documents · owner + fecha *    │   30,001 docs · 66.9 ms │      622 docs · 12.6 ms │        5x │
│ documents · checksum + owner   │   30,001 docs ·  …      │          1 doc  · …     │        …  │
│ users · login por email        │   30,001 docs ·  …      │          1 doc  · …     │        …  │
│ ...                            │                         │                         │           │
└────────────────────────────────┴─────────────────────────┴─────────────────────────┴───────────┘
(*) el índice además elimina el ordenamiento en memoria (stage SORT)
```

La métrica de fondo es `docs` (documentos que MongoDB tuvo que leer): pasa de leer toda la colección a leer solo los necesarios. Para una brecha de tiempo más marcada, subí el volumen con `--count 200000`.

> También existe `scripts/demo_indexes.py`, una demo más simple y genérica del concepto COLLSCAN vs IXSCAN.

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

> **Pendiente con la seguridad activa:** `backup.py` / `restore.py` ejecutan `mongodump` / `mongorestore` y todavía no pasan los flags `--tls --tlsCAFile ... -u ... -p ...`, por lo que fallarán contra la base ahora que exige TLS + auth. Hay que actualizarlos para incluir esas credenciales (pendiente).

```bash
# 1. Verificar que hay documentos
docker compose exec mongodb mongosh "<MONGO_URI>" --eval "db.documents.countDocuments()"

# 2. Hacer el backup
python scripts/backup.py

# 3. Simular pérdida de datos
docker compose exec mongodb mongosh "<MONGO_URI>" --eval "db.documents.deleteMany({})"

# 4. Restaurar
python scripts/restore.py

# 5. Verificar que los datos volvieron
docker compose exec mongodb mongosh "<MONGO_URI>" --eval "db.documents.countDocuments()"
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

MongoDB soporta transacciones multi-documento desde la versión 4.0. Requiere replica set, configurado en este proyecto como `rs0` de un nodo (lo inicializa el servicio `mongo-init`).

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

**Flujo normal:**

1. Autenticarse en Swagger
2. Ejecutar `POST /api/v1/pdf/upload-audited` con un archivo PDF
3. Verificar el documento y el audit log:

```bash
docker compose exec mongodb mongosh "<MONGO_URI>" --eval "db.documents.find({},{filename:1,_id:0})"
docker compose exec mongodb mongosh "<MONGO_URI>" --eval "db.audit_log.find()"
```

**Demostrar rollback (atomicidad):**

Agregar temporalmente en `upload_pdf_with_audit`, después del primer insert:

```python
raise Exception("Error simulado para demostrar rollback")
```

Reiniciar (`docker compose restart app`) y ejecutar `POST /api/v1/pdf/upload-audited` — debe devolver error 500 y el documento NO debe quedar en la DB.

---

## Tema 4: Seguridad

### Capas implementadas

| Capa | Implementación | Protege contra |
|---|---|---|
| Cifrado de conexión a la BD | **TLS `requireTLS` entre app y MongoDB** (CA self-signed, cert con SAN) | Intercepción del tráfico app ↔ base de datos |
| Autenticación de la BD | **MongoDB con auth SCRAM + keyFile del replica set** | Acceso anónimo a la base de datos |
| Menor privilegio | **Usuario `appuser` con roles acotados solo a `pdf_extract_db`** (sin acceso a `admin`) | Daño acotado si se filtra la credencial |
| Autenticación de la API | JWT HS256, expiración 30 min | Acceso no autorizado a los endpoints |
| Autorización (RBAC) | Rol de superusuario + dependencia `require_superuser` en los endpoints `/admin/*` y de gestión de usuarios | Escalada de privilegios / acceso de un usuario común al panel admin |
| Contraseñas | pbkdf2_sha256 con salt | Fuerza bruta offline |
| Aislamiento | Filtro por `owner_id` en cada query | Acceso a documentos de otro usuario |
| Configuración | `.env` nunca commiteado | Exposición de secretos |
| Validación | Pydantic + Motor (consultas como BSON, no concatenación) | Inyección NoSQL |

### Seguridad de la conexión a MongoDB (TLS + auth)

A diferencia de la inyección NoSQL (que se ataca en la capa de aplicación), el cifrado y la autenticación protegen el **canal y el acceso** a la base de datos:

- **TLS** — `mongod` arranca en `--tlsMode requireTLS`: rechaza toda conexión sin cifrar. Los certificados (CA + cert de servidor con SAN para `mongodb`/`localhost`/`127.0.0.1`) los genera el servicio `cert-init` en el volumen `mongo_certs`. Los clientes verifican el servidor contra el CA (`tls=true&tlsCAFile=...`).
- **Autenticación** — el replica set usa un `keyFile` para la autenticación interna entre miembros, y todas las conexiones requieren credenciales SCRAM. La app usa el usuario `appuser`; el `root` solo se usa para administrar.
- **Menor privilegio** — `appuser` tiene `readWrite` + `dbAdmin` **únicamente** sobre `pdf_extract_db`. No puede tocar la base `admin` ni otras bases.

> Las credenciales viven en `.env` (no commiteado) y la `MONGODB_URL` con TLS la inyecta `docker-compose.yml` por servicio. No hizo falta tocar el código Python: el driver Motor/pymongo lee `tlsCAFile` desde la URI.

### Control de acceso por rol (RBAC)

Además de exigir un token válido, algunas operaciones exigen ser **superusuario**. El flag `is_superuser` viaja en el modelo de usuario y en el `UserResponse`, y la dependencia `require_superuser` (en `app/api/v1/endpoints/auth.py`) rechaza con `403` a cualquier usuario común.

- **Panel de administración** (`/admin/*`): `backup`, `backups`, `users`, `documents` y `stats` son solo para superusuarios.
- **Gestión de usuarios**: listar, ver por id y eliminar usuarios requiere superusuario. Actualizar un usuario lo puede hacer el propio dueño de la cuenta **o** un superusuario (un usuario común no puede editar la cuenta de otro).
- El seed marca al usuario **`admin`** como superusuario; el resto de los usuarios demo son comunes. El seed es idempotente: si el usuario ya existía, sincroniza el flag `is_superuser`.

### Cómo probar

**1. Autenticación de la API — sin token da 401, con token da 200:**

```bash
curl http://localhost:8000/api/v1/pdf/
# {"detail": "Not authenticated"}

# Obtener token y usarlo
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier": "admin", "password": "admin123"}'
curl http://localhost:8000/api/v1/pdf/ -H "Authorization: Bearer <TOKEN>"
```

**2. RBAC — un usuario común NO puede entrar al panel admin:**

```bash
# Login como usuario común (no superusuario)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier": "usuario", "password": "usuario123"}'
curl http://localhost:8000/api/v1/admin/stats -H "Authorization: Bearer <TOKEN_USUARIO>"
# {"detail": "Se requieren privilegios de administrador"}   (403)

# Con el token de admin (superusuario) sí responde
curl http://localhost:8000/api/v1/admin/stats -H "Authorization: Bearer <TOKEN_ADMIN>"
# {"total_users": 4, "total_documents": 500}
```

**3. TLS obligatorio — una conexión SIN TLS es rechazada:**

```bash
docker compose exec mongodb mongosh --host 127.0.0.1 --eval 'db.runCommand({ping:1})'
# MongoServerSelectionError: connection ... closed   (requireTLS la rechaza)
```

**4. Auth obligatoria — con TLS pero SIN credenciales, un comando privilegiado falla:**

```bash
docker compose exec mongodb mongosh --tls --tlsCAFile /etc/mongo-certs/ca.crt \
  --eval 'db.getSiblingDB("pdf_extract_db").documents.countDocuments()'
# MongoServerError: Command aggregate requires authentication
```

**5. Menor privilegio — `appuser` no puede leer la base `admin`:**

```bash
docker compose exec mongodb mongosh --tls --tlsCAFile /etc/mongo-certs/ca.crt \
  -u appuser -p <MONGO_APP_PASSWORD> --authenticationDatabase pdf_extract_db \
  --eval 'db.getSiblingDB("admin").system.users.find().toArray()'
# MongoServerError: not authorized on admin to execute command ...
```

> En Git Bash (Windows), anteponé `MSYS_NO_PATHCONV=1` a los comandos con rutas tipo `/etc/...` para evitar que se conviertan a rutas Windows.

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

> **Nota:** la primera inferencia puede tardar 1-2 minutos mientras Ollama carga el modelo en RAM. Las siguientes son más rápidas.

---

## Sistema de migraciones

Las migraciones viven en `migrations/versions/` y se aplican **automáticamente** al levantar el stack (servicio `migrate`). El runner registra cada migración aplicada en la colección `_migration_log`, usa un lock distribuido (`_migration_lock`) y valida checksums, por lo que es seguro re-ejecutarlo: las ya aplicadas se saltean.

| Comando | Acción |
|---|---|
| `python -m migrations status` | Ver estado (aplicadas / pendientes) |
| `python -m migrations migrate` | Aplicar pendientes (`--dry-run` para simular) |
| `python -m migrations rollback` | Revertir la última |

Resumen de lo que hacen las migraciones de índices:

- **001–009** — índices iniciales, campos y la colección `audit_log` (008 es idempotente: tolera que `audit_log` ya exista).
- **010** — reemplaza el único de `checksum` por el compuesto `(checksum, owner_id)`.
- **011** — crea el compuesto `ix_documents_owner_created` (el que faltaba para el listado).
- **012–014** — limpieza: eliminan índices duplicados (users) y muertos (documents, audit_log).

---

## Estructura del proyecto

```
Grupo_ODLR/
├── app/
│   ├── main.py
│   ├── api/v1/
│   │   ├── router.py
│   │   └── endpoints/
│   │       ├── auth.py
│   │       ├── pdf.py            # CRUD + /summary + listado con search/order
│   │       ├── users.py          # gestión de usuarios + RBAC (require_superuser)
│   │       ├── admin.py          # Backup & Restore + panel admin (users/documents/stats)
│   │       └── health.py
│   ├── services/
│   │   ├── document_service.py   # upload_pdf_with_audit (transacciones)
│   │   ├── ollama_service.py     # Integración con Ollama
│   │   ├── pdf_service.py
│   │   └── auth_service.py
│   ├── repositories/
│   │   ├── document_repo.py      # get_by_owner con search ($regex) + sort
│   │   ├── audit_repository.py
│   │   ├── user_repository.py
│   │   └── role_repository.py
│   ├── core/
│   │   ├── config.py             # SECRET_KEY validator + OLLAMA settings
│   │   └── security.py
│   └── db/
│       └── database.py           # start_transaction()
├── migrations/
│   ├── runner.py / registry.py / config.py
│   └── versions/                 # 001 → 014 (índices, audit_log, limpieza)
├── scripts/
│   ├── init_mongo_security.sh    # Genera keyfile + CA + cert TLS (servicio cert-init)
│   ├── mongo-init.sh             # Inicia el replica set + crea appuser (sobre TLS+auth)
│   ├── backup.py
│   ├── restore.py
│   ├── seed_documents.py         # Seed de 500 documentos de ejemplo
│   ├── demo_indexes.py           # Demo COLLSCAN vs IXSCAN (genérica)
│   └── demo_indexes_all.py       # Demo de los índices reales del proyecto
├── frontend/                     # Dashboard web (nginx, :8080)
│   ├── index.html / register.html
│   ├── dashboard.html / upload.html / backup.html
│   └── admin.html                # Panel de administración (solo superusuarios)
├── backups/                      # Backups generados (en .gitignore)
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```
