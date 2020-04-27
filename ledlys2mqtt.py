#!/usr/bin/python3

import os
import re
import paho.mqtt.client as mqtt
import json
import subprocess
import time
from dotenv import load_dotenv
import logging
import asyncio
import importstruct
import socket

LYSPORT=15240
REPORTPORT=15241

OWNIP="10.20.0.50"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = {}
lampinit = {}

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
    client.subscribe("homeassistant/light/ulc20652/set")
    do_discovery()

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
            newcolortemp = settings[lampid]["color"]
        elif payload['state'] == "ON":
            if "brightness" in payload:
                newbrightness = int(payload['brightness'])
            else:
                newbrightness = settings[lampid]["bri"]
            if "color_temp" in payload:
                calculatedcolortemp = int((int(payload['color_temp']) -153)/3.47)
                newcolortemp = calculatedcolortemp
            else:
                newcolortemp = settings[lampid]["color"]
            if "brightness" not in payload and "color_temp" not in payload:
                newbrightness = settings[lampid]["prev"]
                newcolortemp = settings[lampid]["color"]
        do_setlamp(int(lampid),int(newbrightness),int(newcolortemp))
        do_enquire(int(lampid))

def do_llbroadcast(binary_data):
    opened_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    opened_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    opened_socket.sendto(binary_data, ("<broadcast>", LYSPORT))
    opened_socket.close

def do_discovery():
    binary_data=importstruct.dicttobytes(9,0)
    do_llbroadcast(binary_data)

def do_enquire(lampid):
    binary_data=importstruct.dicttobytes(8,lampid)
    do_llbroadcast(binary_data)

def do_setlamp(lampid,bri=0,col=100):
    binary_data=importstruct.dicttobytes(2,lampid,{"val8_0": bri,"val8_1": col})
    do_llbroadcast(binary_data)

def set_lampstatus(lampid,bri=None,col=None):
    global settings
    global lampinit
    mqtt_state = {}
    change = False
    if col:
        if int(col) != settings[str(lampid)]["color"]:
            change = True
            settings[str(lampid)]["color"] = int(col)

    if int(bri) > -1:
        if int(bri) != settings[str(lampid)]["bri"]:
            change = True
            if bri > 0:
                settings[str(lampid)]["prev"] = bri
            settings[str(lampid)]["bri"] = bri       
    if lampid in lampinit:
        if int(lampinit[lampid]) == 1:
            change = True
            lampinit[lampid] = 2

    if change:
        if bri == 0:
            mqtt_state["state"] = "OFF"
        else:
            mqtt_state["state"] = "ON"
            mqtt_state["brightness"] = settings[str(lampid)]["bri"]
            mqtt_state["color_temp"] = int((int(settings[str(lampid)]["color"]) * 3.47 ) + 153)
        mqttpath = "homeassistant/light/ulc" + str(lampid)
        client.publish(mqttpath + "/state", payload=json.dumps(mqtt_state),retain=True)
        logger.info("Syncronizing lamp %s: %s",str(lampid),mqtt_state)
        write_settings(settings)

def init_lamp(lampid, lamp):
    global settings
    global lampinit
    mqttpath = "homeassistant/light/ulc" + str(lamp["sourceid"])
    hauniqueid = "ulc" + str(lamp["sourceid"])
    conftopic =  mqttpath + "/config"
    mqtt_conf = {"~": mqttpath, "name": lamp["lampname"],  "unique_id": hauniqueid, "cmd_t": "~/set", "stat_t": "~/state", "schema": "json", "device": {"name": "ULC-"+ str(lamp["sourceid"])+" ("+lamp["lampname"]+")","model": "ULC (" +str(lamp["hdwversion_1"])+ "." +str(lamp["hdwversion_2"])+ ")","manufacturer": "LedLys AS", "identifiers": [lamp["serial"], hauniqueid],"sw_version": str(lamp["stwversion_1"]) + "." + str(lamp["stwversion_2"])},  "brightness": True, "bri_scl": 100 }
    if int(lamp["lampMode"]) == 1:
        mqtt_conf["color_temp"] = True
    client.publish(conftopic, payload=json.dumps(mqtt_conf),retain=True)
    subject= mqttpath+ "/set"
    client.subscribe(subject)
    lampinit[lamp["sourceid"]] = 1
    do_enquire(lamp["sourceid"])

class ledlysServer:
    def connection_made(self, transport):
        self.transport = transport
    def datagram_received(self, data, addr):
        global settings
        global lampinit
        packet=importstruct.bytestodict(data)
        if str(addr[0]) == OWNIP:
            logger.debug('Dont mind me talking to myself Type: ' + str(packet["type"])+ "(" + str(packet["msgtype"]["name"])+")" )
        else:
            logger.debug('Received data from '+ str(addr[0]) + " Type: " + str(packet["type"])+ "(" + str(packet["msgtype"]["name"])+")"  )
            if int(packet["type"]) == 3:
                set_lampstatus(packet["sourceid"],packet["unscaledIntensityPct"],packet["unscaledTemperaturePct"])
            elif int(packet["type"]) == 10:
                if packet["sourceid"] not in lampinit:
                    init_lamp(packet["sourceid"],packet)
                set_lampstatus(packet["sourceid"],packet["currentIntensityPct"],packet["currentTemperaturePct"])


loop = asyncio.get_event_loop()
logger.info('Starting UDP server')
listen = loop.create_datagram_endpoint(ledlysServer, local_addr=('0.0.0.0', LYSPORT))
transport, protocol = loop.run_until_complete(listen)  
listen2 = loop.create_datagram_endpoint(ledlysServer, local_addr=('0.0.0.0', REPORTPORT))
transport, protocol = loop.run_until_complete(listen2)

if os.path.isfile(SETTINGS_FILE):
    settings = read_settings()

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(MQTTUSER, MQTTPASS)
client.connect(MQTTHOST)
client.enable_logger(logger)
logger.info('Main loop starting')
client.loop_start()
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

transport.close()
loop.close()
