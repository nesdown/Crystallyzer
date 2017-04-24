//Sikorsky Challenge 2016
#include <math.h>
#define LDR_PIN A1
#define TERMIST_PIN A0
#define TERMIST_B 4300
#define VIN 5.0
#define BUZZER_PIN 3
#define RESIST_PIN A2
#define LED_PIN 13
int measureTime = 10;

void setup() {
  // init serial monitor with 9600 bpm
  Serial.begin(9600);
  digitalWrite(LED_PIN, HIGH); 
  delay(1000);
  digitalWrite(LED_PIN, LOW);
  delay(1000);
  

  //environment params measure
  for(int x = 0; x < measureTime; x++){
    tone(BUZZER_PIN, 4000, 20);
    delay(500);
  }
    
  measure();

  delay(10000);

  //crystall params measure
  digitalWrite(LED_PIN, HIGH);
  for(int x = 0; x < measureTime; x++){
    tone(BUZZER_PIN, 4000, 20);
    delay(500);
  }
  measure();
}

void loop() {
  
}

void measure() {
  //work with light dependent resistor
  int lightVal = analogRead(LDR_PIN);

  //work with temperature sensor
  //formula for the temperature with voltage, aresist and fahrenheit to celcium covertation
  float voltage = analogRead(TERMIST_PIN) * VIN / 1023.0;
  float r1 = voltage / (VIN - voltage);
  float temperature = 1.0/( 1.0/(TERMIST_B)*log(r1)+1.0/(25.0 + 273.0) ) - 273.0; 
  float resist = analogRead(A2);

  Serial.print(temperature);
  Serial.print(" ");
  Serial.print(lightVal);
  Serial.print(" ");
  Serial.print(resist);
  Serial.println();
}

