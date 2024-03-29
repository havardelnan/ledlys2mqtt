import re
# import sys
import struct
# import json

NAMESIZE = 34
MAXGROUPS = 100
MAXPEERS = 100
MAXBUTTS = 8
MAXSCENES = 16
MAXTIMES = 20

f = open("../ledlys_embedded/msglist.h", "r")
msgtypes = f.read()
maindict = {"structs": {}, "msgtypes": {}}
i = 0
for line in msgtypes.splitlines():
    pattern = r'^MSG\("([^"]*)"[^,]*,[^,]*,[^,]*,[^"]*"([^"]*)"[^,]*,[^,]*,[ ]*(\w*).*$'
    result = re.match(pattern, line)
    if result:
        maindict["msgtypes"][i] = {"name": str(result.group(1)).strip(), "description": str(result.group(2)).strip(), "msgclass": str(result.group(3)).strip()}
        i = i+1

f = open("../ledlys_embedded/msgs.h", "r")
inputstruct = f.read()
currentstruct = None
translatedict = {"uint8_t": "B", "uint16_t": "H", "uint32_t": "I", "float": "f", "int8_t": "b", "int16_t": "h", "int32_t": "i", "char": "s", "struct": ""}
translatedict2 = {"uint8_t": "int", "uint16_t": "int", "uint32_t": "int", "float": "float", "int8_t": "int", "int16_t": "int", "int32_t": "int", "char": "str"}
for line in inputstruct.splitlines():
    line = line.strip()
    pattern = r'^struct (.*)\{$'
    result = re.match(pattern, line)
    # print("-"+l+"-")
    if line == "":
        # print("blankline no thankz")
        _ = None
    elif line[0] == "/" or line.strip() == "PAD":
        # print("These are not the lines you are looking for: " + l)
        _ = None
    elif line.strip() == "};":
        # print("End of struct: " + str(currentstruct))
        currentstruct = None
    elif result:
        currentstruct = str(result.group(1)).strip()
        # print("Start of struct: " + currentstruct)
        maindict["structs"][currentstruct] = {}
        maindict["structs"][currentstruct]["keys"] = {}
        maindict["structs"][currentstruct]["pack"] = ""
        keyindex = 0
    elif currentstruct:
        pattern = r'^([a-zA-Z0-9_]+)[ ]*([a-zA-Z0-9_]+|[a-zA-Z0-9_, ]+)(?:\[([a-zA-Z0-9_]*)\])?(?: ([a-zA-Z0-9_]*))?\;(?:.*)?$'
        result2 = re.match(pattern, line)
        if result2:
            keys = str(result2.group(2)).split(",")
            for key in keys:
                key = key.strip()
                if result2.group(1) in translatedict:
                    if result2.group(1) == "struct":
                        maindict["structs"][currentstruct]["pack"] += maindict["structs"][key]["pack"]
                        if str(result2.group(4)) == "hdr":
                            maindict["structs"][currentstruct]["pack"] += "xx"
                    elif result2.group(3):
                        maindict["structs"][currentstruct]["pack"] += str(int(eval(result2.group(3))))
                    maindict["structs"][currentstruct]["pack"] += translatedict[result2.group(1)]
                else:
                    print("datatype not handled: " + result2.group(1))
                if result2.group(1) == "struct":
                    for x in range(len(maindict["structs"][result2.group(2)]["keys"])):
                        maindict["structs"][currentstruct]["keys"][keyindex] = maindict["structs"][result2.group(2)]["keys"][x]
                        keyindex = int(keyindex + 1)
                elif result2.group(3) and result2.group(1) != "char":
                    for x in range(int(eval(result2.group(3)))):
                        maindict["structs"][currentstruct]["keys"][keyindex] = {"name": key+"_"+str(x+1), "type":  translatedict2[result2.group(1)]}
                        keyindex = int(keyindex + 1)
                else:
                    maindict["structs"][currentstruct]["keys"][keyindex] = {"name": key, "type":  translatedict2[result2.group(1)]}
                    keyindex = int(keyindex + 1)
        # else:
            # print("not handled:" + line)
    # else:
        # print("line not inside struct:" + line)


def bytestodict(bytestring):
    header = struct.unpack(maindict["structs"]['hdr_t']["pack"], bytearray(bytestring)[:struct.calcsize(maindict["structs"]['hdr_t']["pack"])])
    msgtype = (maindict["msgtypes"][int(header[1])])
    msgtype["idx"] = int(header[1])
    type = msgtype["msgclass"]
    t = maindict["structs"][type]
    if len(bytestring) != struct.calcsize(t["pack"]):
        # print("ERROR: bytestring do not match size of " + type)
        t["pack"] = t["pack"].ljust((len(t["pack"])+(len(bytestring) - struct.calcsize(t["pack"]))), 'x')
    r = list(struct.unpack(t["pack"], bytestring))
    if len(r) != len(t["keys"]):
        print("ERROR: resulting list does not match number of keys")
    a = {"msgtype": msgtype}
    for x in range(len(t["keys"])):
        key = t["keys"][x]
        res = r[x]
        if key["type"] == "str":
            a[key["name"]] = str(res.decode("utf-8"))[:str(res.decode("utf-8")).index('\x00')]
        else:
            a[key["name"]] = eval(key["type"]+"("+str(res)+")")
    return a


def dicttobytes(msgid, lampid, msgdict={}):
    msgtype = maindict["msgtypes"][int(msgid)]
    # build the header
    msgdict["salt"] = 0
    msgdict["type"] = int(msgid)
    msgdict["cksum"] = 0
    msgdict["targetid"] = int(lampid)
    msgdict["sourceid"] = 32767
    t = maindict["structs"][msgtype["msgclass"]]
    s = '"'
    for x in range(len(t["keys"])):
        key = t["keys"][x]
        v = eval(key["type"]+"("+str(msgdict[key["name"]])+")")
        s += "," + str(v)
    bytestring = eval('struct.pack("' + t["pack"] + s+")")
    return bytestring
