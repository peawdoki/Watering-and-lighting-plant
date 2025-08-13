def show_wifi_info():
    try:
        with open("datapae.txt", "r") as f:
            line = f.readline().strip()
            parts = line.split(",")  

        ssid = parts[6]      
        password = parts[7]  

        print("SSID:", ssid)
        print("Key:", password)

    except Exception as e:
        print("Error reading datapae.txt:", e)
        
show_wifi_info()