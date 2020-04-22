import socket
import struct
LYSPORT=15240
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

datalabels = {2: ["salt","type","cksum","targetid","sourceid","brightness","colortemp"],3: ["salt","type","cksum","targetid","sourceid","stwversionmay","stwversionmin","unscaledIntensityPct","unscaledTemperaturePct","sceneScaleIntensityPct","sceneScaleTemperaturePct","scalepct","rsvd","powerkWh","powerdays","powersecs","powernow","presencedetects","presenceswitch","presencems","presence5Min","_trssi","secondsSinceRestart","voltage","ambientLight","airTemperature","airHumidity","airCO2ppm","airTVOCppb","airPressure","pm2","pm10","s4","rxcnt","txcnt","ssid","lampname","powerkWhSinceRestart","aliveSent","pingRecv","uptime","presentPeers","presentI2C","newDust","sdcode","sduptime","rsreason","rsexccause"],8: ["salt","type","cksum","targetid","sourceid"]}
msglist = ["present","absent","setlight","alive","pifind","ident","beep","motion","enquire","discover","report","eeprom","eepromresp","state","stateresp","restart","zapp","","ack","clrstats","scene","toggle","alarmset","alarmon","","","commit","setpeer","delpeer","setgrp","delgroup","setmaxpct","setminpct","setscale","setoffdly","setupspeed","setdownspeed","setid","setname","setssid","setpass","","setfade","seteeprom","setopmode","setopgroup","setoptout","setopadc","setlampmode","setisswitch","setopspeed","setscene","delscene","setdeflight","setlamppower","setrtcscene","setrtcdays","setrtctime","setrtcdate","setlatitude","setlongitude","setclock","settimezone","setoponscn","setopoffscn","setswapns","setmamin","setmamax","eerestore","delay","help","quit"]
client.bind(("", LYSPORT))
while True: 
    data, addr = client.recvfrom(1024)
    header = struct.unpack("IBBHH",bytearray(data)[:10])
    print("received message:" + str(msglist[header[1]]))
    if int(header[1]) == 3:
        result=list(struct.unpack("IBBHHxx8BfHIf4IiIB3f2H4f2I34s34sf5IB4I",data))
        result[36] = str(result[36].decode("utf-8")).rstrip('\x00')
        result[35] = (result[35].decode("utf-8")).rstrip('\x00')
        result=dict(zip(datalabels[header[1]], result))
        result["stwversion"] = float(str(result["stwversionmay"])+"."+str(result["stwversionmin"]))
        result["ip"] = addr[0]
        print("Lamp: "+ str(result["sourceid"]))
        print("Name: "+ str(result["lampname"]))
        print(result)
    elif int(header[1]) == 2:
        result=list(struct.unpack("IBBHHxx2Bxx",data))
        result=dict(zip(datalabels[header[1]], result))
        print("Lamp: "+ str(result["sourceid"]))
        print(result)
    elif int(header[1]) == 8:
        result=list(struct.unpack("IBBHHxx",data))
        result=dict(zip(datalabels[header[1]], result))
        print("Lamp: "+ str(result["sourceid"]))
        print(result)



 