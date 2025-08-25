import os
import network
import ufirebase as firebase
from machine import UART
from time import sleep
import gc
gc.collect()

uart1 = UART(1, baudrate=115200, tx=19, rx=32)


ssid = 'LAPTOP-R0A00K9B 7400'
password = 'U5r04*35'
#Connect to Wifi
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(ssid, password)
print("Connecting to Wi-Fi...")
while not wifi.isconnected():
  print(".", end="")
  sleep(1)
print()
ipaddr, netmask, gateway, dns = wifi.ifconfig()
print("Connected with IP address :", ipaddr)

firebase.setURL("https://test-dcf94-default-rtdb.asia-southeast1.firebasedatabase.app/")

str_data = ""
command_str = '0'

while True:
    firebase.get("comm", "var1", bg=0)
    command_str = firebase.var1    
    
    if command_str[0] != '0':
        print("command: "+ command_str)
        uart1.write(command_str)
        command_str = '0'        
        firebase.put("comm", "0", id=0)        
        
        sleep(3)
        
        str_read = uart1.read()
        while str_read == None:
            str_read = uart1.read()
        # Convert the byte string to a string using the decode() method
        str_read = str_read.decode("utf-8")

        # Print the decoded string               
        print(str_read)
                
        command_str = '0'
        try:            
            firebase.put("esp", str_read, id=0)                
            sleep(5)   #8
        except:
            pass
  
    sleep(2)

