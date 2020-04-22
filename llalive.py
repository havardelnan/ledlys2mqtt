import socket
import struct
LYSPORT=15240
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
#client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

client.bind(("", LYSPORT))
while True:
    data, addr = client.recvfrom(1024)
    print("received message:")
    #print(data)
    #result=struct.unpack("LBBHH9BfHLf4LiIB3f2H4f2I34s34sf5IB4I",data)
    result=list(struct.unpack("IBBHH9BfHIf4IiIB3f2H4f2I34s34sf5IB4I",data))
    result[37] = str(result[37].decode("utf-8")).rstrip('\x00')
    result[36] = (result[36].decode("utf-8")).rstrip('\x00')
    print("Lamp: "+ str(result[4]))
    print("Name: "+result[37])
    print(result)


 