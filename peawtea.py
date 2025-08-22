from lcd_api import LcdApi
from i2c_lcd import I2cLcd
from ds3231 import DS3231
import os
import network
import ufirebase as firebase
from machine import Pin, ADC, PWM, SoftI2C
from time import sleep
import gc
gc.collect()

# === Wi-Fi ===
ssid = 'LAPTOP-R0A00K9B 7400'
password = 'U5r04*35'

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

# === Firebase ===
# firebase.setURL("https://led-control1-418f2-default-rtdb.asia-southeast1.firebasedatabase.app/")
firebase.setURL("https://test-dcf94-default-rtdb.asia-southeast1.firebasedatabase.app/")

data_control = ['1','7','30','0','16','30','0','1','8','30','0','18','30','0','0','0','0','0','10000','50000','40','70','536','36','50','1000','50','Danny','password']
# control_mode_motor, start_time_motor, start_time_motor, start_time_motor, stop_time_motor, stop_time_motor, stop_time_motor,
# control_mode_pump, start_time_pump, start_time_pump, start_time_pump, stop_time_pump, stop_time_pump, stop_time_pump,
# motorStatus, motorState, pumpStatus, pumpState, start_light, stop_light, start_humid_d, stop_humid_d, pump_power, temp, humid, lux, humid_d,
# ssid, password

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=10000)
ds = DS3231(i2c)

def set_time(time_list): 
    time_set_list = list(time_list)
    time_set_list[7] = time_set_list[3]
    time_set_list.pop(3)
    time_set_tuple = tuple(time_set_list)
    ds.datetime(time_set_tuple) 

def file_operation(mode):
    global data_control
    
    f = open('data1.txt', mode)
    if mode == 'r':
        data_str = f.readline()
        data_str = data_str[:len(data_str) - 1]    
        data_control = data_str.split(",")
    elif mode == 'w':
        data_str = ""     
        for x in data_control:
           data_str = data_str + str(x) + ','  # แปลง x เป็น string ก่อนเชื่อม
        data_str = data_str[:-1]
        data_str = data_str + '\n'     
        f.write(data_str)
    f.close()

command_str = '0'



def operation_web_comm():
    global data_control, command_str

    web_str = ""

    # ป้องกันกรณี command_str ว่าง
    if not command_str:
        return None

    # ===== Date/Time (ต้องมี ds และ set_time ในโปรเจกต์) =====
    if command_str[0] == '1':  # read date
        datetime1 = ds.datetime()   # (year, month, mday, weekday, hour, minute, second, 0)
        web_str = '1,' + str(datetime1[0]) + "," + str(datetime1[1]) + "," + str(datetime1[2]) + "," + str(datetime1[3])

    elif command_str[0] == '2':  # set date
        web_str = command_str.split(",")
        time_value = ds.datetime()
        time_list = list(time_value)
        for i in range(3):
            time_list[i] = int(web_str[i+1])
        set_time(time_list)
        web_str = "OK!"

    elif command_str[0] == '3':  # read time
        datetime1 = ds.datetime()
        web_str = '3'
        for i in range(4, 7):
            web_str = web_str + ',' + str(datetime1[i])

    elif command_str[0] == '4':  # set time
        web_str = command_str.split(",")
        time_value = ds.datetime()
        time_list = list(time_value)
        for i in range(3):
            time_list[i+4] = int(web_str[i+1])
        set_time(time_list)
        web_str = "OK!"

    # ===== Wi-Fi show/change =====
    elif command_str[0] == '5':  # Show wifi
        file_operation('r')
        web_str = '5,' + data_control[27] + "," + data_control[28]
        
    elif command_str[0] == '6':  # Change wifi
        web_str = command_str.split(",")
        data_control[27] = web_str[1]
        data_control[28] = web_str[2]
        file_operation('w')
        web_str = "OK!"
    elif command_str[0] == '7':   
        connect_wifi()
        web_str = "OK!"

    # ===== Device control/status (ต้องมี devs เป็น list ของ Pin) =====
    elif command_str[0] == '8':  # Dev ON/OFF
        file_operation('r')
        web_str = '8,' + data_control[23] + "," + data_control[24] + "," + data_control[26] + "," + data_control[25]

    elif command_str[0] == '9':  # Dev Status
        file_operation('r')
        web_str = '9,' + data_control[0] + "," + data_control[7]

    # ===== Power / Control flags =====
    elif command_str[0] == 'A':  # Show Power
        web_str = command_str.split(",")
        data_control[0] = web_str[1]
        file_operation('w')
        web_str = "OK!"

    elif command_str[0] == 'B':  # Control ON/OFF
        web_str = command_str.split(",")
        data_control[7] = web_str[1]
        file_operation('w')
        web_str = "OK!"

    elif command_str[0] == 'C':  # Show Control Status
        web_str = command_str.split(",")        
        data_control[15] = web_str[1]
        file_operation('w')
        web_str = "OK!"

    elif command_str[0] == 'D':  # Set Con Value (timer block 8 ช่อง)
        web_str = command_str.split(",")        
        data_control[17] = web_str[1]
        file_operation('w')
        web_str = "OK!"

    elif command_str[0] == 'E':  # Show Con Value
        file_operation('r')
        web_str = 'E,' + data_control[14] + "," + data_control[16]
        
    elif command_str[0] == 'F':  # Save Data ON/OFF
        web_str = command_str.split(",")
        data_control[18] = web_str[1]
        data_control[19] = web_str[2]
        file_operation('w')
        web_str = "OK!"

    elif command_str[0] == 'G':  # Save Data Status
        web_str = command_str.split(",")
        data_control[1] = web_str[1]
        data_control[2] = web_str[2]
        data_control[3] = web_str[3]
        data_control[4] = web_str[4]
        data_control[5] = web_str[5]
        data_control[6] = web_str[6]
        file_operation('w')
        web_str = "OK!"
        
    elif command_str[0] == 'H':
        web_str = command_str.split(",")
        data_control[20] = web_str[1]
        data_control[21] = web_str[2]
        file_operation('w')
        web_str = "OK!"
    
    elif command_str[0] == 'I':  # Save Data Status
        web_str = command_str.split(",")
        data_control[8] = web_str[1]
        data_control[9] = web_str[2]
        data_control[10] = web_str[3]
        data_control[11] = web_str[4]
        data_control[12] = web_str[5]
        data_control[13] = web_str[6]
        file_operation('w')
        web_str = "OK!"
        
    elif command_str[0] == 'J':  # Dev ON/OFF
        file_operation('r')
        web_str = 'J,' + data_control[18] + "," + data_control[19] + "," + data_control[1] + "," + data_control[2] + "," + data_control[3] + "," + data_control[4] + "," + data_control[5] + "," + data_control[26]
        
    elif command_str[0] == 'K':  # Dev ON/OFF
        file_operation('r')
        web_str = 'K,' + data_control[20] + "," + data_control[21] + "," + data_control[8] + "," + data_control[9] + "," + data_control[10] + "," + data_control[11] + "," + data_control[12] + "," + data_control[13]   
    
    else:
        # คำสั่งไม่รู้จัก
        web_str = None

    return web_str


# ===== Main Loop =====
str_data = ""
while True:
    # ดึงคำสั่งจาก Firebase
    firebase.get("comm", "var1", bg=0)
    command_str = firebase.var1 if hasattr(firebase, "var1") else ""

    # ถ้ามีคำสั่ง และไม่ใช่ "0"
    if command_str and command_str[0] != '0':
        print("command: " + command_str)

        # ประมวลผล
        str_read = operation_web_comm()
        while str_read is None:
            sleep(0.1)
            str_read = operation_web_comm()

        # ส่งผลลัพธ์ไปที่ Firebase
        try:
            print(str_read)
            firebase.put("esp", str_read, id=0)
            sleep(2)
        except:
            pass

        command_str = '0'
        # รีเซ็ตค่าบน Firebase เป็น "0"
        try:
            firebase.put("comm", "0", id=0)
            firebase.put("esp", "", id=0)
            sleep(2)
        except:
            pass

    sleep(2)
