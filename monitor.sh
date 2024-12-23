#!/bin/bash

while true
do
    echo 
    echo "Métricas de CPU:"
    mpstat

    echo "Uso de memoria:"
    free -m

    echo "Red:"
    ifconfig

    echo "Almacenamiento:"
    df -h

    echo 
    sleep 30
done

