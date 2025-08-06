import network
import time
import urequests
from machine import UART, Pin, SoftI2C
from time import sleep
from lcd_api import LcdApi
from i2c_lcd import I2cLcd

# === กำหนดขา DE/RE สำหรับ MAX485 ===
de = Pin(18, Pin.OUT)
re = Pin(5, Pin.OUT)

# === กำหนด UART2 ===
uart2 = UART(2, baudrate=4800, tx=17, rx=16, bits=8, parity=None, stop=1)

# === เชื่อมต่อ WiFi ===
def connect_wifi(ssid, password, timeout=15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(ssid, password)
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                print('WiFi connection timeout')
                return False
            time.sleep(1)
    print('WiFi connected:', wlan.ifconfig()[0])
    return True

# === Firebase ===
SSID = 'PEAW_DOKI'
PASSWORD = 'peaw33140'
FIREBASE_URL = 'https://test-dcf94-default-rtdb.asia-southeast1.firebasedatabase.app/'

def send_data(path, data):
    url = FIREBASE_URL + path + '.json'
    try:
        response = urequests.put(url, json=data)
        response.close()
        print("Firebase Sent:", data)
    except Exception as e:
        print("Send Error:", e)

def write_data_to_file(data):
    with open('data.txt','w') as f:
        for key, value in data.items():
            f.write(f"{key}:{value}\n")

def read_data_from_file(filename):
    data = {}
    with open(filename, 'r') as f:
        for line in f:
            key, value = line.strip().split(':')
            data[key] = value
    return data

readData = read_data_from_file('data.txt')


# === ฟังก์ชัน CRC16 Modbus RTU ===
def crc16(data):
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc

# === อ่านคำสั่งจาก Firebase ===
def read_command():
    url = FIREBASE_URL + 'sensor_data/comd.json'
    try:
        response = urequests.get(url)
        data = response.json()
        
        # ดีบักข้อมูลที่ได้รับ
        print("Data from Firebase:", data)
        
        # ถ้า data เป็นตัวเลขหรือข้อความที่ตรงกับคำสั่ง
        if data:
            return {'comd': str(data)}  # แปลงค่าให้เป็น string
        else:
            print("No valid command in the data.")
            return None
    except Exception as e:
        print("Error reading Firebase:", e)
        return None

# === ประมวลผลคำสั่ง ===
def execute_command(cmd):
    # แปลง cmd เป็นสตริงถ้าค่าที่ได้รับเป็นตัวเลข
    if isinstance(cmd, int):
        cmd = str(cmd)

    if cmd == '1':  # ถ้าคำสั่งคือ '1' ให้ดึงข้อมูลอุณหภูมิและความชื้น
        result = {'esp32': f"Temp: {temp1}C, Humidity: {humi1}%"}

    elif cmd == '2':  # ถ้าคำสั่งคือ '2' ให้ดึงข้อมูลแสง
        result = {'esp32': f"Light Intensity: {light_value}"}
        
    elif cmd == '3':  
        result = {'esp32': f"HumiditySoid: {humi2}%"}
    
    else:
        result = {'esp32': "Invalid Command"}

    # รอ 3 วินาทีแล้วเคลียร์ค่าใน Firebase ให้เป็นค่าว่าง
    time.sleep(3)
    send_data('sensor_data/comd', "")  # รีเซ็ตค่าคำสั่งให้เป็นค่าว่าง
    return result

# === ส่งคำสั่งและรับข้อมูลผ่าน MAX485 ===
def send_modbus_request(request):
    crc = crc16(request)
    request += [crc & 0xFF, (crc >> 8) & 0xFF]

    de.value(1)
    re.value(1)
    sleep(0.01)

    uart2.write(bytes(request))
    sleep(0.02)

    de.value(0)
    re.value(0)
    sleep(0.1)

    data = uart2.read(20)
    print("RECV:", data)
    return data

# === ฟังก์ชันแยกข้อมูล ===
def parse_two_values(data):
    if data and len(data) >= 9:
        received_crc = (data[-1] << 8) + data[-2]
        calculated_crc = crc16(data[:-2])
        if received_crc != calculated_crc:
            print("CRC ไม่ถูกต้อง!")
            return None, None

        humi = (data[3] << 8) | data[4]
        temp = (data[5] << 8) | data[6]
        return round(temp * 0.1, 1), round(humi * 0.1, 1)
    return None, None

def parse_three_values(data):
    if data and len(data) >= 11:
        received_crc = (data[-1] << 8) + data[-2]
        calculated_crc = crc16(data[:-2])
        if received_crc != calculated_crc:
            print("CRC ไม่ถูกต้อง!")
            return None, None, None

        humi = (data[3] << 8) | data[4]
        temp = (data[5] << 8) | data[6]
        ec   = (data[7] << 8) | data[8]
        return round(temp * 0.1, 1), round(humi * 0.1, 1), round(ec * 0.1, 1)
    return None, None, None

def parse_light_data(data):
    if data and len(data) >= 9:
        received_crc = (data[-1] << 8) + data[-2]
        calculated_crc = crc16(data[:-2])
        if received_crc != calculated_crc:
            print("CRC ผิด")
            return None

        high = (data[3] << 8) + data[4]
        low  = (data[5] << 8) + data[6]
        value = (high << 16) + low
        return value
    else:
        print("ข้อมูลไม่ครบ")
        return None
    
# === โปรแกรมหลัก ===
connect_wifi(SSID, PASSWORD)


# === Loop อ่านเซนเซอร์ทั้งหมด ===
while True:
    # --- SN-300-BYH (Slave ID 2) --- อ่าน 2 ค่า
    print("อ่าน SN-300-BYH")
    req_byh = [2, 3, 0, 0, 0, 2]
    raw1 = send_modbus_request(req_byh)
    temp1, humi1 = parse_two_values(raw1)
    if temp1 is not None:
        print("Temp: {:.1f} °C, Humidity: {:.1f} %".format(temp1, humi1))
    else:
        print("อ่าน SN-300-BYH ไม่สำเร็จ")

    sleep(1)

    # --- SN-3000-ECTH (Slave ID 1) --- อ่าน 3 ค่า
    print("อ่าน SN-3000-ECTH")
    req_ecth = [1, 3, 0, 0, 0, 3]
    raw2 = send_modbus_request(req_ecth)
    temp2, humi2, ec2 = parse_three_values(raw2)
    if temp2 is not None:
        print("Temp: {:.1f} °C, Humidity: {:.1f} %, EC: {:.1f} mS/cm".format(temp2, humi2, ec2))
    else:
        print("อ่าน SN-3000-ECTH ไม่สำเร็จ")

    sleep(1)

    # --- เซนเซอร์แสง (Slave ID 3) --- อ่านค่าแสง 2 รีจิสเตอร์
    print("อ่านเซนเซอร์แสง")
    req_light = [7, 3, 0x01, 0xFA, 0x00, 0x02]
    raw3 = send_modbus_request(req_light)
    light_value = parse_light_data(raw3)
    if light_value is not None:
        print("Light Intensity:", light_value)
    else:
        print("อ่านแสงไม่สำเร็จ")

    sleep(3)
    
    data = {'temp': temp1, 'humi': humi1, 'lux': light_value, 'humisoid': humi2, }
    write_data_to_file(data)
    
    cmd_data = read_command()
    if cmd_data:
        print("Received command:", cmd_data)  # เพิ่มการแสดงผลคำสั่งที่ได้รับ
        if cmd_data['comd']:
            command = cmd_data['comd']
            print("Command to execute:", command)  # แสดงคำสั่งที่ได้รับจาก Firebase
            output = execute_command(command)
            send_data('sensor_data/esp32', output)  # ส่งผลลัพธ์กลับไปที่ Firebase
        else:
            print("No command to execute.")
    time.sleep(1)


