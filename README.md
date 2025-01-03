# practicas_unir

# Monitorización de Recursos de Contenedores en Docker

## Pasos de Configuración

### 1. Construcción de la Imagen Docker para el Monitor de Contenedores

Cree una imagen Docker para monitorear contenedores (para que el contenedor funcione el archivo `monitor.sh` debe estar en la misma raíz que el dockerfile):

```bash
docker build -t monitor-container .
```

### 2. Ejecución del Contenedor de Monitorización

Ejecute el contenedor basado en la imagen creada y verifique que funcione correctamente:

```bash
docker run -d --name monitor-container monitor-container
docker logs monitor-container
```

### 3. Configuración de cAdvisor para la Recolección de Métricas

Ejecute el contenedor de cAdvisor para monitorear las métricas de los contenedores Docker:

```bash
docker run --detach --volume=/:/rootfs:ro --volume=/var/run:/var/run:ro --volume=/sys:/sys:ro --volume=/var/lib/docker/:/var/lib/docker:ro --publish=8080:8080 --name=cadvisor gcr.io/cadvisor/cadvisor:latest
```

### 4. Verificación de cAdvisor

Una vez iniciado, puede verificar que cAdvisor está funcionando accediendo a las siguientes URL en su navegador:

- Interfaz gráfica: [http://localhost:8080](http://localhost:8080)
- Métricas en formato texto: [http://localhost:8080/metrics](http://localhost:8080/metrics)

### 5. Ejecución del Script de Monitoreo y Predicción

Utilice el script `recolectar.py` para monitorear los contenedores en tiempo real cada 30 segundos y realizar predicciones basadas en un modelo preentrenado:

```bash
python recolectar.py
```

El script:

- Lee las métricas de cAdvisor.
- Procesa las métricas para obtener los valores relevantes de cada contenedor.
- Usa el archivo `trained_model.pkl` para realizar predicciones sobre el estado de los recursos del contenedor.

---

## Archivo Trained Model

El archivo `trained_model.pkl` contiene el modelo de aprendizaje automático previamente entrenado para predecir el estado de los contenedores. Este archivo debe estar en la misma ubicación que el script `recolectar.py` para que funcione correctamente.

---

# Interfaz Gráfica para Monitoreo

##  Monitor de Contenedores Docker con Flask

### 1. Clonar el repositorio

Clona el repositorio desde GitHub en tu máquina local:

```bash
git clone https://github.com/iamjosephreinoso/practicas_unir.git
cd monitor_contenedores
```

### 2. Construir la imagen Docker

```bash
docker build -t monitor-contenedores .
```

### 2. Ejecutar el contenedor Docker

```bash
docker run -p 5000:5000 monitor-contenedores
```

### 3. Acceder a la aplicación

```bash
http://localhost:5000
```
