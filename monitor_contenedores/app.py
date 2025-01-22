from flask import Flask, render_template, jsonify, request, send_from_directory
import requests
import time
import re
import pickle
import numpy as np
from prometheus_client import Counter, generate_latest, Summary
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sklearn.preprocessing import MinMaxScaler
import os
from datetime import datetime

app = Flask(__name__)


REQUEST_COUNT = Counter('flask_request_count', 'Total number of requests', ['method', 'endpoint'])
REQUEST_LATENCY = Summary('flask_request_latency_seconds', 'Request latency')

previous_network_metrics = {}
contenedores = {}

def get_cadvisor_metrics():
    url = 'http://cadvisor:8080/metrics'  # Change port if necessary
    try:
        response = requests.get(url, timeout=5)  # Timeout of 5 seconds
        if response.status_code == 200:
            return response.text
        else:
            return None
    except requests.RequestException as e:
        return None

def process_metrics(metrics):

    if not metrics:
        return []

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
    print(f"Etiquetas disponibles: {label_string}")
    match = re.search(rf'{label_name}="([^"]+)"', label_string)
    if match and match.group(1):  # Verifica que la etiqueta no esté vacía
        return match.group(1)
    else:
        return None

def predecir(data):

    with open("static/trained_model1.pkl", "rb") as model_file:
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
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.drawString(100, 690, f"Fecha de generación del reporte: {fecha_hora}")

    c.save()
    return archivo_pdf

@app.route('/')
def index():
    REQUEST_COUNT.labels(method='GET', endpoint='/').inc()
    return render_template('index.html')

@app.route('/get_metrics', methods=['GET'])
@REQUEST_LATENCY.time()
def get_metrics():
    metrics = get_cadvisor_metrics()
    if metrics is None:
        return jsonify({'error': 'Unable to fetch metrics from cAdvisor'}), 500

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

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/descargar_reporte')
def descargar_reporte():
    contenedor_id = request.args.get('contenedor_id')
    estado = contenedores.get(contenedor_id, {}).get("estado", "Desconocido")
    archivo_pdf = generar_reporte_pdf(contenedor_id, estado)
    return send_from_directory(os.getcwd(), archivo_pdf, as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
