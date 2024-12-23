# practicas_unir

#1. Primero se contruye la imagen de Docker llamada monitor-container
docker build -t monitor-container .

#2. Ejecuta el contenedor nuevamente y verifica que funcione correctamente
docker run -d --name monitor-container monitor-container
docker logs monitor-container

#3. Ahora para el cAdvisor se ejecuta la imagen en un contenedor de Docker
docker run --detach --volume=/:/rootfs:ro --volume=/var/run:/var/run:ro --volume=/sys:/sys:ro --volume=/var/lib/docker/:/var/lib/docker:ro --publish=8080:8080 --name=cadvisor gcr.io/cadvisor/cadvisor:latest

#4. Una vez iniciado puede verificar que el contenedor funcione en la dirección
http://localhost:8080 o http://localhost:8080/metrics

#5. Ahora que tenemos funcionando las imagenes en docker, vamos y ejecutamos el archivo recolectar.py
#En este archivo monitorea cada 30 segundo en tiempo real los contenemos de docker y como se encuentrar
#Para eso utilizamos el siguiente comando
python recolectar.py

#Este archivo .py trabaja con el archivo trained_model.pkl el cual guarda ya el modelo entrenado anterior mente para las predicciones de los recursos del contenedor