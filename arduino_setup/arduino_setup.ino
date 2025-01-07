//  Variables
int PulseSensorPurplePin = 0; // Pulse Sensor WIRE connected to ANALOG PIN 0
int LED = LED_BUILTIN; //  The on-board Arduino LED

int Signal; // holds the incoming raw data. Signal value can range from 0-1024
int Threshold = 580; // Determine which Signal to "count as a beat", and which to ignore.
char userInput; // Variable to store user input

// The SetUp Function:
void setup() {
  pinMode(LED, OUTPUT); // pin that will blink to your heartbeat!
  Serial.begin(9600); // Set's up Serial Communication at a certain speed.
}

// The Main Loop Function
void loop() {
  if (Serial.available() > 0) {
    userInput = Serial.read(); // read user input
    if (userInput == 's') {
      Signal = analogRead(PulseSensorPurplePin); // Read the PulseSensor's value.
      Serial.println(Signal); // Send the Signal value to Serial Plotter.
      if (Signal > Threshold) { // If the signal is above "550", then "turn-on" Arduino's on-Board LED.
        digitalWrite(LED, HIGH);
      } else {
        digitalWrite(LED, LOW); //  Else, the signal must be below "550", so "turn-off" this LED.
      }
      // delay(10);
    }
  }
}
