# Índices de la Base de Datos — PDF Extract API

Documento técnico de **todos** los índices que existen realmente en el código del
proyecto (motor MongoDB `pdf_extract_db`, driver `motor` async). El estado descripto
es el **final tras aplicar las 14 migraciones** (`001` → `014`) en orden.

- **Base de datos:** `pdf_extract_db`
- **Colecciones con índices:** `documents`, `users`, `roles`, `audit_log`, `_migration_log`
- **Índices explícitos vivos:** 9 · **Índices implícitos (`_id`):** 5 · **Eliminados por migraciones de limpieza:** 13

> Los índices implícitos `_id_` los crea MongoDB solo (uno por colección, único). Los índices
> marcados **único** creados con `unique=True` son explícitos, no implícitos.

---

## Tabla resumen

| Colección | Índice | Campos (orden) | Tipo | Propósito |
|---|---|---|---|---|
| `documents` | `_id_` | `_id: 1` | Implícito, único | Acceso por `_id` (implícito de Mongo) |
| `documents` | `ix_documents_owner_created` | `owner_id: 1, created_at: -1` | Compuesto | Listado de documentos de un usuario ordenado por fecha |
| `documents` | `ux_documents_checksum_owner` | `checksum: 1, owner_id: 1` | Compuesto, único | Impide que un mismo usuario suba el mismo PDF dos veces |
| `users` | `_id_` | `_id: 1` | Implícito, único | Acceso por `_id` (implícito de Mongo) |
| `users` | `idx_users_email_unique` | `email: 1` | Simple, único | Login por email / unicidad de email |
| `users` | `idx_users_username_unique` | `username: 1` | Simple, único | Login por username / unicidad de username |
| `users` | `idx_users_created_at_desc` | `created_at: -1` | Simple | Listado admin de usuarios por fecha de alta |
| `roles` | `_id_` | `_id: 1` | Implícito, único | Acceso por `_id` (implícito de Mongo) |
| `roles` | `idx_roles_name_unique` | `name: 1` | Simple, único | Búsqueda de rol por nombre / unicidad |
| `roles` | `idx_roles_created_at_desc` | `created_at: -1` | Simple | Listado de roles por fecha |
| `audit_log` | `_id_` | `_id: 1` | Implícito, único | Acceso por `_id` (implícito de Mongo) |
| `audit_log` | `idx_audit_timestamp_desc` | `timestamp: -1` | Simple | Auditoría reciente (`get_recent`) |
| `_migration_log` | `_id_` | `_id: 1` | Implícito, único | Acceso por `_id` (implícito de Mongo) |
| `_migration_log` | `migration_id_1` | `migration_id: 1` | Simple, único | Evita aplicar dos veces la misma migración |
| `_migration_log` | `applied_at_1` | `applied_at: 1` | Simple | Ordena el historial de migraciones aplicadas |

---

## Detalle por índice

### `documents`

#### 1. `_id_` (implícito)
1. **Colección / índice:** `documents` / `_id_`.
2. **Campos y tipo:** `_id: 1`. Implícito y único — lo crea MongoDB automáticamente al crear la colección.
3. **Para qué sirve:** acceso directo por `_id`, p. ej. `find_by_id()` / `update_summary()` en `document_repo.py`.
4. **Cómo probarlo:**
   ```javascript
   db.documents.getIndexes()
   ```
5. **Resultado esperado:** aparece la entrada `{ "v": 2, "key": { "_id": 1 }, "name": "_id_" }`.

#### 2. `ix_documents_owner_created`
1. **Colección / índice:** `documents` / `ix_documents_owner_created`.
   Definido en `migrations/versions/011_add_owner_created_index.py:29-33`.
2. **Campos y tipo:** `owner_id: 1, created_at: -1`. **Compuesto** (`background=True`). No es único.
3. **Para qué sirve:** acelera el listado de documentos de un usuario. `DocumentRepository.get_by_owner()` y `list_all()` hacen `find({owner_id}).sort({created_at})`; el prefijo `owner_id` cubre el filtro y `created_at` resuelve el sort (asc y desc) sin ordenar en memoria. Aplica a `GET /api/v1/pdf/`.
4. **Cómo probarlo:**
   ```javascript
   db.documents.getIndexes()
   db.documents.find({ owner_id: "REEMPLAZAR_OWNER_ID" })
     .sort({ created_at: -1 })
     .explain("executionStats")
   ```
5. **Resultado esperado:** `winningPlan` con stage **IXSCAN** sobre `ix_documents_owner_created`, sin stage `SORT` en memoria, y `totalDocsExamined` ≈ `nReturned` (no recorre toda la colección).

#### 3. `ux_documents_checksum_owner`
1. **Colección / índice:** `documents` / `ux_documents_checksum_owner`.
   Definido en `migrations/versions/010_checksum_owner_unique.py:26-31`.
2. **Campos y tipo:** `checksum: 1, owner_id: 1`. **Compuesto + único** (`unique=True, background=True`).
3. **Para qué sirve:** impide que un mismo usuario suba dos veces el mismo PDF (mismo `checksum`), pero permite que usuarios distintos suban el mismo archivo. Soporta `find_by_checksum_and_owner()` en el upload (`document_repo.py:149`).
4. **Cómo probarlo:**
   ```javascript
   db.documents.getIndexes()
   db.documents.find({ checksum: "REEMPLAZAR_SHA256", owner_id: "REEMPLAZAR_OWNER_ID" })
     .explain("executionStats")
   ```
5. **Resultado esperado:** en `getIndexes` la entrada figura con `"unique": true`. El explain muestra **IXSCAN** sobre `ux_documents_checksum_owner` con `totalDocsExamined` ≤ 1. Insertar un duplicado (mismo `checksum`+`owner_id`) devuelve error `E11000 duplicate key`.

---

### `users`

#### 4. `idx_users_email_unique`
1. **Colección / índice:** `users` / `idx_users_email_unique`. Definido en `migrations/versions/005_create_users_and_roles.py:34-36`.
2. **Campos y tipo:** `email: 1`. **Simple + único** (`unique=True, background=True`).
3. **Para qué sirve:** login por email y validación de unicidad. `UserRepository.get_by_email()` / `email_exists()` → flujo de autenticación.
4. **Cómo probarlo:**
   ```javascript
   db.users.getIndexes()
   db.users.find({ email: "admin@example.com" }).explain("executionStats")
   ```
5. **Resultado esperado:** `"unique": true` en `getIndexes`; explain con **IXSCAN** sobre `idx_users_email_unique`, `totalDocsExamined` ≤ 1. Insertar email repetido → `E11000`.

#### 5. `idx_users_username_unique`
1. **Colección / índice:** `users` / `idx_users_username_unique`. Definido en `migrations/versions/005_create_users_and_roles.py:37-39`.
2. **Campos y tipo:** `username: 1`. **Simple + único** (`unique=True, background=True`).
3. **Para qué sirve:** login por username y unicidad. `UserRepository.get_by_username()`.
4. **Cómo probarlo:**
   ```javascript
   db.users.getIndexes()
   db.users.find({ username: "admin" }).explain("executionStats")
   ```
5. **Resultado esperado:** `"unique": true`; explain con **IXSCAN** sobre `idx_users_username_unique`, `totalDocsExamined` ≤ 1.

#### 6. `idx_users_created_at_desc`
1. **Colección / índice:** `users` / `idx_users_created_at_desc`. Definido en `migrations/versions/005_create_users_and_roles.py:40-42`.
2. **Campos y tipo:** `created_at: -1`. **Simple** (`background=True`). No único.
3. **Para qué sirve:** listado de usuarios ordenado por fecha de alta en el panel admin. `UserRepository.get_all_sorted()`.
4. **Cómo probarlo:**
   ```javascript
   db.users.getIndexes()
   db.users.find({}).sort({ created_at: -1 }).explain("executionStats")
   ```
5. **Resultado esperado:** explain **sin** stage `SORT` en memoria; usa **IXSCAN** sobre `idx_users_created_at_desc` para devolver ya ordenado.

---

### `roles`

#### 7. `idx_roles_name_unique`
1. **Colección / índice:** `roles` / `idx_roles_name_unique`. Definido en `migrations/versions/005_create_users_and_roles.py:44-46`.
2. **Campos y tipo:** `name: 1`. **Simple + único** (`unique=True, background=True`).
3. **Para qué sirve:** búsqueda de rol por nombre y evitar roles duplicados (`user`, `admin`). `RoleRepository.get_by_name()`.
4. **Cómo probarlo:**
   ```javascript
   db.roles.getIndexes()
   db.roles.find({ name: "admin" }).explain("executionStats")
   ```
5. **Resultado esperado:** `"unique": true`; explain con **IXSCAN** sobre `idx_roles_name_unique`, `totalDocsExamined` ≤ 1.

#### 8. `idx_roles_created_at_desc`
1. **Colección / índice:** `roles` / `idx_roles_created_at_desc`. Definido en `migrations/versions/005_create_users_and_roles.py:47-49`.
2. **Campos y tipo:** `created_at: -1`. **Simple** (`background=True`). No único.
3. **Para qué sirve:** listado de roles ordenado por fecha.
4. **Cómo probarlo:**
   ```javascript
   db.roles.getIndexes()
   db.roles.find({}).sort({ created_at: -1 }).explain("executionStats")
   ```
5. **Resultado esperado:** explain sin `SORT` en memoria, con **IXSCAN** sobre `idx_roles_created_at_desc`.

---

### `audit_log`

#### 9. `idx_audit_timestamp_desc`
1. **Colección / índice:** `audit_log` / `idx_audit_timestamp_desc`. Definido en `migrations/versions/008_add_audit_log.py:39-42`.
2. **Campos y tipo:** `timestamp: -1`. **Simple** (sin `background`, se crea en foreground). No único.
3. **Para qué sirve:** traer los registros de auditoría más recientes. `AuditRepository.get_recent()` hace `find().sort({timestamp: -1})`.
4. **Cómo probarlo:**
   ```javascript
   db.audit_log.getIndexes()
   db.audit_log.find({}).sort({ timestamp: -1 }).limit(20).explain("executionStats")
   ```
5. **Resultado esperado:** explain sin `SORT` en memoria, con **IXSCAN** sobre `idx_audit_timestamp_desc`; `totalDocsExamined` acotado por el `limit`.

> Los índices `idx_audit_document_id` y `idx_audit_action` **existieron** (migración 008) pero
> fueron eliminados por la migración `014_drop_dead_audit_indexes` (ninguna query filtraba por esos campos).

---

### `_migration_log` (colección interna del sistema de migraciones)

#### 10. `migration_id_1`
1. **Colección / índice:** `_migration_log` / `migration_id_1` (nombre autogenerado). Definido en `migrations/registry.py:38-40`.
2. **Campos y tipo:** `migration_id: 1`. **Simple + único** (`unique=True, background=True`).
3. **Para qué sirve:** garantiza que cada migración se registre una sola vez; impide reaplicar la misma migración.
4. **Cómo probarlo:**
   ```javascript
   db._migration_log.getIndexes()
   db._migration_log.find({ migration_id: "011_add_owner_created_index" }).explain("executionStats")
   ```
5. **Resultado esperado:** `"unique": true`; explain con **IXSCAN** sobre `migration_id_1`, `totalDocsExamined` ≤ 1.

#### 11. `applied_at_1`
1. **Colección / índice:** `_migration_log` / `applied_at_1` (nombre autogenerado). Definido en `migrations/registry.py:41-42`.
2. **Campos y tipo:** `applied_at: 1`. **Simple** (`background=True`). No único.
3. **Para qué sirve:** ordena el historial de migraciones aplicadas. `MigrationRegistry.get_applied_migrations()` hace `find().sort({applied_at: 1})`.
4. **Cómo probarlo:**
   ```javascript
   db._migration_log.getIndexes()
   db._migration_log.find({}).sort({ applied_at: 1 }).explain("executionStats")
   ```
5. **Resultado esperado:** explain sin `SORT` en memoria, con **IXSCAN** sobre `applied_at_1`.

---

## Índices eliminados (contexto)

Estos índices **ya no existen** tras las migraciones de limpieza; se listan para explicar por qué no
aparecen en `getIndexes()`:

- **`users`** (migración `012_drop_duplicate_user_indexes`): `ux_users_email`, `ux_users_username`,
  `ix_users_created_at_desc` — duplicados de los `idx_users_*` de la migración 005.
- **`documents`** (migración `013_drop_dead_document_indexes`): `idx_filename`, `idx_created_at_desc`,
  `idx_status_created_at`, `idx_user_id`, `idx_organization_id`, `idx_user_created`,
  `idx_docs_summary_exists`, `ux_documents_checksum` — sin uso real o reemplazados por los compuestos 010/011.
- **`audit_log`** (migración `014_drop_dead_audit_indexes`): `idx_audit_document_id`, `idx_audit_action`.

---

## Conexión a la base por `mongosh` (entorno Docker)

MongoDB corre con **TLS obligatorio** (`requireTLS`), replica set `rs0` y autenticación. La forma más
simple es entrar al contenedor `mongodb` (ya tiene el CA montado en `/etc/mongo-certs/ca.crt`) y usar el
usuario de aplicación (`MONGO_APP_USER` / `MONGO_APP_PASSWORD` de tu `.env`, `authSource=pdf_extract_db`).

```bash
# 1) Abrir mongosh dentro del contenedor mongodb, sobre TLS, autenticado como app user
docker compose exec mongodb mongosh \
  --tls --tlsCAFile /etc/mongo-certs/ca.crt --tlsAllowInvalidCertificates \
  -u appuser -p 'TU_MONGO_APP_PASSWORD' \
  --authenticationDatabase pdf_extract_db \
  pdf_extract_db
```

Ya dentro del shell:

```javascript
// Confirmar que estás en la base correcta
db.getName()            // -> "pdf_extract_db"
show collections        // documents, users, roles, audit_log, _migration_log, _migration_lock

// Listar índices de cada colección
db.documents.getIndexes()
db.users.getIndexes()
db.roles.getIndexes()
db.audit_log.getIndexes()
db._migration_log.getIndexes()
```

Alternativa como **root** (si necesitás permisos administrativos):

```bash
docker compose exec mongodb mongosh \
  --tls --tlsCAFile /etc/mongo-certs/ca.crt --tlsAllowInvalidCertificates \
  -u root -p 'TU_MONGO_ROOT_PASSWORD' \
  --authenticationDatabase admin \
  pdf_extract_db
```

> **Notas**
> - Reemplazá `TU_MONGO_APP_PASSWORD` / `TU_MONGO_ROOT_PASSWORD` por los valores reales de tu `.env`
>   (`MONGO_APP_PASSWORD`, `MONGO_ROOT_PASSWORD`).
> - `--tlsAllowInvalidCertificates` evita fallos de verificación de hostname al conectar a `localhost`
>   dentro del contenedor (es el mismo criterio que usa el healthcheck del `docker-compose.yml`).
> - En los `explain`, reemplazá los `REEMPLAZAR_*` por valores reales (podés tomar un `owner_id` /
>   `checksum` de un documento existente con `db.documents.findOne()`).
> - Para forzar la comparación COLLSCAN vs IXSCAN sobre datos de prueba, el repo incluye
>   `scripts/demo_indexes_all.py` (mide `totalDocsExamined` y la eliminación del `SORT` en memoria).
