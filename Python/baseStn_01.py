import socket
import select
import struct
import time
import threading
import csv

#Base station to capture GRIDEYE AMG8833 64-pixels frames for Fall Detection
#VSCode
#Released by KWWong / 01Jan2025
#Note.
# 1. WIFI setup - confirm & edit (refer #kwkwkwk1) this base station IP address before use
# 2. Base station to respond to client with "HELLO" upon client initiates connect using "Status"
# 3. UI prompts user to enter csv filename & number of secs (1..9) of frames (at 10fps) to capture
# 4. Send query starting with "VIDEO" follows by number of seconds (1..9) to client to capture sensor data
# 5. Base station captures arriving sensor data triggered by 8-bytes header "DATA: xx"
# 6. Client will responds accordingly as long as connection with base station stays
# Tested as server with gridClnt_01.cpp on client.

csvf = None
WF_status = "HELLO"
framecnt = 0
clntEnable = threading.Event()  # Create an Event object
clntEnable.clear()  # Set it to True initially

# Define the dimensions of the AMG88xx sensor
sensor_width = 8
sensor_height = 8

# Server Configuration
HOST = '192.168.79.5'  #kwkwkw1 Listen on all available interfaces
PORT = 8080       # Port to listen on
BUFFER_SIZE = 1024
posefilecsv = ""

# Storage for received data
received_packets = {}

def prompt_UI(client_socket):
    global csvf, posefilecsv, clntEnable, framecnt
    # Send commands to client
    posefilecsv = input("Enter pose filename: ")
    csvf=open(posefilecsv,'a')
    while True:
        frameduration = input("Enter frame duration (1..9)s : ")
        if frameduration.isdigit():
            framecnt = int(frameduration) * 10  		# Assuming 10 frames per second
            break
    ack_message = "VIDEO" + frameduration		#f"OK{frameduration}OK"
    client_socket.sendall(ack_message.encode('utf-8') + b'\n')  # Send command to client #kw24dec20a + b'\n'
    clntEnable.set()
    #print("clntEnable set. Returning from prompt_UI.")

def data_available(client_socket):
    ready_to_read, _, _ = select.select([client_socket], [], [], 0)
    return bool(ready_to_read)

# Handle client communication
def handle_client(client_socket, client_address):
    global csvf, WF_status, posefilecsv, clntEnable, framecnt
    cmd_done = True
    print(f"New connection from {client_address}")
    try:
        while True:
            if clntEnable.is_set():
            # Read a line or chunk from the client
                if data_available(client_socket):
                    print("Waiting for client connection...")
                    header = client_socket.recv(8).decode('utf-8').strip()  # Decode for text from client; 8 bytes for header
                    print(f"HEADER received: {header}")
                    if not header:  # Client disconnected
                        print(f"Client {client_address} disconnected")
                    if header.startswith("CMD:"):
                        # Process command
                        command = header.split(":", 1)[1].strip()  # Extract the command
                        print(f"Received command from {client_address}: {command}")

                        if (command == "READY") and (cmd_done == True):
                            # Prompt after READY command
                            prompt_UI(client_socket)
                            cmd_done = False
                        elif command == "DONE":
                            print(f"Client {client_address} indicates transaction done.")
                            # client_socket.sendall(b"Transaction complete.")
                            csvf.close()
                            cmd_done = True
                        else:
                            print(f"Unknown command: {command}")
                            # client_socket.sendall(b"ERROR: Unknown command")

                    elif header.startswith("DATA:"):
                        # Process binary data
                        try:
                            # Extract the length of the incoming data
                            length = int(header.split(":", 1)[1].strip())
                            print(f"Preparing to receive {length} bytes of data from {client_address}")

                            # Receive the specified length of binary data
                            binary_data = client_socket.recv(length*4)
                            #print("Raw bytes:", binary_data.hex())
                            expected_size = 65 * 4  # 65 floats, each 4 bytes
                            if len(binary_data) != expected_size:
                                print(f"Incomplete data: Expected {expected_size} bytes, got {len(binary_data)} bytes")
                            print("Length:", len(binary_data))
                            float_array = struct.unpack('<64f', binary_data[:256])
                            float_seqno = struct.unpack('<1f', binary_data[256:])

                            print(float_array)
                            print(float_seqno)
                            # Open the CSV file in append mode to save multiple entries
                            with open(posefilecsv, mode='a', newline='') as csv_file:
                                csv_writer = csv.writer(csv_file)
                                # Write the sequence number and float array to the file
                                csv_writer.writerow(list(float_seqno))  # Sequence number first, followed by the float array
                                csv_writer.writerow(list(float_array))  # Sequence number first, followed by the float array
                                print(f"Data saved to {posefilecsv}")
                                framecnt = framecnt - 1
                                if framecnt == 0:
                                    clntEnable.clear()
                                    #print(f"clntEnable after framecnt=0: {clntEnable}.")
                        except ValueError:
                            print("Invalid DATA header")
                            #client_socket.sendall(b"ERROR: Invalid DATA header")
                    else:      
                        if header.startswith("Status"):
                            client_socket.sendall(WF_status.encode('utf-8') + b'\n')  # Send status to client, HELLO if 1st time, READY subsequently
                            if WF_status == "HELLO":
                                WF_status = "READY"
                                clntEnable.clear()
                                #print(f"clntEnable after HELLO: {clntEnable}.")
                        else:
                            if header == b'':
                                print(f"Empty header from {client_address}: {header}")
                            else:
                                print(f"Unexpected message from {client_address}: {header}")
                            #client_socket.sendall(b"ERROR: Invalid message format")

    except (ConnectionResetError, BrokenPipeError):
        print(f"Connection with {client_address} lost")
    finally:
        client_socket.close()
        print(f"Connection with {client_address} closed")

# Start the server
def start_server():
    global clntEnable
    print(f"Starting server on {HOST}:{PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_buf_size = server_socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        print(f"Receive buffer size: {recv_buf_size}")

        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print("Server is listening for incoming connections.")

        try:
            client_socket, client_address = server_socket.accept()
            print(f"Connection established with {client_address}.")
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            print(f"Thread started for {client_address}.")
            clntEnable.set()
            client_thread.daemon = True
            client_thread.start()
            while client_thread.is_alive():
			  # Prompt for user to input csv file & sensor frame capture timing in secs
                if (not clntEnable.is_set()):
                    #print(f"clntEnable before prompt_UI: {clntEnable}.")
                    prompt_UI(client_socket)

        except KeyboardInterrupt:
            print("\nKeyBD1 shut down Server.")
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            server_socket.close()
            print("Server Socket Close.")

if __name__ == "__main__":
    try:
        start_server()
    except Exception as e:
        print(f"Server error: {e}")    
