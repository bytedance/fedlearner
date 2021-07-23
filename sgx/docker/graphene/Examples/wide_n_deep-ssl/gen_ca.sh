      
#!/bin/bash
set -x

rm -rf xxx demoCA pa pb pa_w pb_w

function root_ca() {
    mkdir -p ./demoCA/{private,newcerts}
    touch ./demoCA/index.txt
    echo 01 > ./demoCA/serial
    openssl genrsa -out ./demoCA/private/cakey.pem 2048
    openssl req -new -x509 -days 365 -key ./demoCA/private/cakey.pem -out ./demoCA/cacert.pem  -subj "/C=CN/ST=mykey/L=mykey/O=mykey/OU=mykey/CN=server.com"
}

function client_ca() {
    mkdir $1
    openssl genrsa -out $1/userkey.pem
    openssl req -new -key $1/userkey.pem -out $1/userreq.pem  -subj "/C=CN/ST=mykey/L=mykey/O=mykey/OU=mykey/CN=$1.com"
    openssl ca -policy policy_anything -days 3652  -keyfile ./demoCA/private/cakey.pem -cert ./demoCA/cacert.pem  -in $1/userreq.pem -out $1/usercert.pem
}

root_ca
echo "Sign client\n"
client_ca pa
client_ca pa_w
client_ca pb
client_ca pb_w

mkdir xxx
mv demoCA pa pb pa_w pb_w xxx
