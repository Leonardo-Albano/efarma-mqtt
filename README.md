docker build -t efarmatcc/efarmamqtt .

docker push efarmatcc/efarmamqtt

docker pull efarmatcc/efarmamqtt

docker run -d -p 5002:5002 --name efarmamqtt efarmatcc/efarmamqtt