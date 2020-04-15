#!/usr/bin/python3
import os
import paho.mqtt.client as mqtt
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()
MQTTUSER = os.getenv('MQTT_USER')
MQTTPASS = os.getenv('MQTT_PASS')
MQTTHOST = os.getenv('MQTT_HOST')
LLCMD = "/usr/bin/ledlyscmd2"
SETTINGS_FILE="ledlys2mqtt.json"
#settingsfile

def read_settings():
    with open(SETTINGS_FILE) as json_file:
        return json.load(json_file)

def write_settings(settings):
    with open(SETTINGS_FILE, 'w') as outfile:
        json.dump(settings, outfile)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    init_ledlys()

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    if msg.topic == "homeassistant/light/ulc20652/set":
        payload = json.loads(msg.payload)
        lampid = '20652'
        retdict= {}
        if payload['state'] == "OFF":
            retdict['state'] = "OFF"
            process = subprocess.run([LLCMD,'lightset', lampid, "0"])
        else :
            retdict['state'] = "ON"
            if payload['brightness']:
                retdict['brightness'] = int(payload['brightness'])
                process = subprocess.run([LLCMD,'lightset', lampid, str(payload['brightness'])])
        returnjson = json.dumps(retdict)
        client.publish("homeassistant/light/ulc20652/state", returnjson)

def on_log(client, userdata, level, buf):
    print("log: ",buf)

def init_ledlys():
    print("Initializing...")
    discovery = json.loads(subprocess.run([LLCMD, "discover"], stdout=subprocess.PIPE).stdout.decode('utf-8'))
    if os.path.isfile(SETTINGS_FILE):
        settings = read_settings()
    else:
        settings = {}
        for x in discovery:
            #print("---")
            #print(x)
            settings[x["lamp"]] = x
            subject="homeassistant/light/ulc" + x["lamp"] + "/set"
            client.subscribe(subject)
        print(settings)
        write_settings(settings)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_log=on_log
client.username_pw_set(MQTTUSER, MQTTPASS)
client.connect(MQTTHOST)
client.loop_forever()

