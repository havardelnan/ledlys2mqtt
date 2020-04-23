import re
import sys
import struct

NAMESIZE=34
MAXGROUPS=100
MAXPEERS=100
MAXBUTTS=8
MAXSCENES=16
MAXTIMES=20

inputstruct = '''struct msg_report_t {
   struct hdr_t hdr;                   //I
   uint16_t peerid;                    //E*
   uint32_t serial;                    //E
   uint8_t stwversion[2];              //I
   uint32_t ipaddr;                    //S
   uint16_t voltage;                   //S
   char lampname[NAMESIZE];            //E
   uint8_t currentIntensityPct;        //S* current light intensity
   uint8_t ngroups;                    //E
   uint8_t groups[MAXGROUPS];          //E
   uint32_t seconds;                   //S
   uint8_t lampMode;                   //E pwm1 and pwm2 mode
   uint8_t currentTemperaturePct;      //S* current light temperature
   uint8_t defaultTemperaturePct;      //E default light temperature
   uint8_t isswitch;                   //E
   uint8_t fadewarm;                   //E
   uint8_t minpct;                     //E
   uint8_t maxpct;                     //E
   uint16_t offdelay;                  //E
   uint8_t npeers;                     //E
   uint16_t peers_id[MAXPEERS];        //E
   uint8_t peers_wantedpct[MAXPEERS];  //E
   uint8_t peers_suggestpct[MAXPEERS]; //S
   uint8_t scalepct;                   //E
   uint8_t upspeed;                    //E
   uint8_t downspeed;                  //E
   uint8_t opspeed;                    //E
   uint16_t opgroup[MAXBUTTS];         //E
   uint8_t opmode[MAXBUTTS];           //E
   uint16_t optimeout[MAXBUTTS];       //E
   // new stuff in 2.6
   uint16_t UNUSED2[MAXBUTTS];         //U
   uint32_t XXXreanimates;             //U
   uint8_t nscenes;                    //E
   uint16_t scenes_id[MAXSCENES];      //E 14 bits of scene number no, SCN_BITS but RELSCN
   uint8_t scenes_pct[MAXSCENES];      //E
   uint8_t scenes_color[MAXSCENES];    //E
   uint8_t defaultIntensityPct;        //E default light intensity
   float powernow;                     //I
   float powerkWh;                     //I
   uint16_t powerdays;                 //E
   uint32_t powersecs;                 //S
   float powerwatts;                   //E
   uint32_t presencedetects;           //S
   // new in 3.1
   int32_t rssi;                       //I wifi signal strength
   float rtc_latf;                     //E latitude
   float rtc_lonf;                     //E longitude
   uint8_t rtc_days[MAXTIMES];         //E bitmask of days
   uint16_t rtc_time[MAXTIMES];        //E hours, minutes
   uint16_t rtc_date[MAXTIMES];        //E month, day
   uint16_t rtc_scene[MAXTIMES];       //E which scene
   float rtc_timezone;                 //E
   // new in 3.3
   uint32_t presenceswitch;            //S number of clicks on present switch
   uint32_t presencems;                //I ms since last presence detect
   uint8_t hdwversion[2];              //I
   uint32_t presentI2C;                //I i2c stuff found
   uint8_t presenceHistory[64];        //I number of presence detects each minute for the last hour
   uint8_t presenceSecs;               //S number of seconds in the latest history entry
   // sensors
   float ambientLight;                 //S
   float airTemperature;               //S
   float airHumidity;                  //S
   uint16_t airCO2ppm;                 //S
   uint16_t airTVOCppb;                //S
   float airPressure;                  //S
   float pm2;
   float pm10;
   float s4;                           //U spare sensors
   uint32_t clkDate;                   //I yyyymmdd
   uint16_t clkTime;                   //I hhmm
   uint16_t clkRise;                   //I sunrise hhmm
   uint16_t clkSet;                    //I sunset hhmm
   // new in 3.4
   uint16_t opOnScene[MAXBUTTS];       //E toggle/on scene number, 0 is none
   uint16_t opOffScene[MAXBUTTS];      //E toggle/off scene number, 0 is none
   uint8_t boardType;                  //I
   uint8_t X99;                        //U
   uint16_t presence5Min;              //S
   uint8_t swapNS;         // true if swapping NS on alarm
   uint16_t mAmin;         // minimum mA before lamp starts to glow
   uint16_t mAmax;         // maximum mA the lamp can take
   // new in 3.7
   char ssid[32];
   PAD
};'''

maindict = {}
translatedict={"uint8_t" : "B","uint16_t" : "H", "uint32_t" : "I","float" : "f","int8_t" : "b","int16_t" : "h","int32_t":"i", "char": "s"}
for l in inputstruct.splitlines():
    l = l.strip()

    pattern = '^struct (.*)\{$'
    result = re.match(pattern, l)

    if l[0] == "/" :
        print("These are not the lines you are looking for: " + l)
    elif result:
        currentstruct = str(result.group(1)).strip()
        maindict[currentstruct] = {}
        maindict[currentstruct]["keys"] = ["salt","type","cksum","targetid","sourceid"]
        maindict[currentstruct]["pack"] = "IBBHHxx"
    else:
        pattern = '^([a-zA-Z0-9_]+) ([a-zA-Z0-9_]+)(?:\[([a-zA-Z0-9_]*)\])?\;(.*)$'
        result2 = re.match(pattern, l)
        if result2:
            if result2.group(1) in  translatedict:
                if result2.group(3) :
                    maindict[currentstruct]["pack"] += str(int(eval(result2.group(3))))
                maindict[currentstruct]["pack"] += translatedict[result2.group(1)]
            else:
                print("datatype not handled: " + result2.group(1))
            if result2.group(3) and result2.group(1) != "char":
                for x in range(int(eval(result2.group(3)))):
                    maindict[currentstruct]["keys"].append(str(result2.group(2))+"_"+str(x+1))
            else:
                maindict[currentstruct]["keys"].append(result2.group(2))
        else:
            print("not handled:" + l)

#print(maindict)
testreport = b'\x00\x00\x00\x00\n\x00\x00\x00\xacP\x00\x00\xacP\x00\x00\xac\xd05\x02\x04\x02\x00\x00\n\x14\x00\x9c\xb6\x11Verksted Benk\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\r\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04r\x01\x00\x016\x00\x01\x00\x00d\x00\x08\x00\x01\x00\xacP\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00d\x05\nc\x00\x80\x00\x80\x00\x80\x00\x80\x00\x80\x00\x80\x00\x80\x00\x80\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00V\xf8\xbb<\x01\x00\x00\x00\x84 \x00\x00\x00\x00 A\x00\x00\x00\x00\xe9\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xaf&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\xae&\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\x00\x00\x00\x00\x00\x00\x00\xd7^\xa5\x05\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00+\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x85\x99,\x01\x00\x00\x00\x00\x00\x00\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x00\xc0\x02\x00\x00\x00\x00\x00\x00\x00d\x00sarve\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
#print(len(testreport))
result = list(struct.unpack(maindict['msg_report_t']["pack"],testreport))
result=dict(zip(maindict['msg_report_t']["keys"], result))
print(result)