Project using GRIDEYE AMG8833 64 pixels sensor for Fall Detection
Client: gridClnt_01.cpp
Develop on: VSCode/PlatformIO/C++
env = ESP32-S3-devkitm-1
platform = espressif32
board = esp32-s3-devkitm-1
framework = arduino
AMG8833 library used: https://github.com/adafruit/Adafruit_AMG88xx

Additional notes:
 - as the client refers to the hard-coded IP address of base station, it will be eaiser to fix the IP address of the base station
   e.g. run 'netsh interface ipv4 set address name="Wi-Fi" static 192.168.1.5 255.255.255.0 192.168.1.1' from command prompt of the
   base station, where 192.168.1.5 is the desired IP Address and 192.168.1.1 the Default Gateway
 - as its placement may be out of reach, it will be easier to wait out for the client to auto-restart when the base station application 
   restarts
Released by KWWong / 01Jan2025
