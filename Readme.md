Project using GRIDEYE AMG8833 64 pixels sensor for Fall Detection
Client: espressif32 ESP32-S3 with WIFI
Base Station: PC-based with WIFI
Develop on: VSCode/PlatformIO/C++, VSCode/Python
AMG8833 library used: https://github.com/adafruit/Adafruit_AMG88xx
Released by KWWong / 01Jan2025
Version 1.0 features.
1. Poll and obtain 64-bytes data from GRIDEYE AMG8833 via I2C, at 100ms interval i.e. 10fps
2. WIFI comm between client & server via router; temporary disable Firewall on server if connection fails
3. Client initiates "Status" to get server attention
4. UI on base station prompts for csv file name & number of seconds (1..9) to capture sensor data frames
5. Base station queries client for sensor data with "VIDEO" follows by number of seconds (1..9) to capture
6. Client auto-restarts if it loses contact with base station for a pre-determined interval (60s); this also allows 
   it to auto-connect if base station restarts
Tested: client: gridClnt_01.cpp; server: baseStn_01.py