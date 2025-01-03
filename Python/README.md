Project using GRIDEYE AMG8833 64 pixels sensor for Fall Detection
Base Station: baseStn_01.py
Develop on: VSCode/Python
C:>python -m venv .venv  				# Create a new virtual environment
C:>.venv\Scripts\activate 				# Activate it (Windows)
C:>pip install -r requirements.txt  	# Install dependencies
To execute the application:
C:>python .venv\baseStn_01.py

Additional notes:
 - option to alter the IP address of base station:
   a) edit it in baseStn_01.py
   b) from command prompt, use 'netsh interface ipv4 set address name="Wi-Fi" static 192.168.1.5 255.255.255.0 192.168.1.1'
      where 192.168.1.5 is the desired IP Address and 192.168.1.1 the Default Gateway
 - to break a running application (esp. when unable to do so with Ctrl-C),
   From command prompt:
    a) use 'netstat -ano | findstr :8080' to find out the PROCESSID
    b) run 'taskkill /PID PROCESSID /F' to stop it
Released by KWWong / 01Jan2025
