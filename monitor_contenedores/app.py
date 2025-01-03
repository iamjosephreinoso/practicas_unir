from flask import Flask, render_template, jsonify, request, send_from_directory
import requests
import time
import re
import pickle
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sklearn.preprocessing import MinMaxScaler
import os
from datetime import datetime
app = Flask(__name__)

previous_network_metrics = {}
contenedores = {}

def get_cadvisor_metrics():
    url = 'http://localhost:8080/metrics'  # Cambia el puerto si es necesario
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print("Error al obtener las métricas de cAdvisor.")
        return None


def process_metrics(metrics):
    data = []
    lines = metrics.splitlines()
    timestamp = time.time()

    container_data = {}

    for line in lines:
        if not line.strip() or line.startswith('#'):
            continue

        match = re.match(r'^([^ ]+){([^}]*)} ([0-9.e+-]+)$', line)
        if match:
            metric_name = match.group(1)
            labels = match.group(2)
            metric_value = float(match.group(3))

            container_id = extract_label_value(labels, 'name')
            if not container_id:
                continue

            if container_id not in container_data:
                container_data[container_id] = {
                    'cpu_uso': 0,
                    'memoria_uso': 0,
                    'red_velocidad': 0,
                    'almacenamiento_uso': 0
                }

            if metric_name == 'container_cpu_usage_seconds_total':
                container_data[container_id]['cpu_uso'] += metric_value
            elif metric_name == 'container_memory_usage_bytes':
                container_data[container_id]['memoria_uso'] = metric_value
            elif metric_name in ['container_network_receive_bytes_total', 'container_network_transmit_bytes_total']:
                previous_value = previous_network_metrics.get((container_id, metric_name), 0)
                delta = max(0, metric_value - previous_value)
                previous_network_metrics[(container_id, metric_name)] = metric_value
                container_data[container_id]['red_velocidad'] += delta
            elif metric_name == 'container_fs_usage_bytes':
                container_data[container_id]['almacenamiento_uso'] = metric_value

    for container_id, metrics in container_data.items():
        data.append({
            'contenedor_id': container_id,
            'cpu_uso': metrics['cpu_uso'],
            'memoria_uso': metrics['memoria_uso'],
            'red_velocidad': metrics['red_velocidad'],
            'almacenamiento_uso': metrics['almacenamiento_uso'],
            'timestamp': timestamp
        })

    return data

def extract_label_value(label_string, label_name):
    match = re.search(rf'{label_name}="([^"]+)"', label_string)
    return match.group(1) if match else None


def predecir(data):
    with open("static/trained_model.pkl", "rb") as model_file:
        model = pickle.load(model_file)

    scaler = MinMaxScaler()
    new_data = {
        "cpu_uso": data['cpu_uso'],
        "memoria_uso": data['memoria_uso'] * 1024 ** 3,
        "red_velocidad": data['red_velocidad'] * 1024 ** 2,
        "almacenamiento_uso": data['almacenamiento_uso'] * 1024 ** 3,
    }

    scaled_input = scaler.fit_transform(np.array(
        [[new_data["cpu_uso"], new_data["memoria_uso"], new_data["red_velocidad"], new_data["almacenamiento_uso"]]]))

    prediction = model.predict(scaled_input)

    state_mapping_reverse = {0: "Normal", 1: "Alerta", 2: "Critico"}
    predicted_state = state_mapping_reverse[prediction[0]]

    return predicted_state


def generar_reporte_pdf(contenedor_id, estado):
    archivo_pdf = f"static/reporte_{contenedor_id}.pdf"

    c = canvas.Canvas(archivo_pdf, pagesize=letter)
    c.setFont("Helvetica", 12)

    c.drawString(100, 750, "Reporte de Estado del Contenedor")
    c.drawString(100, 730, f"Contenedor ID: {contenedor_id}")
    c.drawString(100, 710, f"Estado: {estado}")


    '''c.drawString(100, 690, f"Uso de CPU: {metrics['cpu_uso']} segundos")
    c.drawString(100, 670, f"Uso de Memoria: {metrics['memoria_uso']} GB")
    c.drawString(100, 650, f"Velocidad de Red: {metrics['red_velocidad']} MB/s")
    c.drawString(100, 630, f"Uso de Almacenamiento: {metrics['almacenamiento_uso']} GB")'''

    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.drawString(100, 610, f"Fecha de generación del reporte: {fecha_hora}")

    if estado == "Alerta":
        c.drawString(100, 690, "Solución: Revisar el uso de recursos y optimizar las aplicaciones.")
    elif estado == "Critico":
        c.drawString(100, 690,
                     "Solución: Tomar acciones inmediatas para reducir el uso de recursos y verificar procesos.")

    c.save()
    return archivo_pdf

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_metrics', methods=['GET'])
def get_metrics():
    metrics = get_cadvisor_metrics()
    processed_data = process_metrics(metrics)

    results = []
    for data in processed_data:
        prediction = predecir(data)
        contenedores[data['contenedor_id']] = {'estado': prediction}
        results.append({
            'contenedor_id': data['contenedor_id'],
            'cpu_uso': data['cpu_uso'],
            'memoria_uso': data['memoria_uso'] / 1024**3,
            'red_velocidad': data['red_velocidad'] / 1024**2,
            'almacenamiento_uso': data['almacenamiento_uso'] / 1024**3,
            'prediccion': prediction
        })

    return jsonify(results)

@app.route('/descargar_reporte')
def descargar_reporte():
    contenedor_id = request.args.get('contenedor_id')  # Obtener el ID del contenedor
    estado = contenedores.get(contenedor_id, {}).get("estado", "Desconocido")
    archivo_pdf = generar_reporte_pdf(contenedor_id, estado)
    return send_from_directory(os.getcwd(), archivo_pdf, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
