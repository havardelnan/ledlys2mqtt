#!/usr/bin/python3
import os
import re
import paho.mqtt.client as mqtt
import json
import subprocess
from dotenv import load_dotenv

settings = {}

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
    global settings
    reg = "homeassistant/light/ulc([0-9]*)/set"
    match = re.match(reg, msg.topic)
    if bool(match):
        payload = json.loads(msg.payload)
        lampid = match.group(1)
        if payload['state'] == "OFF":
            process = subprocess.run([LLCMD,'lightset', lampid, "0"])
        elif payload['state'] == "ON":
            if "brightness" in payload:
                process = subprocess.run([LLCMD,'lightset', lampid, str(payload['brightness'])])
                settings[lampid]["prev"] = int(payload['brightness'])
                write_settings(settings)
            if "color_temp" in payload:
                calculatedcolortemp = (int(payload['color_temp']) -153)/3.47
                process = subprocess.run([LLCMD,'setcolor', lampid, str(calculatedcolortemp)])
            if "brightness" not in payload and "color_temp" not in payload:
                saved_brightness = settings[lampid]["prev"]
                process = subprocess.run([LLCMD,'lightset', lampid, str(saved_brightness)]) 
        sync_lamp(lampid)

def on_log(client, userdata, level, buf):
    print("log: ",buf)

def init_ledlys():
    global settings
    print("Initializing...")
    discovery = json.loads(subprocess.run([LLCMD, "discover"], stdout=subprocess.PIPE).stdout.decode('utf-8'))
    if os.path.isfile(SETTINGS_FILE):
        settings = read_settings()
    for lamp in discovery:
        if lamp["intensity"] != "0":
                settings[lamp["lamp"]] = {"prev": int(lamp["intensity"])}
        mqttpath = "homeassistant/light/ulc" + lamp["lamp"]
        hauniqueid = "ulc" + lamp["lamp"]
        conftopic =  mqttpath + "/config"
        mqtt_conf = {"~": mqttpath, "name": lamp["name"],  "unique_id": hauniqueid, "cmd_t": "~/set", "stat_t": "~/state", "schema": "json", "device": {"name": "ULC-"+lamp["lamp"]+" ("+lamp["name"]+")","model": "ULC","manufacturer": "LedLys AS", "identifiers": [lamp["serial"], hauniqueid],"sw_version": lamp["version"]},  "brightness": True, "bri_scl": 100 }
        if lamp["varicolor"] == "1":
            mqtt_conf["color_temp"] = True
        client.publish(conftopic, payload=json.dumps(mqtt_conf),retain=True)
        subject= mqttpath+ "/set"
        client.subscribe(subject)
        sync_lamp(lamp["lamp"])
        #print(settings)
        #write_settings(settings)
def sync_lamp(lampid):
    enquire = json.loads(subprocess.run([LLCMD, "enquire", lampid], stdout=subprocess.PIPE).stdout.decode('utf-8'))
    if enquire["report"]["intensity"] == "0":
        mqtt_state = {"state": "OFF"}
    else:
        mqtt_state = {"state": "ON", "brightness": int(enquire["report"]["intensity"])}
        if enquire["report"]["varicolor"] == "1":
            calculatedcolortemp = (int(enquire["report"]["color"]) * 3.47 ) + 153
            mqtt_state["color_temp"] = calculatedcolortemp
    mqttpath = "homeassistant/light/ulc" + lampid
    client.publish(mqttpath + "/state", payload=json.dumps(mqtt_state),retain=True)





client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_log=on_log
client.username_pw_set(MQTTUSER, MQTTPASS)
client.connect(MQTTHOST)
client.loop_forever()

