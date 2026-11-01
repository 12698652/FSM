/**
 * 食品腐败智能检测系统 - ESP32-S3 固件（阶段 0：数据采集版）
 *
 * 功能：连 WiFi → 连巴法云 MQTT → 定时上报传感器 JSON → PC 端接收入库
 *
 * 使用说明：
 *   1. SENSORS_ENABLED = 1（PCB 已就位），启用 BME680 / SGP30 / MQ-137 真实采集
 *   2. WIFI_SSID / WIFI_PASS 填手机热点（注意 ESP32 仅支持 2.4GHz 频段）
 *   3. 上报周期 60 秒/次，匹配预处理 "60 点 = 60 分钟" 的窗口定义
 *   4. 时间戳由 PC 接收端统一按服务器时间写入，固件不再上报时间
 *   5. OLED(0x3C, SSD1306 128x64) 实时显示当前读数 + WiFi/MQTT 状态
 *   6. SGP30 基线持久化：每 30min 存 NVS，上电恢复 → 断电重启后无需
 *      等 1 小时基线重建，几分钟即回到可信读数（NVS 断电不丢、带磨损均衡）
 */
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiMulti.h>
#include <WiFiManager.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ===================== 用户配置区 =====================
// 多 WiFi 自动切换（WiFiMulti）：哪个可用连哪个，全断则自动重试
#define WIFI1_SSID      "HONOR 200"         // 手机热点（需为 2.4GHz 频段）
#define WIFI1_PASS      "pangwaer"          // 手机热点密码
#define WIFI2_SSID      "CMCC-KAUE"         // 备用 WiFi
#define WIFI2_PASS      "xinjinzhongxue"    // 备用 WiFi 密码
#define WIFI3_SSID      "gao"               // 备用 WiFi 3（需为 2.4GHz 频段）
#define WIFI3_PASS      "gao83516361"       // 备用 WiFi 3 密码

// 配网（WiFiManager）：已知网络都连不上时，板子自开热点，用手机网页输入新 WiFi
#define AP_NAME              "FSM-Setup"    // 配网热点名
#define AP_PASS              "fsm12345"     // 配网热点密码（≥8 位）
#define KNOWN_WIFI_TIMEOUT_MS 15000UL       // 尝试已知网络的时长(ms)，超过则进入配网
#define PORTAL_TIMEOUT_S     300            // 配网网页超时(秒)，超时后重启重试

#define MQTT_HOST       "bemfa.com"         // 巴法云 MQTT 服务器
#define MQTT_PORT       9501                // 巴法云 MQTT 端口
#define MQTT_KEY        "afc373d147d6af88a41f607133a292de"  // 巴法云私钥（作为 clientId，方式一认证）
#define TOPIC           "food001"           // 巴法云主题（仅字母数字）
#define TOPIC_SET       "food001/set"       // /set 后缀：推送给订阅者（PC 端用方式二身份订阅）

#define PUBLISH_INTERVAL_MS  60000UL        // 上报间隔：60 秒/次（匹配 60 点 = 60 分钟窗口）
#define WARMUP_MS            60000UL        // 上电后等待传感器稳定（MQ-137 完整老化需连续通电 24~48h）

#define SENSORS_ENABLED  1                  // PCB 已就位：启用真实传感器采集

// 温度校准：BME680 贴近 MQ-137 加热丝/主控，读数偏高（自热耦合）
// 一阶热模型：自热偏移 = OFF_MAX * S(t)，S 为板子自热进度 0→1
// 2026-09-22 开放环境标定：热平衡板读 41.7℃ / 室温 25.0℃；升温时间常数约 50 分钟
// 关键：开机时用 BME680 首读数判断芯片是否已热（死区判据）
//       首读数偏低(<THERMAL_WARM_C) → 芯片≈室温(冷启动) → S0=0，直接显示原值=真实室温
//       首读数偏高                  → 芯片已自热         → 按读数推断进度 S0
//       → 冷启动开机即显示真实室温（不再一律钉到 25℃），也不会等约 2 小时才恢复
// 物理依据：热平衡板读≈室温+16.7℃，故「未完热」芯片的读数必然明显低于热平衡值
// 注意：环境改变（封闭盒子/加风扇）后需重新标定 OFF_MAX
#define SELFHEAT_OFF_MAX   16.7f                // 热平衡自热偏移（℃）= 41.7 - 25.0
#define SELFHEAT_TAU_MS    (50.0f * 60000.0f)   // 热时间常数（约50分钟）
#define THERMAL_COLD_C     25.0f                // 标定室温参考点（℃），用于计算自热进度
#define THERMAL_HOT_C      41.7f                // 热平衡时 BME680 读数（℃）
#define THERMAL_WARM_C     34.0f                // 首读数低于此值即视为「芯片未热」（冷启动）
// =====================================================

#if SENSORS_ENABLED
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME680.h>
#include "Adafruit_SGP30.h"
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Preferences.h>

#define I2C_SDA   11      // 板卡 I²C SDA = A4（与 Arduino Nano ESP32 一致）
#define I2C_SCL   12      // 板卡 I²C SCL = A5（ESP32-S3 无 GPIO22，禁用 22~25）
#define MQ137_ADC 1       // 模拟输入 = A0 = U1 pin19（ADC1_CH0）。PCB 上 NH3_AO 走 R2/R3 分压后接到此脚
#define OLED_ADDR 0x3C    // OLED I²C 地址（诊断扫描已确认）

Adafruit_BME680 bme;      // I2C 地址 0x76
Adafruit_SGP30  sgp;      // I2C 地址 0x58
Adafruit_SSD1306 display(128, 64, &Wire, -1);   // SSD1306 128x64, I2C

// SGP30 基线持久化（NVS）：上电恢复 + 定期保存
// Sensirion 建议：基线在传感器稳定运行后读取；恢复后立即生效，免去约 1h 重建
Preferences prefs;
#define SGP_BASELINE_SAVE_MS  (30UL * 60UL * 1000UL)   // 保存周期 30min
unsigned long lastBaselineSave = 0;

// 最近一次采样（OLED 显示与 JSON 上报共用同一份数据）
struct Reading {
  float temp = 0, humi = 0, voc = 0;
  int   tvoc = 0, co2eq = 0, nh3 = 0;
  bool  sgpOk = false;
} last;

// ---------- OLED 状态屏 ----------
void oledShow(const char *l1, const char *l2 = "", const char *l3 = "", const char *l4 = "") {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);  display.println(l1);
  display.setCursor(0, 16); display.println(l2);
  display.setCursor(0, 32); display.println(l3);
  display.setCursor(0, 48); display.println(l4);
  display.display();
}

// VOC 污染指数(0-100)：BME680 的 voc 是气体电阻(kΩ)，洁净电阻大、污染电阻小，
// 与直觉相反。对数尺度折算成「洁净=低、污染=高」，锚点取训练数据电阻范围
// 1.4~12.5 kΩ（12.5→0，1.4→100），与网页端 vocIndex() 保持同一公式，仅作显示。
uint8_t vocIndex(float rKohm) {
  const float LO = 1.4f, HI = 12.5f;
  if (rKohm >= HI) return 0;
  if (rKohm <= LO) return 100;
  float s = (log10f(HI) - log10f(rKohm)) / (log10f(HI) - log10f(LO));
  return (uint8_t)(constrain(s, 0.0f, 1.0f) * 100.0f + 0.5f);
}

void oledUpdate(bool wifiOk, bool mqttOk) {
  char l1[22], l2[22], l3[22], l4[22];
  snprintf(l1, sizeof(l1), "T:%.1fC  H:%.0f%%", last.temp, last.humi);
  snprintf(l2, sizeof(l2), "TVOC:%d  CO2:%d", last.sgpOk ? last.tvoc : -1, last.sgpOk ? last.co2eq : -1);
  snprintf(l3, sizeof(l3), "VOC:%3u/100 NH3:%d", vocIndex(last.voc), last.nh3);
  snprintf(l4, sizeof(l4), "WIFI:%s MQTT:%s", wifiOk ? "OK" : "--", mqttOk ? "OK" : "--");
  oledShow(l1, l2, l3, l4);
}

// 自热进度：从开机推断的 S0 出发，指数趋近热平衡 1
float         thermalS0 = 0.0f;   // 开机时板子已自热程度 0..1（setup 按 BME680 首读数推断）
unsigned long thermalT0 = 0;      // 对应时间基准（millis）

// 自热偏移 = 热平衡偏移 × 当前自热进度
float selfHeatOffset() {
  float dt = (float)(millis() - thermalT0);
  float s  = 1.0f - (1.0f - thermalS0) * expf(-dt / SELFHEAT_TAU_MS);
  return SELFHEAT_OFF_MAX * s;
}

// NH₃ 采样：连续读 5 次取中位数，压制单次电噪声毛刺（真实气体变化会被保留）
int readNh3Median() {
  int s[5];
  for (int i = 0; i < 5; i++) { s[i] = analogRead(MQ137_ADC); delay(2); }
  for (int i = 1; i < 5; i++) {          // 插入排序
    int k = s[i], j = i - 1;
    while (j >= 0 && s[j] > k) { s[j + 1] = s[j]; j--; }
    s[j + 1] = k;
  }
  return s[2];
}

// SGP30 湿度补偿所需：绝对湿度 AH(g/m³)，Sensirion Magnus 公式
//   AH = 216.7 × (RH/100 × 6.112 × exp(17.62·T/(243.12+T))) / (273.15+T)
float absHumidity(float tC, float rh) {
  float es = 6.112f * expf(17.62f * tC / (243.12f + tC));   // 饱和水汽压(hPa)
  return 216.7f * (rh / 100.0f * es) / (273.15f + tC);
}

// 反向换算：已知绝对湿度 AH(g/m³) 与目标温度，求该温度下的相对湿度 RH(%)
//   用途：BME680 报的 RH 是「芯片温度(~41℃)」下的读数，直接上报会明显偏低；
//   芯片与环境同处一舱、含湿量近似守恒，用 AH 折算到【补偿后环境温度】即得更接近真实的 RH。
float rhFromAbsHumidity(float tC, float ah) {
  float es = 6.112f * expf(17.62f * tC / (243.12f + tC));
  return 100.0f * ah * (273.15f + tC) / (216.7f * es);
}
#endif

WiFiClient   wifiClient;
WiFiMulti    wifiMulti;
PubSubClient mqtt(wifiClient);
unsigned long lastPublish   = 0;
unsigned long lastPublishOk = 0;      // 上次成功发布时刻（自愈看门狗基准）
unsigned long bootTime      = 0;

// 自愈看门狗：连续 30 分钟无一次成功发布（WiFi 掉/MQTT 挂/程序异常）→ 重启自愈
#define PUBLISH_FAIL_REBOOT_MS  (30UL * 60UL * 1000UL)

// ---------- WiFi（已知网络 + WiFiManager 网页配网）----------
// 进入配网模式时的回调：串口 + OLED 提示怎么连
void onConfigMode(WiFiManager *wm) {
  char l2[24], l3[24];
  snprintf(l2, sizeof(l2), "AP: %s", AP_NAME);
  snprintf(l3, sizeof(l3), "PWD: %s", AP_PASS);
  Serial.printf("[WiFi] 进入配网模式：热点 %s / 密码 %s\n", AP_NAME, AP_PASS);
  Serial.printf("[WiFi] 手机连上后打开 http://%s 选择 WiFi\n", WiFi.softAPIP().toString().c_str());
  oledShow("WiFi Setup Mode", l2, l3, "192.168.4.1");
}

void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);

  // 1) 先试代码里写死的已知网络：在家里会秒连，不打扰用户
  Serial.println("[WiFi] 尝试已知网络: HONOR 200 / CMCC-KAUE / gao");
  wifiMulti.addAP(WIFI1_SSID, WIFI1_PASS);
  wifiMulti.addAP(WIFI2_SSID, WIFI2_PASS);
  wifiMulti.addAP(WIFI3_SSID, WIFI3_PASS);
  unsigned long t0 = millis();
  while (wifiMulti.run() != WL_CONNECTED && millis() - t0 < KNOWN_WIFI_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] 已连接 %s, IP: %s\n",
                  WiFi.SSID().c_str(), WiFi.localIP().toString().c_str());
    return;
  }

  // 2) 已知网络都不可用 → 交给 WiFiManager：先试 NVS 记住的旧网络，仍不行就开热点配网
  Serial.println("\n[WiFi] 未发现已知网络，启动 WiFiManager（记忆旧网络 / 网页配网）...");
  WiFiManager wifiManager;
  wifiManager.setDebugOutput(true);
  wifiManager.setConfigPortalTimeout(PORTAL_TIMEOUT_S);
  wifiManager.setAPCallback(onConfigMode);
  if (!wifiManager.autoConnect(AP_NAME, AP_PASS)) {
    Serial.println("[WiFi] 配网超时，重启后重试...");
    delay(1000);
    ESP.restart();
  }
  Serial.printf("[WiFi] 配网完成，已连接 %s, IP: %s\n",
                WiFi.SSID().c_str(), WiFi.localIP().toString().c_str());
}

// ---------- MQTT ----------
// 有界重连：最多 10 次，绝不永久阻塞 loop()（阻塞会导致 OLED 冻结、自愈看门狗失效）
void mqttReconnect() {
  for (int i = 0; i < 10 && !mqtt.connected(); i++) {
    Serial.println("[MQTT] 连接巴法云...");
    // 方式一认证：clientId = 私钥（用户名密码留空）
    if (mqtt.connect(MQTT_KEY)) {
      Serial.println("[MQTT] 连接成功");
      break;
    }
    Serial.printf("[MQTT] 失败 rc=%d, 3秒后重试(%d/10)\n", mqtt.state(), i + 1);
    delay(3000);
  }
}

// ---------- 读取传感器并构造 JSON ----------
bool buildPayload(char *buf, size_t len) {
  StaticJsonDocument<256> doc;
#if SENSORS_ENABLED
  if (!bme.performReading()) {
    Serial.println("[BME680] 读取失败");
    return false;
  }
  last.voc  = bme.gas_resistance / 1000.0;       // kOhm，后续可换算 VOC 指数
  last.temp = bme.temperature - selfHeatOffset(); // 减去自热偏移（随时间变化）→ 近似真实环境温度
  // 绝对湿度必须用 BME680 的【原始 (T,RH) 配对】——两者都基于芯片温度，自洽；
  //   若用 last.temp(已减 ~16.7℃) 配原始 RH，算出的绝对湿度会偏小好几倍。
  //   同一个 AH 用于两处：(1) SGP30 湿度补偿  (2) 折算环境温度下的 RH 上报
  float ah = absHumidity(bme.temperature, bme.humidity);
  last.humi = rhFromAbsHumidity(last.temp, ah);  // 芯片温度 RH → 补偿温度 RH（否则明显偏低）
  sgp.setHumidity((uint32_t)(ah * 1000.0f));
  last.sgpOk = sgp.IAQmeasure();
  if (last.sgpOk) {
    last.tvoc  = sgp.TVOC;
    last.co2eq = sgp.eCO2;
  }
  last.nh3 = readNh3Median();
  doc["voc"]    = last.voc;
  doc["temp"]   = last.temp;
  doc["humi"]   = last.humi;
  if (last.sgpOk) {
    doc["tvoc"]  = last.tvoc;
    doc["co2eq"] = last.co2eq;
  }
  doc["nh3_adc"] = last.nh3;
#else
  // ---- PCB 未到手：模拟数据（模拟食品缓慢腐败趋势）----
  unsigned long t = (millis() - bootTime) / 1000UL;
  doc["voc"]    = 150 + 0.02 * t;
  doc["co2eq"]  = 400 + 0.6 * t;
  doc["tvoc"]   = 200 + 0.4 * t;
  doc["temp"]   = 25.0;
  doc["humi"]   = 60.0;
  doc["nh3_adc"] = 512 + (int)(0.25 * t);
#endif
  serializeJson(doc, buf, len);   // 时间戳由 PC 接收端按服务器时间写入
  return true;
}

// ===================== 主程序 =====================
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n===== 食品腐败检测系统 固件启动 =====");
  bootTime = millis();
  lastPublishOk = millis();   // 自愈看门狗基准：从开机起算

#if SENSORS_ENABLED
  Wire.begin(I2C_SDA, I2C_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR))
    Serial.println("[OLED] 初始化失败，检查接线/地址 0x3C");
  oledShow("FSM Booting...", "MQ-137 warmup", "60s...");
  Serial.println("[传感器] MQ-137 预热中(60秒)...");
  delay(WARMUP_MS);
  if (!bme.begin(0x76, &Wire)) Serial.println("[BME680] 初始化失败，检查接线/地址");
  if (!sgp.begin())            Serial.println("[SGP30] 初始化失败，检查接线");
  else {
    sgp.IAQinit();
    // ---- 基线恢复：NVS 有历史基线则立即写入，免去 ~1h 重建 ----
    prefs.begin("sgp30", false);
    if (prefs.isKey("eco2b") && prefs.isKey("tvocb")) {
      uint16_t b_eco2 = prefs.getUShort("eco2b");
      uint16_t b_tvoc = prefs.getUShort("tvocb");
      if (sgp.setIAQBaseline(b_eco2, b_tvoc))
        Serial.printf("[SGP30] 基线恢复成功 eco2=%u tvoc=%u\n", b_eco2, b_tvoc);
      else
        Serial.println("[SGP30] 基线恢复失败，走默认自校准");
    } else {
      Serial.println("[SGP30] NVS 无历史基线，首次运行走默认自校准");
    }
    lastBaselineSave = millis();
  }
  Serial.println("[传感器] SGP30 前15秒输出固定值，属正常现象");

  // 开机自热推断：用 BME680 首读数判断芯片是否已热（死区判据）
  //   首读数偏低(<THERMAL_WARM_C) → 冷启动，芯片≈室温 → S0=0，直接显示原值（真实室温）
  //   首读数偏高                  → 芯片已自热         → 按读数推断进度 S0
  float r0 = bme.performReading() ? bme.temperature : THERMAL_COLD_C;
  if (r0 < THERMAL_WARM_C) {
    thermalS0 = 0.0f;   // 冷启动：不补偿，原值即室温
  } else {
    thermalS0 = constrain((r0 - THERMAL_COLD_C) / (THERMAL_HOT_C - THERMAL_COLD_C), 0.0f, 1.0f);
  }
  thermalT0 = millis();
  Serial.printf("[温度] 开机首读 %.1f℃ → 自热进度 %.2f（起始偏移 %.1f℃）\n",
                r0, thermalS0, SELFHEAT_OFF_MAX * thermalS0);
#endif

  oledShow("FSM Booting...", "Connecting WiFi", "auto / portal");
  setupWiFi();
  oledShow("WiFi OK", WiFi.SSID().c_str(), WiFi.localIP().toString().c_str(), "Connecting MQTT...");
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

void loop() {
  // ---- 自愈看门狗：连续 30 分钟无成功发布 → 重启（覆盖掉线/挂死/被踢全部场景）----
  if (millis() - lastPublishOk >= PUBLISH_FAIL_REBOOT_MS) {
    Serial.println("[自愈] 连续30分钟无成功发布，重启设备...");
#if SENSORS_ENABLED
    oledShow("Self-heal reboot", "no publish 30min",
             (WiFi.status() == WL_CONNECTED) ? WiFi.SSID().c_str() : "WiFi lost", "");
#endif
    delay(500);
    ESP.restart();
  }

  if (WiFi.status() != WL_CONNECTED) {   // WiFi 掉线：先重连上次网络(NVS)，再试已知网络
    Serial.println("[WiFi] 掉线，尝试重连...");
    WiFi.reconnect();
    if (WiFi.status() != WL_CONNECTED) wifiMulti.run();
    delay(1000);
    return;
  }
  if (!mqtt.connected()) mqttReconnect();
  mqtt.loop();

  if (millis() - lastPublish >= PUBLISH_INTERVAL_MS) {
    lastPublish = millis();
    char buf[256];
    if (buildPayload(buf, sizeof(buf))) {
      bool ok = mqtt.publish(TOPIC_SET, buf);   // /set 后缀才会推送给 PC 订阅端
      if (ok) lastPublishOk = millis();         // 喂自愈看门狗
      Serial.printf("[MQTT] 发布%s: %s\n", ok ? "成功" : "失败", buf);
    }
#if SENSORS_ENABLED
    oledUpdate(true, mqtt.connected());         // 每个上报周期刷新 OLED 状态屏

    // ---- SGP30 基线定期保存到 NVS（30min 一次，NVS 自带磨损均衡）----
    if (last.sgpOk && millis() - lastBaselineSave >= SGP_BASELINE_SAVE_MS) {
      lastBaselineSave = millis();
      uint16_t b_eco2, b_tvoc;
      if (sgp.getIAQBaseline(&b_eco2, &b_tvoc)) {
        prefs.putUShort("eco2b", b_eco2);
        prefs.putUShort("tvocb", b_tvoc);
        Serial.printf("[SGP30] 基线已存 NVS eco2=%u tvoc=%u\n", b_eco2, b_tvoc);
      }
    }
#endif
  }
}
