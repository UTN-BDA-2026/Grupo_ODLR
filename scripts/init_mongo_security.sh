#!/bin/sh
# Genera el material de seguridad de MongoDB en un volumen compartido:
#   - keyfile  : autenticacion interna entre miembros del replica set (cluster auth)
#   - ca.crt   : autoridad certificadora (la confian los clientes)
#   - server.pem : clave + certificado del servidor para TLS (firmado por el CA)
#
# Se ejecuta una sola vez (idempotente): si los archivos ya existen, no regenera.
# Corre como root en alpine y asigna owner 999:999 (usuario mongodb de la imagen oficial)
# para que mongod pueda leer el keyfile y la clave privada con permisos restrictivos.
set -e

CERT_DIR=/certs
MONGO_UID=999
MONGO_GID=999

if [ -f "$CERT_DIR/ca.crt" ] && [ -f "$CERT_DIR/server.pem" ] && [ -f "$CERT_DIR/keyfile" ]; then
  echo "[cert-init] El material de seguridad ya existe, no se regenera."
  exit 0
fi

echo "[cert-init] Instalando openssl..."
apk add --no-cache openssl >/dev/null

echo "[cert-init] Generando keyfile para autenticacion interna del replica set..."
openssl rand -base64 756 > "$CERT_DIR/keyfile"

echo "[cert-init] Generando Autoridad Certificadora (CA)..."
openssl genrsa -out "$CERT_DIR/ca.key" 4096
openssl req -new -x509 -days 3650 -key "$CERT_DIR/ca.key" \
  -out "$CERT_DIR/ca.crt" -subj "/CN=ODLR-Root-CA"

echo "[cert-init] Generando certificado del servidor (con SAN)..."
cat > "$CERT_DIR/san.cnf" <<EOF
[req]
distinguished_name = dn
req_extensions = v3_req
prompt = no
[dn]
CN = mongodb
[v3_req]
subjectAltName = @alt
[alt]
DNS.1 = mongodb
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF

openssl genrsa -out "$CERT_DIR/server.key" 4096
openssl req -new -key "$CERT_DIR/server.key" -out "$CERT_DIR/server.csr" \
  -config "$CERT_DIR/san.cnf"
openssl x509 -req -in "$CERT_DIR/server.csr" -CA "$CERT_DIR/ca.crt" \
  -CAkey "$CERT_DIR/ca.key" -CAcreateserial -days 3650 \
  -out "$CERT_DIR/server.crt" -extensions v3_req -extfile "$CERT_DIR/san.cnf"

# MongoDB espera clave + certificado concatenados en el tlsCertificateKeyFile
cat "$CERT_DIR/server.key" "$CERT_DIR/server.crt" > "$CERT_DIR/server.pem"

echo "[cert-init] Ajustando permisos y propietario..."
# Material privado: solo lo lee el usuario mongodb (no group/other) -> mongod lo exige
chmod 400 "$CERT_DIR/keyfile" "$CERT_DIR/server.pem" "$CERT_DIR/server.key" "$CERT_DIR/ca.key"
# El CA es publico (lo leen los contenedores cliente que corren como root)
chmod 444 "$CERT_DIR/ca.crt"
chown $MONGO_UID:$MONGO_GID "$CERT_DIR"/* || true

echo "[cert-init] Listo. Material de seguridad generado en $CERT_DIR"
