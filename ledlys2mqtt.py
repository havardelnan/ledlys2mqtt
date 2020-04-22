#!/usr/bin/python3
import os
import re
import paho.mqtt.client as mqtt
import json
import subprocess
import time
from dotenv import load_dotenv
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = {}

load_dotenv()
MQTTUSER = os.getenv('MQTT_USER')
MQTTPASS = os.getenv('MQTT_PASS')
MQTTHOST = os.getenv('MQTT_HOST')
LLCMD = "/usr/bin/ledlyscmd"
SETTINGS_FILE="ledlys2mqtt.json"

def read_settings():
    with open(SETTINGS_FILE) as json_file:
        return json.load(json_file)

def write_settings(settings):
    with open(SETTINGS_FILE, 'w') as outfile:
        json.dump(settings, outfile)

def on_connect(client, userdata, flags, rc):
    logger.info("Connected to mqtt broker with result code %s",str(rc))
    init_ledlys()

def on_message(client, userdata, msg):
    global settings
    reg = "homeassistant/light/ulc([0-9]*)/set"
    match = re.match(reg, msg.topic)
    if bool(match):
        payload = json.loads(msg.payload)
        lampid = match.group(1)
        logger.info("Setting lamp %s:%s",str(lampid),payload)
        if payload['state'] == "OFF":
            newbrightness = 0
            newcolortemp = settings[lampid]["prevcolor"]
        elif payload['state'] == "ON":
            if "brightness" in payload:
                newbrightness = int(payload['brightness'])
            else:
                newbrightness = settings[lampid]["prev"]
            if "color_temp" in payload:
                calculatedcolortemp = int((int(payload['color_temp']) -153)/3.47)
                newcolortemp = calculatedcolortemp
            else:
                newcolortemp = settings[lampid]["prevcolor"]
            if "brightness" not in payload and "color_temp" not in payload:
                newbrightness = settings[lampid]["prev"]
                newcolortemp = settings[lampid]["prevcolor"]
        process = subprocess.run([LLCMD,'setlight', lampid, str(newbrightness), str(newcolortemp)]) 
        if int(newbrightness) != 0:
            settings[lampid]["prev"] = int(newbrightness)
        settings[lampid]["prevcolor"] = int(newcolortemp)
        write_settings(settings)
        sync_lamp(lampid)

def init_ledlys():
    global settings
    logger.info("Initializing")
    discovery = json.loads(subprocess.run([LLCMD, "discover"], stdout=subprocess.PIPE).stdout.decode('utf-8'))
    if os.path.isfile(SETTINGS_FILE):
        settings = read_settings()
    time.sleep(1)    
    for lamp in discovery:
        if lamp["currentIntensityPct"] != "0":
            settings[lamp["lamp"]] = {"prev": int(lamp["currentIntensityPct"])}
            settings[lamp["lamp"]]["prevcolor"] = int(lamp["currentTemperaturePct"])
        mqttpath = "homeassistant/light/ulc" + lamp["lamp"]
        hauniqueid = "ulc" + lamp["lamp"]
        conftopic =  mqttpath + "/config"
        mqtt_conf = {"~": mqttpath, "name": lamp["name"],  "unique_id": hauniqueid, "cmd_t": "~/set", "stat_t": "~/state", "schema": "json", "device": {"name": "ULC-"+lamp["lamp"]+" ("+lamp["name"]+")","model": "ULC ("+lamp["hdwversion"]+")","manufacturer": "LedLys AS", "identifiers": [lamp["serial"], hauniqueid],"sw_version": lamp["stwversion"]},  "brightness": True, "bri_scl": 100 }
        if int(lamp["lampMode"]) == 1:
            mqtt_conf["color_temp"] = True
        client.publish(conftopic, payload=json.dumps(mqtt_conf),retain=True)
        subject= mqttpath+ "/set"
        client.subscribe(subject)
        sync_lamp(lamp["lamp"])

def sync_lamp(lampid):
    enquire = json.loads(subprocess.run([LLCMD, "enquire", lampid], stdout=subprocess.PIPE).stdout.decode('utf-8'))
    if int(enquire["report"]["currentIntensityPct"]) == 0:
        mqtt_state = {"state": "OFF"}
    else:
        mqtt_state = {"state": "ON", "brightness": int(enquire["report"]["currentIntensityPct"])}
        if int(enquire["report"]["lampMode"]) == 1:
            calculatedcolortemp = int((int(enquire["report"]["currentTemperaturePct"]) * 3.47 ) + 153)
            mqtt_state["color_temp"] = calculatedcolortemp
    mqttpath = "homeassistant/light/ulc" + lampid
    client.publish(mqttpath + "/state", payload=json.dumps(mqtt_state),retain=True)
    logger.info("Syncronizing lamp %s: %s",str(lampid),mqtt_state)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(MQTTUSER, MQTTPASS)
client.connect(MQTTHOST)
client.enable_logger(logger)
logger.info('Main loop starting')
client.loop_forever()
