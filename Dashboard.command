#!/bin/bash
# Moliya Dashboard — ikki marta bosing, dashboard ochiladi
cd "$(dirname "$0")"

# Port allaqachon ishlayotganmi? Ishlayotgan bo'lsa — shunchaki brauzer ochamiz
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:5050/; then
    open "http://127.0.0.1:5050/"
    exit 0
fi

# Venvdagi python bilan ishga tushirib, brauzer ochamiz
nohup ./venv/bin/python dashboard.py > /tmp/dashboard.log 2>&1 &
sleep 3
open "http://127.0.0.1:5050/"
