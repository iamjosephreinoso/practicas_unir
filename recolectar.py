import requests
import time
import re
import pickle
import numpy as np
from sklearn.preprocessing import MinMaxScaler


def get_cadvisor_metrics():
    url = 'http://localhost:8080/metrics' #Cambiar el puerto si el cAdvisor esta ocupando otro puerto
    response = requests.get(url)
    return response.text

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
                container_data[container_id]['red_velocidad'] += metric_value
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


#-------------------------------------------------------------------------


def predecir(data):
    with open("trained_model.pkl", "rb") as model_file:
        model = pickle.load(model_file)

    scaler = MinMaxScaler()
    new_data = {
        "cpu_uso": data['cpu_uso'],
        "memoria_uso": data['memoria_uso'] * 1024**3,  
        "red_velocidad": data['red_velocidad'] * 1024**2, 
        "almacenamiento_uso": data['almacenamiento_uso'] * 1024**3,
    }
    
    #print(new_data)

    scaled_input = scaler.fit_transform(np.array([[
        new_data["cpu_uso"], 
        new_data["memoria_uso"], 
        new_data["red_velocidad"], 
        new_data["almacenamiento_uso"]
    ]]))

    prediction = model.predict(scaled_input)

    state_mapping_reverse = {0: "Normal", 1: "Alert", 2: "Critical"}
    predicted_state = state_mapping_reverse[prediction[0]]

    print(f"La predicción del contenedor {data['contenedor_id']}es: {predicted_state}")


#--------------------------------------------------------------------------

while True:
    metrics = get_cadvisor_metrics() 
    processed_data = process_metrics(metrics)
    for data in processed_data:
        #print(data)
        predecir(data)
    time.sleep(30)  # Esperar 30 segundo
