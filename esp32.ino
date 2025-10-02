//Autores: Antônio Jacinto de Andrade Neto (RM: 561777), Felipe Bicaletto (RM: 563524), João Vitor dos Santos Pereira (RM: 551695) e Thayná Pereira Simões (RM: 566456) 
//Resumo: Programa para criar um placar eletrônico com ESP32, 4 botões físicos, MQTT e LCD I2C.

#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"

// ---------------- Configurações editáveis ----------------
const char* SSID = "Wokwi-GUEST";  // Nome da rede Wifi
const char* PASSWORD = "";  // Senha da rede Wifi
const char* BROKER_MQTT = "20.46.254.134";  // IP do broker
const int BROKER_PORT = 1883;  // Porta do Broker
const char* DEVICE_ID = "hosp001";
const char* TOPICO_SUBSCRIBE = "/TEF/hosp001/cmd";
const char* TOPICO_PUBLISH_L = "/TEF/hosp001/attrs/l";  // Tópico de envio da luminosidade
const char* TOPICO_PUBLISH_T = "/TEF/hosp001/attrs/t";  // Tópico de envio da temperatura
const char* TOPICO_PUBLISH_H = "/TEF/hosp001/attrs/h";  // Tópico de envio da umidade
const char* ID_MQTT = "fiware_001";  // ID do MQTT

bool alert_luminosity_flag = false;
bool alert_temperature_flag = false;
bool alert_humidity_flag = false;

// ---------------- Objetos ----------------
WiFiClient espClient;  // Objeto Wifi
PubSubClient MQTT(espClient);  // Objeto MQTT

#define DHTPIN 25
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

const int ldrPIN = 33;
const int LED = 2;
const int BUZZER = 18;

// ---------------- Funções ----------------

// Inicia monitor serial
void initSerial() {
  Serial.begin(115200);
}

// Inicia conexão wifi
void initWiFi() {
  Serial.println("------ Conexao WiFi ------");
  WiFi.begin(SSID, PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

// Inicia conexão com MQTT Broker
void initMQTT() {
  MQTT.setServer(BROKER_MQTT, BROKER_PORT);
  MQTT.setCallback(mqtt_callback);
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
    String msg;
    for (int i = 0; i < length; i++) {
        char c = (char)payload[i];
        msg += c;
    }
    Serial.print("- Mensagem recebida: ");
    Serial.println(msg);

    // Forma o padrão de tópico para comparação
    String on_alert_luminosity = String(DEVICE_ID) + "@on_alert_luminosity|";
    String on_normal_luminosity = String(DEVICE_ID) + "@on_normal_luminosity|";
    String on_alert_temperature = String(DEVICE_ID) + "@on_alert_temperature|";
    String on_normal_temperature = String(DEVICE_ID) + "@on_normal_temperature|";
    String on_alert_humidity = String(DEVICE_ID) + "@on_alert_humidity|";
    String on_normal_humidity = String(DEVICE_ID) + "@on_normal_humidity|";
    
    // Compara com o tópico recebido
    if (msg.equals(on_alert_luminosity)) alert_luminosity_flag = true;
    if (msg.equals(on_normal_luminosity)) alert_luminosity_flag = false;

    if (msg.equals(on_alert_temperature)) alert_temperature_flag = true;
    if (msg.equals(on_normal_temperature)) alert_temperature_flag = false;

    if (msg.equals(on_alert_humidity)) alert_humidity_flag = true;
    if (msg.equals(on_normal_humidity)) alert_humidity_flag = false;

}

// Reconecta ao MQTT
void reconnectMQTT() {
  while (!MQTT.connected()) {
    Serial.print("Tentando conectar ao Broker MQTT...");
    if (MQTT.connect(ID_MQTT)) {
      Serial.println("Conectado!");
      MQTT.subscribe(TOPICO_SUBSCRIBE);
    } else {
      Serial.print("Falhou, rc=");
      Serial.print(MQTT.state());
      Serial.println(" tentando novamente em 2s");
      delay(2000);
    }
  }
}

// Verifica conexão wifi e conexão com MQTT Broker
void VerificaConexoesWiFIEMQTT() {
  if (!MQTT.connected()) reconnectMQTT();
  if (WiFi.status() != WL_CONNECTED) initWiFi();
}

// Publica gols do time A e gols do time B no tópico definido
void publicarLuminosidade() {
  int sensorValue = analogRead(ldrPIN);
  int luminosidade = map(sensorValue, 0, 4095, 100, 0);
  String mensagem = String(luminosidade);
  Serial.print("Valor da luminosidade: ");
  Serial.print(mensagem.c_str());
  Serial.println("%");
  MQTT.publish(TOPICO_PUBLISH_L, mensagem.c_str());
}

void publicarTemperatura() {
  float temperatura = dht.readTemperature();
  String mensagem = String(temperatura);
  Serial.print("Valor da temperatura: ");
  Serial.print(mensagem.c_str());
  Serial.println("°C");
  MQTT.publish(TOPICO_PUBLISH_T, mensagem.c_str());
}

void publicarUmidade() {
  float umidade = dht.readHumidity();
  String mensagem = String(umidade);
  Serial.print("Valor da umidade: ");
  Serial.print(mensagem.c_str());
  Serial.println("%");
  MQTT.publish(TOPICO_PUBLISH_H, mensagem.c_str());
}

void alert_luminosity () {
  digitalWrite(LED, HIGH);
  tone(BUZZER, 1000);   // tom 1kHz
  delay(200);
  digitalWrite(LED, LOW);
  noTone(BUZZER);
  delay(200);
}

void alert_temperature () {
  digitalWrite(LED, HIGH);
  tone(BUZZER, 500);   // tom 500Hz
  delay(500);
  digitalWrite(LED, LOW);
  noTone(BUZZER);
  delay(500);
}

void alert_humidity () {
  digitalWrite(LED, HIGH);
  tone(BUZZER, 2000);   // tom 2kHz
  delay(300);
  noTone(BUZZER);
  delay(300);
}

// Função que é executada no início
void setup() {
  initSerial();
  initWiFi();
  initMQTT();

  pinMode(BUZZER, OUTPUT);
  pinMode(LED, OUTPUT);
}

// Função que fica rodando durante a aplicação
void loop() {
  VerificaConexoesWiFIEMQTT();
  
  publicarLuminosidade();
  publicarTemperatura();
  publicarUmidade();

  if (
    (alert_luminosity_flag == true && alert_temperature_flag == true && alert_humidity_flag == true) ||
    (alert_luminosity_flag == true && alert_temperature_flag == true) ||
    (alert_luminosity_flag == true && alert_humidity_flag == true) ||
    (alert_temperature_flag == true && alert_humidity_flag == true) 
  ) {
    digitalWrite(LED, HIGH);
    tone(BUZZER, 1000);
  } else {

    if (alert_luminosity_flag == true) alert_luminosity();
    if (alert_temperature_flag == true) alert_temperature();
    if (alert_humidity_flag == true) alert_humidity();
  }
  
  delay((1000));
  
  MQTT.loop();
}