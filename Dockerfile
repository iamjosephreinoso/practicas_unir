# Usar una imagen base
FROM ubuntu:22.04

# Instalar herramientas necesarias
RUN apt-get update && apt-get install -y sysstat net-tools

# Copiar el script al contenedor
COPY monitor.sh /usr/local/bin/monitor.sh

# Dar permisos de ejecución
RUN chmod +x /usr/local/bin/monitor.sh

# Comando por defecto al iniciar el contenedor
CMD ["bash", "/usr/local/bin/monitor.sh"]

