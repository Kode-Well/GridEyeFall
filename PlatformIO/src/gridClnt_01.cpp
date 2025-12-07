//GRIDEYE AMG8833 64 pixels sensor for Fall Detection
//PlatformIO /VSCode
//env = ESP32-S3-devkitm-1
//platform = espressif32
//board = esp32-s3-devkitm-1
//framework = arduino
//AMG8833 library = https://github.com/adafruit/Adafruit_AMG88xx
//Released by KWWong / 01Jan2025
//Note.
// 1. WIFI setup - confirm & edit (refer //kwkwkwk1) the base station IP address, ssid, password before use
// 2. Software will auto-restart after it loses contact with base station after a pre-determined interval (60s)
// 3. Modify pin number for I2C to sensor if different from current set up of SDA_PIN=21 & SCL_PIN=20
// 4. Base station to respond to client with "HELLO" upon client initiates connect using "Status"
// 5. Query starting with "VIDEO" follows by number of seconds (1..9) to capture sensor data is sent by base station
// 6. 8-bytes header "DATA: xx" is used to inform base station of arriving sensor data
// Tested as client with baseStn_01.py on server.

#include <Arduino.h>
#include <WiFi.h>
#include <Adafruit_AMG88xx.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

const char* ssid = "ssid";							//kwkwkw1 Replace with your server's SSID
const char* password = "password";			//kwkwkw1 Replace with your server's PASSWORD
const char* serverIP = "192.168.0.102"; 	//kwkwkw1 Replace with your server's IP address
const int serverPort = 8080;
const int WFstatusInterval = 20000; 		// WiFi check for status interval (ms) before warm restart
uint32_t lastWFTime = 0;

WiFiClient client;
Adafruit_AMG88xx amg;

//GRIDEYE I2C for ESP32-S3
#define SDA_PIN 21	
#define SCL_PIN 22

const int lightPin = 13;
const int errorLightPin = 14;
const int recordingLightPin = 15;

// Buffer and sequence numbers
const int payloadsz = 65;									// 64 float bytes of Grideye data + 1 float byte of seq no
const int bufferSize = 10;               // buffer size for 1s of 10 frames
float buffer[bufferSize][payloadsz];    // Packet buffer (1 float byte sequence + 64 float bytes)
uint32_t currentSeqNum = 0;

// Function Prototypes
void readI2C();
bool sendPacket(float* data, size_t size);
String svr_reply = "";

void setup() {
	Serial.begin(115200);
	Serial.println(F("AMG88xx pixels"));
	delay(200);

	// No need to explicitly define I2C pins for standard Arduino boards
	Wire.begin(SDA_PIN, SCL_PIN); 		// Automatically uses the correct I2C pins

	bool status = false;
	pinMode(42, INPUT_PULLUP);
	while (status == false)
	{
		status = amg.begin();
		if (status == false) {
			Serial.println("Could not find a valid AMG88xx sensor, check wiring!");
			//while (1);
		}

		Serial.println("-- AMG88xx sensor --");
		Serial.println();
		delay(100); // let sensor boot up
	}

	Serial.println("AMG88xx initialized!");

	// Debugging Lights
	turnOnInitLight();
	turnOffRecordingLight();
	turnOffErrorLight();

	// Connect to Wi-Fi
	WiFi.begin(ssid, password);
	while (WiFi.status() != WL_CONNECTED) {
		delay(500);
		Serial.print(".");
	}
	Serial.println("\nWi-Fi connected.");
	Serial.println(WiFi.localIP());

	// Wait for server connection (handshake)
	while (!client.connect(serverIP, serverPort)) {
		Serial.println("Waiting for server...");
		delay(1000); // Retry every second
	}
	Serial.println("Connected to server!");

	// Send "Status" message to query server
	client.print("Status");
	client.flush();
	Serial.println("Sent First Status query to server");
	while (client.connected()) {
		if (client.available()) {
			svr_reply = client.readStringUntil('\n'); 	// Read until newline
			svr_reply.trim();														//clear any extras
			Serial.println("svr_reply:" + svr_reply);
			if (svr_reply != "HELLO") {
				Serial.println("Base station not from starting stage, restarting..");
				client.stop();
				esp_restart(); // Perform a warm restart
			}
			else {
				Serial.println("Base station ready, proceed..");
				break;
			}
		}
	}
}

void loop() {
	byte noConnectCnt = 0;
	byte reqframeCount = 0;
	lastWFTime = millis();
	while (1) {
		if (millis() - lastWFTime >= WFstatusInterval) {				//check whether base station restarted after every 20000ms
			lastWFTime = millis();
			Serial.println("Routine status check.");
			//kwkwkw2 only for free mode client.print("Status");    //avoid strip with \n leftover at basestn  client.println
			if (client.connected()) {
				if (client.available()) {
					svr_reply = client.readStringUntil('\n'); 	// Read until newline
					svr_reply.trim();														//clear any extras
					if (svr_reply.startsWith("VIDEO")) {					//1st priority
						Serial.println("Frames for video requested by server.");
						String frameCountStr = svr_reply.substring(5, 6);	// Remove "VIDEO" from string to get x secs; x=1..9
						reqframeCount = frameCountStr.toInt(); 							// Convert to an integer
						Serial.println("Frame count received from server: " + String(reqframeCount));
						currentSeqNum = 1;

						turnOnRecordingLight();
						for (int frm = 0; frm < reqframeCount; frm++) {
							readI2C();
						}
						reqframeCount = 0;
						turnOffRecordingLight();

					}
					else if (svr_reply.startsWith("CMD")) {
						Serial.println("Sensor configure by server.");
					}
					else if (reqframeCount == 0) {
						if (svr_reply == "HELLO") {
							Serial.println("PC fresh reply, restarting ESP32 in 1 seconds...");
							delay(1000);
							client.stop();
							esp_restart(); // Perform a warm restart
						}
						else if (svr_reply == "READY") {     //kwkwkw2
							Serial.println("svr_req: " + svr_reply);
							currentSeqNum = 1;
							readI2C();
						}
						else {
							Serial.println("svr_reply READY?" + svr_reply);
						}
					}
				}
			}
			else {
				noConnectCnt++;
				if (noConnectCnt > 3) {
					Serial.println("No connect with PC, restarting ESP32...");
					client.stop();
					esp_restart(); // Perform a warm restart
				}
			}
		}
	}
}

void readI2C() {
	const int i2CInterval = 100; // I2C read interval (ms)
	uint32_t lastI2CTime = 0;
	float pixels[AMG88xx_PIXEL_ARRAY_SIZE];			//float pixels[64];
	float f_curSeqNum;
	byte framecnt = 0;
	while (framecnt < bufferSize) {
		if (millis() - lastI2CTime >= i2CInterval) {
			lastI2CTime = millis();
			amg.readPixels(pixels);
			for (int i = 0; i < AMG88xx_PIXEL_ARRAY_SIZE; i++) {
				buffer[framecnt][i] = pixels[i];
				Serial.print(pixels[i]);
				Serial.print(", ");
			}
			Serial.println();
			f_curSeqNum = static_cast<float>(currentSeqNum);
			buffer[framecnt][AMG88xx_PIXEL_ARRAY_SIZE] = f_curSeqNum;
			// memcpy(buffer[framecnt] + payloadsz, &f_curSeqNum, sizeof(f_curSeqNum));        // Add sequence number &currentSeqNum	
			currentSeqNum++;
			framecnt++;
		}
	}
	for (int i = 0; i < bufferSize; i++) {
		if (sendPacket(buffer[i], payloadsz)) {      // Send the i-th row (65 floats)
			Serial.printf("Packet %d sent successfully. \n", i);
			//			  client.write((uint8_t*)buffer[i], payloadsz * sizeof(float));
			for (int j = 0; j < AMG88xx_PIXEL_ARRAY_SIZE + 1; j++) {
				Serial.print(buffer[i][j]);
				Serial.print(", ");
			}
		}
		else {
			Serial.printf("Failed to send packet %d. \n", i);
		}
	}
}

bool sendPacket(float* data, size_t size) {
	if (!client.connected()) {
		Serial.println("Server is not connected. Cannot send packet.");
		return false; // Connection lost
	}

	String datamsg = "DATA: " + String(payloadsz);  //total send string length fixed at 8 bytes
	client.print(datamsg);
	client.write((uint8_t*)data, size * sizeof(float));

	return true;
}

void turnOnInitLight() {
	pinMode(lightPin, OUTPUT);
	digitalWrite(lightPin, HIGH);
}

void turnOnRecordingLight() {
	pinMode(recordingLightPin, OUTPUT);
	digitalWrite(recordingLightPin, HIGH);
}

void turnOffRecordingLight() {
	pinMode(recordingLightPin, OUTPUT);
	digitalWrite(recordingLightPin, LOW);
}

void turnOnErrorLight() {
	pinMode(errorLightPin, OUTPUT);
	digitalWrite(errorLightPin, HIGH);
}

void turnOffErrorLight() {
	pinMode(errorLightPin, OUTPUT);
	digitalWrite(errorLightPin, HIGH);
}