#!/bin/sh

dir="$1"
if [ -z "$dir" ]; then
    dir=~/.local/share/bard/certs
fi
KEY="$dir/server.key"
CSR="$dir/server.csr"
CRT="$dir/server.crt"
PEM="$dir/cert.pem"
HOSTNAME=`hostname`

echo "Certificate files for host $HOSTNAME will be written to $dir"
echo "Press ENTER to continue or Ctrl-C to cancel"
read

mkdir -p "$dir"
USER_REAL_NAME=`getent passwd "$UID" | cut -d : -f 5 | cut -d , -f 1`
openssl genrsa -out "$KEY" 2048
openssl rsa -in "$KEY" -out "$KEY"
openssl req -sha256 -new -key "$KEY" -out "$CSR" -subj "/CN=$HOST/O=$USER_REAL_NAME/OU=$USER_REAL_NAME"
openssl x509 -req -sha256 -days 365 -in "$CSR" -signkey "$KEY" -out "$CRT"
cat "$CRT" "$KEY" > "$PEM"

if [[ "${dir:0:1}" == / || "${dir:0:2}" == ~[/a-z] ]]; then
    fullkey="$KEY"
    fullpem="$PEM"
else
    fullkey="$PWD/$KEY"
    fullpem="$PWD/$KEY"
fi


echo "You can set the following variables in the bard config file to use the generated keys:"
echo "\"hostname\" : \"$HOSTNAME\","
echo "\"use_ssl\" : true,"
echo "\"ssl_certificate_key_file\"  : \"$fullkey\","
echo "\"ssl_certificate_chain_file\": \"$fullpem\","
