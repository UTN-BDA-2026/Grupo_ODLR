#!/bin/bash
# Inicializa el replica set y crea el usuario de aplicacion con privilegios minimos.
# Se conecta SIEMPRE sobre TLS (verificando el CA) y autenticado como root.
set -e

HOST="mongodb:27017"
CA="/etc/mongo-certs/ca.crt"

ROOT_ARGS="--host $HOST --tls --tlsCAFile $CA \
  -u $MONGO_INITDB_ROOT_USERNAME -p $MONGO_INITDB_ROOT_PASSWORD \
  --authenticationDatabase admin --quiet"

echo "[mongo-init] Inicializando replica set rs0 (si hace falta)..."
mongosh $ROOT_ARGS --eval '
  try {
    rs.status();
    print("Replica set ya inicializado");
  } catch (e) {
    rs.initiate({ _id: "rs0", members: [{ _id: 0, host: "mongodb:27017" }] });
    print("Replica set rs0 inicializado");
  }
'

echo "[mongo-init] Esperando a que el nodo sea PRIMARY..."
until mongosh $ROOT_ARGS --eval 'db.hello().isWritablePrimary' | grep -q true; do
  echo "[mongo-init] todavia no es primary, reintentando..."
  sleep 2
done

echo "[mongo-init] Creando usuario de aplicacion (idempotente)..."
mongosh $ROOT_ARGS --eval '
  const appDb = db.getSiblingDB("pdf_extract_db");
  const user = "'"$MONGO_APP_USER"'";
  const pwd  = "'"$MONGO_APP_PASSWORD"'";
  if (appDb.getUser(user)) {
    print("El usuario de aplicacion ya existe");
  } else {
    appDb.createUser({
      user: user,
      pwd: pwd,
      roles: [
        { role: "readWrite", db: "pdf_extract_db" },
        { role: "dbAdmin",   db: "pdf_extract_db" }
      ]
    });
    print("Usuario de aplicacion creado con privilegios acotados a pdf_extract_db");
  }
'

echo "[mongo-init] Inicializacion completa."
