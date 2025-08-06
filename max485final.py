from machine import UART, Pin
from time import sleep

# === กำหนดขา DE/RE สำหรับ MAX485 ===
de = Pin(18, Pin.OUT)
re = Pin(5, Pin.OUT)

# === กำหนด UART2 ===
uart2 = UART(2, baudrate=4800, tx=17, rx=16, bits=8, parity=None, stop=1)

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

    # --- เซนเซอร์แสง (Slave ID 7) --- อ่านค่าแสง 2 รีจิสเตอร์
    print("อ่านเซนเซอร์แสง")
    req_light = [7, 3, 0x01, 0xFA, 0x00, 0x02]
    raw3 = send_modbus_request(req_light)
    light_value = parse_light_data(raw3)
    if light_value is not None:
        print("Light Intensity:", light_value)
    else:
        print("อ่านแสงไม่สำเร็จ")

    sleep(3)
    

    
    
    
