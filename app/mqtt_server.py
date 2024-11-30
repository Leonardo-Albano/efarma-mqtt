import paho.mqtt.client as mqtt
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
        # Se passou mais tempo que o tempo de inatividade definido
        if current_time - last_message_time > INACTIVITY_TIMEOUT:
            print("Nenhuma mensagem recebida. Atualizando tags para vazio.")
            save_tags_to_json([])  # Salva as tags como vazio
            last_message_time = current_time  # Reseta o tempo da última mensagem
        time.sleep(1)

# Função de callback quando a conexão MQTT for estabelecida
def on_connect(client, userdata, flags, rc):
    print(f"Conectado ao broker com código: {rc}")

    # Inscreve-se nos tópicos relevantes
    client.subscribe("Tags_Prateleira")
    client.subscribe("Solicitar_Acesso")
    client.subscribe("Solicitar_Saida")

# Configuração do cliente MQTT
client = mqtt.Client()

# Atribui as funções de callback
client.on_connect = on_connect
client.on_message = on_message_tags_prateleira

# Conecta ao broker MQTT
client.connect("localhost", 1883, 60)

# Inicia o monitoramento de inatividade em uma thread separada
inactivity_thread = threading.Thread(target=monitor_inactivity)
inactivity_thread.daemon = True
inactivity_thread.start()

# Inicia o loop do cliente MQTT
client.loop_start()

# Flask app (se necessário)
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "running"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
