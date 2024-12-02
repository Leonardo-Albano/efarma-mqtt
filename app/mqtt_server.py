mport paho.mqtt.client as mqtt
import json
import os
import threading
import time
import requests
from flask import Flask, jsonify

# Configuração dos endpoints MQTT
ENDPOINT_ENTRY_URL = "http://157.230.224.194:5001/api/StockRoom/Entry"
ENDPOINT_EXIT_URL = "http://157.230.224.194:5001/api/StockRoom/Exit"

# Caminho do arquivo JSON onde as mensagens são salvas
JSON_FILE_PATH = '/root/mqtt_messages/mensagens_mqtt.json'
# JSON_FILE_PATH = r'C:\Users\Gabriel França\Desktop\mensagens_mqtt_acesso.json'

# Tempo de inatividade antes de registrar como vazio (em segundos)
INACTIVITY_TIMEOUT = 4

# Variável global para armazenar o tempo da última mensagem
last_message_time = time.time()

# Função para salvar as tags no arquivo JSON
def save_tags_to_json(tags):
    data = {
        "topic": "Tags_Prateleira",
        "tags": tags
    }

    # Cria o diretório se não existir
    os.makedirs(os.path.dirname(JSON_FILE_PATH), exist_ok=True)

    # Salva no arquivo JSON
    with open(JSON_FILE_PATH, 'w') as f:
        json.dump(data, f, indent=4)

    if tags:
        print(f"Tags identificadas: {tags}")
    else:
        print("Nenhuma tag detectada. Arquivo atualizado para vazio.")

# Função de callback para o tópico 'Tags_Prateleira'
def on_message_tags_prateleira(client, userdata, message):
    global last_message_time
    msg = message.payload.decode('utf-8').strip()
    print(f"Mensagem recebida no tópico {message.topic}: {msg}")

    # Atualiza o tempo da última mensagem recebida
    last_message_time = time.time()

    # Processa a mensagem recebida
    try:
        tags = json.loads(msg) if msg else []
    except json.JSONDecodeError:
        tags = []

    # Salva as tags no arquivo JSON
    save_tags_to_json(tags)

# Função de callback para os tópicos 'Solicitar_Acesso' e 'Solicitar_Saida'
def on_message_access(client, userdata, message):
    msg = message.payload.decode('utf-8')
    print(f"Mensagem recebida no tópico {message.topic}: {msg}")

    # Dados a serem enviados ao endpoint
    data = {
        "stockRoomUniqueId": "bf6a7dcc",  # ID fixo para ambos os tópicos
        "tagCode": msg  # ID da tag recebido na mensagem
    }

    # Escolhe o endpoint apropriado com base no tópico
    endpoint_url = ENDPOINT_ENTRY_URL if message.topic == "Solicitar_Acesso" else ENDPOINT_EXIT_URL

    # Envia os dados ao endpoint
    send_to_endpoint(client, data, endpoint_url)

# Função para enviar dados JSON ao endpoint de entrada ou saída
def send_to_endpoint(client, data, endpoint_url):
    try:
        response = requests.post(endpoint_url, json=data)
        if response.status_code == 200:
            print("Dados enviados com sucesso!")
            response_data = response.json()
            result_message = {
                "dados": response_data.get("message", ""),
                "success": response_data.get("success", False)
            }
        elif response.status_code != 404:
            print(f"Falha ao enviar dados. Código de status: {response.status_code}")
            response_data = response.json()
            result_message = {
                "dados": response_data.get("message", ""),
                "success": response_data.get("success", False)
            }
        else:
            result_message = {"dados": "Acesso nao autorizado", "success": False}
    except requests.RequestException as e:
        print(f"Erro ao conectar ao endpoint: {e}")
        result_message = {"dados": "Erro ao conectar ao endpoint.", "success": False}

    # Envia a resposta para o tópico 'Retorno_Acesso'
    send_return_message(client, result_message)

# Função para publicar a mensagem de retorno no tópico 'Retorno_Acesso'
def send_return_message(client, message):
    client.publish("Retorno_Acesso", json.dumps(message))
    print(f"Mensagem enviada para 'Retorno_Acesso': {message}")

# Função para monitorar inatividade
def monitor_inactivity():
    global last_message_time
    while True:
        current_time = time.time()
        # Se passou mais tempo que o permitido sem mensagem, atualiza como vazio
        if current_time - last_message_time > INACTIVITY_TIMEOUT:
            print("Tempo de inatividade excedido. Atualizando arquivo para vazio.")
            save_tags_to_json([])  # Atualiza o arquivo com valor vazio
            last_message_time = current_time  # Reseta o tempo para evitar repetições
        time.sleep(1)  # Verifica a cada 1 segundo

# Configuração do cliente MQTT
def configure_mqtt_client(client_id, topic, on_message_callback):
    client = mqtt.Client(client_id)
    client.on_connect = lambda c, u, f, rc: c.subscribe(topic)
    client.on_message = on_message_callback
    client.connect("138.197.226.240", 1883, 10)
    return client

# Inicia os clientes MQTT
print("Iniciando clientes MQTT...")
client_tags = configure_mqtt_client("ClienteTagsPrateleira", "Tags_Prateleira", on_message_tags_prateleira)
client_access = configure_mqtt_client("ClienteAccess", "Solicitar_Acesso", on_message_access)
client_exit = configure_mqtt_client("ClienteExit", "Solicitar_Saida", on_message_access)
client_tags.loop_start()
client_access.loop_start()
client_exit.loop_start()

# Inicia a thread para monitorar inatividade
inactivity_thread = threading.Thread(target=monitor_inactivity, daemon=True)
inactivity_thread.start()

# Configuração do servidor Flask para consulta do JSON
app = Flask(_name_)

@app.route('/get_tags', methods=['GET'])
def get_tags():
    if os.path.exists(JSON_FILE_PATH):
        with open(JSON_FILE_PATH, 'r') as f:
            data = json.load(f)
        return jsonify(data), 200
    else:
        return jsonify({"error": "Nenhum dado disponível"}), 404

if _name_ == "_main_":
    app.run(host='0.0.0.0', port=5002)
