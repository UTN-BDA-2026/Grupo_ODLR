# Base de Datos Avanzada

**Profesores:** Ricardo Sergio Arroyo · Jorge Pérez Herrera©

**UTN — Facultad Regional San Rafael**

---

# Seguridad en Conexiones a BD

---

## Transacciones en Base de datos

**Veremos**

1. Introducción
2. Inyección SQL
3. Consultas Parametrizadas
4. Cifrado de Conexiones (SSL/TLS)
5. Gestión de Credenciales
6. Casos Prácticos
7. Mejores prácticas

---

## Introducción

La seguridad en las conexiones a bases de datos es fundamental para proteger la información sensible de nuestras aplicaciones. Los vectores de ataque más comunes incluyen la inyección SQL, interceptación de comunicaciones y compromiso de credenciales.

---

## Principales amenazas

**Inyección SQL**
Inserción de código malicioso en consultas para manipular la base de datos.

**Interceptación de datos**
Captura de información en tránsito entre la app y la base de datos.

**Credenciales comprometidas**
Acceso no autorizado por filtración de usuarios y contraseñas.

**Escalación de privilegios**
Abuso de permisos excesivos para acceder a datos sensibles.

---

## Inyección SQL

La inyección SQL es una técnica donde un atacante inserta código SQL malicioso en campos de entrada para manipular consultas a la base de datos.

### ¿Cómo funciona?

1. Usuario ingresa datos
2. App arma la consulta
3. Atacante inyecta SQL
4. BD ejecuta código malicioso

**Código vulnerable:**

```java
String sql = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'";
```

**Input del atacante:**

```
username: admin'--
password: cualquier_cosa
-- Resultado: omite la password
```

**Resultado:**

```sql
SELECT * FROM users WHERE username = 'admin'--' AND password = 'cualquier_cosa'
-- El -- comenta todo lo que sigue → la contraseña nunca se verifica
```

**Impacto:** robo de credenciales · acceso no autorizado · eliminación de datos

---

## Tipos de inyección SQL

### Clásica

El resultado del ataque es visible directamente en la pantalla.

```sql
-- Entrada maliciosa: ' OR '1'='1
SELECT * FROM products WHERE category = '' OR '1'='1'
-- Retorna TODOS los productos
```

### UNION

Se agrega una segunda consulta para extraer datos de otras tablas.

```sql
-- Entrada maliciosa: ' UNION SELECT username, password FROM users--
SELECT name, price
FROM products WHERE id = '1'
UNION SELECT username, password FROM users--'
-- Expone datos de usuarios
```

### Blind

No hay resultado visible: el atacante deduce info por comportamiento (tiempos, errores).

```sql
-- El atacante no ve resultados directos, pero puede inferir información
SELECT * FROM users WHERE id = '1' AND
(SELECT LENGTH(password) FROM users WHERE username='admin') > 5--'
```

---

## Impacto de un ataque exitoso

- Robo de credenciales
- Acceso no autorizado a la base de datos
- Alteración de la base de datos
- Eliminación de información

---

## Consultas Parametrizadas (prepared statements)

**La defensa principal contra la inyección SQL**

### ¿Cómo funciona?

1. La app envía el template SQL con marcadores de posición (`?`, `%s`, `@param`)
2. La BD parsea y compila el template una sola vez
3. La app envía los datos por separado
4. La BD nunca los interpreta como código SQL

### Ventajas adicionales

- Mejor rendimiento: parseo solo una vez
- Menos tráfico: solo viajan los parámetros
- Validación de tipos automática
- Separación clara entre código y datos

**Ejemplo Python (psycopg2):**

```python
# Vulnerable
cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
```

**Versión segura:**

```python
# Seguro
cursor.execute(
    "SELECT * FROM users WHERE username = %s", (username,))
```

---

## Consultas Parametrizadas — Implementación por lenguaje

**Java (JDBC)**

```java
String sql = "SELECT * FROM users WHERE username = ?";
PreparedStatement pstmt = conn.prepareStatement(sql);
pstmt.setString(1, username);
```

**C# (.NET)**

```csharp
string sql = "SELECT * FROM users WHERE username = @username";
SqlCommand cmd = new SqlCommand(sql, connection);
cmd.Parameters.AddWithValue("@username", username);
```

**PHP (PDO)**

```php
$sql = "SELECT * FROM users WHERE username = ?";
$stmt = $pdo->prepare($sql);
$stmt->execute([$username]);
```

**Python (psycopg2)**

```python
cursor.execute(
    "SELECT * FROM users WHERE username = %s",
    (username,))
```

- La BD recibe el template y los datos como cosas distintas.
- Nunca interpreta los datos como código SQL. Si el usuario escribe `admin'--`, llega como un string literal, no como instrucción.

---

## Consultas Parametrizadas — En síntesis

1. **Separación clara** entre código SQL y datos
2. **Reutilización** de consultas compiladas (mejor rendimiento)
3. **Prevención automática** de inyección SQL
4. **Validación de tipos** automática

---

## Cifrado de Conexiones (SSL/TLS)

El cifrado protege los datos en tránsito entre la aplicación y la base de datos.

Muy distinto a la inyección SQL que ataca las consultas.

---

## Cifrado de Conexiones — Funcionamiento

**Protege el canal de comunicación entre la app y la base de datos**

Flujo entre **Cliente** y **Servidor BD**:

1. Client Hello
2. Server Hello + Certificado
3. Verificación certificado
4. Intercambio de claves
5. Confirmación

→ **Conexión cifrada establecida**

6. Datos cifrados
7. Respuestas cifradas

---

## Cifrado de Conexiones — Configuración por Motor de BD

### MySQL

```ini
-- Configuración del servidor (my.cnf)
[mysqld]
ssl-ca=/path/to/ca-cert.pem
ssl-cert=/path/to/server-cert.pem
ssl-key=/path/to/server-key.pem
require_secure_transport=ON
```

```java
// Conexión desde aplicación Java
String url = "jdbc:mysql://localhost:3306/mydb?useSSL=true&requireSSL=true&verifyServerCertificate=true";
```

### PostgreSQL

```ini
# postgresql.conf
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
ssl_ca_file = 'ca.crt'
```

```python
# Conexión desde Python
conn = psycopg2.connect(
    host="localhost",
    database="mydb",
    user="user",
    password="password",
    sslmode="require")
```

---

## Niveles de Seguridad SSL

- **Disabled:** Sin cifrado
- **Preferred:** Cifrado si está disponible
- **Required:** Cifrado obligatorio
- **Verify-CA:** Verificar certificado de la autoridad
- **Verify-Full:** Verificación completa del certificado

---

## Gestión de Credenciales

La gestión segura de credenciales es esencial para prevenir accesos no autorizados.

### Variables de Entorno (Mínimo aceptable)

Las credenciales viven fuera del código en `.env` (sin commitear). La app las lee en tiempo de ejecución.

```bash
# .env (no commitear a repositorio)
DB_HOST=localhost
DB_USER=myuser
DB_PASSWORD=securepassword123
DB_NAME=myapp
```

```java
// Java - Lectura de variables de entorno
String dbPassword = System.getenv("DB_PASSWORD");
if (dbPassword == null) {
    throw new RuntimeException("DB_PASSWORD environment variable not set");
}
```

---

## Gestión de Credenciales — Gestores de Secretos (Producción)

> ¿Dónde guarda una contraseña de base de datos si no puede estar en el código, ni en un archivo que se commitea, ni en texto plano en el servidor?

HashiCorp Vault (open source - Kubernetes) / AWS Secrets Manager. La app pide el secreto al gestor. Nunca toca disco. Permite rotación automática.

### HashiCorp Vault

```bash
# Almacenar secreto
vault kv put secret/myapp/db password=securepassword123

# Leer secreto desde aplicación
vault kv get -field=password secret/myapp/db
```

### AWS Secrets Manager

```python
import boto3
import json

def get_secret():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='prod/myapp/db')
    secret = json.loads(response['SecretString'])
    return secret['password']
```

---

## Gestión de Credenciales — Menor Privilegio (Siempre)

El usuario de BD solo tiene los permisos que necesita. Si la credencial se filtra, el daño es acotado.

```sql
-- ❌ Usuario con privilegios excesivos
GRANT ALL PRIVILEGES ON *.* TO 'appuser'@'%';

-- ✅ Usuario con privilegios específicos
GRANT SELECT, INSERT, UPDATE ON myapp.users TO 'appuser'@'localhost';
GRANT SELECT, INSERT ON myapp.logs TO 'appuser'@'localhost';
```

---

## Casos prácticos

### Caso 1: Sistema de Login Vulnerable

**Escenario:** Sistema de autenticación con inyección SQL

```java
// Código vulnerable
public boolean authenticateUser(String username, String password) {
    String sql = "SELECT COUNT(*) FROM users WHERE username = '" +
        username + "' AND password = '" + password + "'";
    // ... ejecución vulnerable
}
```

**Ataque:**

- Username: `admin'--`
- Password: `cualquier_cosa`

```sql
SELECT COUNT(*) FROM users WHERE username = 'admin'--' AND password = 'cualquier_cosa'
```

---

### Caso 1 — Solución

```java
public boolean authenticateUser(String username, String password) {
    String sql = "SELECT COUNT(*) FROM users WHERE username = ? AND password_hash = ?";
    PreparedStatement pstmt = connection.prepareStatement(sql);
    pstmt.setString(1, username);
    pstmt.setString(2, hashPassword(password)); // Hash seguro
    ResultSet rs = pstmt.executeQuery();
    // ... verificación segura
}
```

---

### Caso 2: Aplicación de E-commerce

**Escenario:** Búsqueda de productos vulnerable

```php
// Código vulnerable
$search = $_GET['search'];
$sql = "SELECT * FROM products WHERE name LIKE '%$search%'";
$result = mysqli_query($connection, $sql);
```

**Ataque:**

El atacante necesita "cerrar" el LIKE y agregar su consulta. Escribe en el campo de búsqueda:

```
' UNION SELECT id, username, password FROM users --
```

```
GET /search?search=' UNION SELECT id, username, password FROM users --
```

---

### Caso 2 — Solución

```php
$search = $_GET['search'];
$sql = "SELECT * FROM products WHERE name LIKE ?";
$stmt = $connection->prepare($sql);
$searchParam = "%$search%";
$stmt->bind_param("s", $searchParam);
$stmt->execute();
$result = $stmt->get_result();
```

---

## Mejores Prácticas

### Desarrollo

- Consultas parametrizadas en todas las queries
- Validar y sanitizar entradas del usuario
- Hashing seguro de contraseñas (bcrypt / PBKDF2)
- Nunca almacenar credenciales en código fuente

### Base de Datos

- Habilitar cifrado SSL/TLS
- Usuarios con privilegios mínimos
- Auditoría de accesos habilitada
- Firewall de base de datos configurado

### Infraestructura

- BD en red separada del acceso público
- Backups cifrados
- Rotación periódica de credenciales
- Software actualizado

---

## La seguridad no es una característica, es una responsabilidad

- Nunca concatenar strings para armar SQL
- Cifrar siempre el canal de comunicación
- Las credenciales no van en el código
- Menos privilegios = menos superficie de ataque

---

## Herramientas Recomendadas

### Análisis de Código

- **SonarQube:** Detección de vulnerabilidades de seguridad
- **OWASP ZAP:** Testing de seguridad en aplicaciones web
- **SQLMap:** Testing específico de inyección SQL

### Gestión de Secretos

- **HashiCorp Vault:** Gestión centralizada de secretos
- **AWS Secrets Manager:** Gestión de secretos en la nube
- **Azure Key Vault:** Alternativa de Microsoft
- **Docker Secrets:** Para entornos containerizados

### Monitoreo

- **Fail2Ban:** Protección contra ataques de fuerza bruta
- **OSSEC:** Sistema de detección de intrusiones
- **Elasticsearch + Kibana:** Análisis de logs de seguridad

---

## Recursos Adicionales

- OWASP Top 10
- SQL Injection Prevention Cheat Sheet
- Database Security Checklist
- TLS Configuration Guide

---

# ¡Gracias!

**Base de Datos Avanzada — UTN, Facultad Regional San Rafael**
