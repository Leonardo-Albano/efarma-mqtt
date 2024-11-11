import paho.mqtt.client as mqtt
import json
import os
import requests
from flask import Flask, jsonify, request

# Configuração dos endpoints MQTT
ENDPOINT_ENTRY_URL = "http://157.230.224.194:5001/api/StockRoom/Entry"
ENDPOINT_EXIT_URL = "http://157.230.224.194:5001/api/StockRoom/Exit"

# Caminho do arquivo JSON onde as mensagens são salvas
JSON_FILE_PATH = '/root/mqtt_messages/mensagens_mqtt.json'

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

# Função de callback para o tópico 'Tags_Prateleira'
def on_message_tags_prateleira(client, userdata, message):
    msg = message.payload.decode('utf-8').strip()
    print(f"Mensagem recebida no tópico {message.topic}: {msg}")

    # Verifica se a mensagem está vazia e define o conteúdo do JSON
    data = {
        "topic": message.topic,
        "tags": json.loads(msg) if msg else []
    }

    # Cria o diretório se não existir
    os.makedirs(os.path.dirname(JSON_FILE_PATH), exist_ok=True)
    
    # Salva no arquivo JSON sobrescrevendo o conteúdo anterior
    with open(JSON_FILE_PATH, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Arquivo JSON sobrescrito com nova mensagem em {JSON_FILE_PATH}")

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

    # Envia os dados ao endpoint e publica a resposta no tópico 'Retorno_Acesso'
    send_to_endpoint(client, data, endpoint_url)

# Função para configurar e conectar o cliente MQTT
def configure_mqtt_client(client_id, topic):
    def on_connect(client, userdata, flags, rc):
        pass  # Não exibe mensagens de conexão

    # Associa a função de callback adequada ao tópico
    on_message = on_message_access if topic in ["Solicitar_Acesso", "Solicitar_Saida"] else on_message_tags_prateleira

    client = mqtt.Client(client_id)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("138.197.226.240", 1883, 60)
    client.subscribe(topic)  # Inscreve-se no tópico

    return client

# Configurando os clientes MQTT e exibindo uma mensagem única
print("Iniciando a configuração dos clientes MQTT e inscrição nos tópicos...")
client1 = configure_mqtt_client("ClienteSubscriber1", "Solicitar_Acesso")
client2 = configure_mqtt_client("ClienteSubscriber2", "Tags_Prateleira")
client3 = configure_mqtt_client("ClienteSubscriber3", "Solicitar_Saida")
print("Clientes MQTT configurados e inscritos nos tópicos.")

# Inicia o loop para todos os clientes
client1.loop_start()
client2.loop_start()
client3.loop_start()

# Configuração do servidor Flask para servir o endpoint HTTP
app = Flask(__name__)

# Endpoint para obter mensagens de Tags_Prateleira no formato JSON
@app.route('/get_tags', methods=['GET'])
def get_tags():
    tag_codes = request.args.get("TagCodes")
    
    # Verifica se o arquivo JSON existe
    if os.path.exists(JSON_FILE_PATH):
        with open(JSON_FILE_PATH, 'r') as f:
            data = json.load(f)

        # Retorna o conteúdo no formato solicitado
        return jsonify(data), 200
    else:
        return jsonify({"error": "Nenhum dado disponível"}), 404

# Mantém o servidor Flask em execução
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002)