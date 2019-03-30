#!/bin/sh
dir=~/.local/share/bard/certs
mkdir -p "$dir"
KEY="$dir/server.key"
CSR="$dir/server.csr"
CRT="$dir/server.crt"
PEM="$dir/cert.pem"
HOSTNAME=`hostname`
USER_REAL_NAME=`getent passwd "$UID" | cut -d : -f 5 | cut -d , -f 1`
openssl genrsa -out "$KEY" 2048
openssl rsa -in "$KEY" -out "$KEY"
openssl req -sha256 -new -key "$KEY" -out "$CSR" -subj "/CN=$HOST/O=$USER_REAL_NAME/OU=$USER_REAL_NAME"
openssl x509 -req -sha256 -days 365 -in "$CSR" -signkey "$KEY" -out "$CRT"
cat "$CRT" "$KEY" > "$PEM"
