/**
 * 食品腐败智能检测系统 — 阶段1硬件联调诊断固件
 *
 * 用途：PCB 到手后第一个烧录的程序，验证三件事：
 *   1. 芯片/内存自检         —— 确认 ESP32-S3 正常启动、Flash/PSRAM 被识别
 *   2. I²C 总线扫描          —— 确认 SGP30(0x58) / OLED(0x3C) 接线与上拉正常
 *   3. MQ-137 ADC 采样       —— 确认 A0/GPIO1 可用、氨气传感器输出的电压是否合理
 *
 * 编译： pio run -e diag
 * 烧录： pio run -e diag -t upload
 * 监视： pio run -e diag -t monitor
 *
 * 与主固件 main.cpp 无关，不影响主程序。
 */
#include <Arduino.h>
#include <Wire.h>

#define I2C_SDA   11      // 板卡 I²C SDA = A4 = U1 pin23
#define I2C_SCL   12      // 板卡 I²C SCL = A5 = U1 pin24
#define MQ137_ADC 1       // 模拟输入 = A0 = U1 pin19（ADC1_CH0）。PCB 上 NH3_AO 走 R2/R3 分压后接到此脚

// ===================== 1. 芯片自检 =====================
void chipInfo() {
  Serial.println("\n========== [1] 芯片自检 ==========");
  Serial.printf("  芯片型号 : %s\n", ESP.getChipModel());
  Serial.printf("  核心数   : %d\n", ESP.getChipCores());
  Serial.printf("  CPU 频率 : %d MHz\n", ESP.getCpuFreqMHz());
  Serial.printf("  Flash 大小: %d MB\n", ESP.getFlashChipSize() / 1048576);
  uint32_t psram = ESP.getPsramSize();
  Serial.printf("  PSRAM 大小: %d MB\n", psram / 1048576);
  if (psram > 0) {
    // 带 PSRAM 的 ESP32-S3 模组(如 ESP32-S3R8)会用 GPIO33~37 作 Octal PSRAM 数据线，
    // 因此 ADC 只走 ADC1(GPIO1~10)，本固件用 A0(GPIO1) 避开冲突。
    Serial.println("  [提示] 检测到 PSRAM，ADC 选用 ADC1 的 A0(GPIO1)，避开 PSRAM 占用的 GPIO33~37");
  }
}

// ===================== 2. I²C 总线扫描 =====================
void scanI2C() {
  Serial.println("\n========== [2] I²C 总线扫描 (SDA=A4/pin23=GPIO11, SCL=A5/pin24=GPIO12) ==========");
  int found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    uint8_t err = Wire.endTransmission();
    if (err == 0) {
      Serial.printf("  0x%02X", addr);
      if (addr == 0x76)      Serial.print("  <== BME680");
      else if (addr == 0x77) Serial.print("  <== BME680(备选地址)");
      else if (addr == 0x58) Serial.print("  <== SGP30");
      else if (addr == 0x3C) Serial.print("  <== OLED");
      else if (addr == 0x3D) Serial.print("  <== OLED(备选地址)");
      Serial.println();
      found++;
      delay(2);
    }
  }
  if (found == 0) {
    Serial.println("  !! 未发现任何设备");
    Serial.println("     排查: 1) 传感器是否已焊/插 2) 供电是否正常 3) SDA/SCL 是否接反");
  } else {
    Serial.printf("  共发现 %d 个 I²C 设备\n", found);
  }
}

// ===================== 3. MQ-137 ADC 采样 =====================
void testADC() {
  Serial.println("\n========== [3] MQ-137 ADC 采样 (A0/GPIO1) ==========");
  analogReadResolution(12);
  analogSetPinAttenuation(MQ137_ADC, ADC_11db);   // 11dB 衰减，量程约 0~3.1V
  Serial.println("  连续采样 10 次(每次间隔 500ms):");
  Serial.println("  注意: MQ-137 需预热 1-2 分钟读数才稳，刚上电偏低属正常");
  int minV = 4096, maxV = 0;
  for (int i = 0; i < 10; i++) {
    int raw = analogRead(MQ137_ADC);
    float volt = raw * 3.3f / 4095.0f;
    Serial.printf("    #%2d  raw=%4d  约 %.3f V\n", i + 1, raw, volt);
    if (raw < minV) minV = raw;
    if (raw > maxV) maxV = raw;
    delay(500);
  }
  Serial.printf("  结果: 最小值=%d 最大值=%d 波动=%d\n", minV, maxV, maxV - minV);
  if (minV < 0) {
    // 不可能发生，占位
  } else if (maxV >= 4090) {
    Serial.println("  !! 读数长时间满量程(≈4095/3.3V)");
    Serial.println("     可能: 1) MQ-137 输出(5V)直连 A0/GPIO1 未分压(超 3.3V 损坏风险!) 2) 分压电阻接错");
    Serial.println("     请立即断电检查 PCB，确认 MQ-137 AO 是否经过 R2/R3 分压后再到 A0/GPIO1");
  } else if (maxV - minV <= 2) {
    Serial.println("  !! 读数完全不变，A0/GPIO1 可能未接线或分压后电压过低");
  } else {
    Serial.println("  [OK] 读数正常波动，A0/GPIO1 可用，ADC 工作正常");
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n==========================================");
  Serial.println("  食品腐败检测系统 · 阶段1诊断固件 v1");
  Serial.println("==========================================");

  chipInfo();
  Wire.begin(I2C_SDA, I2C_SCL);
  scanI2C();
  testADC();

  Serial.println("\n==========================================");
  Serial.println("  诊断完成。如需重跑，按板载 RST 或重新上电");
  Serial.println("==========================================");
}

void loop() {
  // 烧录结束时 esptool 会自动硬复位一次，日志在监视器打开前就打完了；
  // 本板没有 BOOT 键，为避免依赖手动复位，loop 里周期重扫，
  // 保证串口监视器任何时候连上来都能看到结果。
  delay(5000);
  Serial.println("\n\n>>>>>> 周期重扫 (每 5 秒一次，便于监视器随时查看) <<<<<<");
  scanI2C();

  Serial.println("\n---------- MQ-137 ADC 单次快照 (A0/GPIO1) ----------");
  analogReadResolution(12);
  analogSetPinAttenuation(MQ137_ADC, ADC_11db);
  int raw = analogRead(MQ137_ADC);
  Serial.printf("  raw=%4d  约 %.3f V\n", raw, raw * 3.3f / 4095.0f);
  if (raw >= 4090) {
    Serial.println("  !! 满量程：确认 MQ-137 AO 是否经 R2/R3 分压后再接 A0/GPIO1（超 3.3V 有损坏风险）");
  }
}
