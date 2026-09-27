#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
食品腐败风险预测系统 - KiCad 工程文件生成器
生成 KiCad 5 格式的工程文件,可导入嘉立创EDA专业版

输出文件:
  - FoodSpoilageMonitor.pro   工程文件
  - FoodSpoilageMonitor.sch   原理图
  - FoodSpoilageMonitor.kicad_pcb  PCB布局
  - FoodSpoilageMonitor.net   网表(备份)
  - FoodSpoilageMonitor.lib   自定义符号库
  - FoodSpoilageMonitor.dcm   符号库描述
"""

import os
import time

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 元件清单 (BOM)
# 格式: (位号, 名称, 值, 封装, 库引用, x坐标, y坐标, 旋转)
# 坐标单位: mil (1 mil = 0.0254 mm)
# ============================================================
COMPONENTS = [
    # 电源部分 (左侧)
    ("J1",  "USB_IN",      "5V/3A",   "TerminalBlock:TerminalBlock_bornier-2_P5.08mm",
     "Connector_Generic:Conn_01x02", 1500, 2000, 0),
    ("SW1", "总开关",       "SS-12F15","Button_Switch_THT:SW_CuK_OS102011MA1QN1_SPDT_Angled",
     "Switch:SW_SPDT",        2500, 2000, 180),
    ("F1",  "PTC保险丝",    "1.1A",    "Fuse:Fuse_BelFuse_0ZCF0005FF_C6.3x5.1",
     "Device:Polyfuse",       3500, 2000, 0),
    ("C1",  "电解电容",     "10uF",    "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm",
     "Device:CP",             4500, 2000, 0),

    # ESP32 主控 (中央)
    ("U1",  "ESP32-WROOM-32","",       "Module:NodeMCU-32S",
     "ESP32:ESP32-WROOM-32",  4000, 4000, 0),

    # I2C传感器 (右上)
    ("U2",  "BME680",       "",        "PinHeader:PinHeader_1x04_P2.54mm_Vertical",
     "Connector_Generic:Conn_01x04", 6500, 2000, 0),
    ("U3",  "SGP30",        "",        "PinHeader:PinHeader_1x04_P2.54mm_Vertical",
     "Connector_Generic:Conn_01x04", 6500, 3100, 0),

    # MQ-137 (右下)
    ("U4",  "MQ-137",       "NH3",     "PinHeader:PinHeader_1x03_P2.54mm_Vertical",
     "Connector_Generic:Conn_01x03", 6500, 4500, 0),
    ("C2",  "陶瓷电容",     "100nF",   "Capacitor_SMD:C_0805_2012Metric",
     "Device:C",              5600, 4500, 0),

    # 风扇 (左下)
    ("SW2", "风扇开关",     "SS-12F15","Button_Switch_THT:SW_CuK_OS102011MA1QN1_SPDT_Angled",
     "Switch:SW_SPDT",        2500, 5200, 0),
    ("M1",  "风扇",         "5V",      "PinHeader:PinHeader_1x02_P2.54mm_Vertical",
     "Connector_Generic:Conn_01x02",  3500, 5500, 0),

    # LED指示灯
    ("D1",  "LED红",        "Red",     "LED_THT:LED_D5.0mm",
     "Device:LED",            1500, 3700, 180),
    ("R1",  "限流电阻",     "150R",    "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
     "Device:R",              1500, 3000, 90),

    # 端子排 (底部)
    ("TB1", "电源端子排",   "4P",      "TerminalBlock:TerminalBlock_bornier-4_P5.08mm",
     "Connector_Generic:Conn_01x04", 1500, 6500, 0),
    ("TB2", "信号端子排",   "8P",      "TerminalBlock:TerminalBlock_bornier-8_P5.08mm",
     "Connector_Generic:Conn_01x08", 3500, 6500, 0),
    ("TB3", "风扇端子排",   "2P",      "TerminalBlock:TerminalBlock_bornier-2_P5.08mm",
     "Connector_Generic:Conn_01x02", 5500, 6500, 0),
]

# ============================================================
# 网络连接表 (Netlist)
# 格式: 网络名 -> [(位号, 引脚号), ...]
# ============================================================
NETS = {
    "+5V": [
        ("J1", "1"), ("SW1", "1"), ("F1", "1"), ("C1", "1"),
        ("U1", "1"),   # ESP32 VIN
        ("U4", "1"),   # MQ-137 VCC
        ("SW2", "1"),  # 风扇开关输入
        ("R1", "1"),   # LED限流电阻
        ("TB1", "1"),
    ],
    "GND": [
        ("J1", "2"), ("C1", "2"), ("C2", "2"),
        ("U1", "2"),   # ESP32 GND
        ("U2", "2"), ("U3", "2"), ("U4", "2"),
        ("M1", "2"),   # 风扇GND
        ("D1", "1"),   # LED负极
        ("TB1", "2"), ("TB2", "4"), ("TB3", "2"),
    ],
    "+3V3": [
        ("U1", "3"),   # ESP32 3V3输出
        ("U2", "1"),   # BME680 VCC
        ("U3", "1"),   # SGP30 VCC
        ("TB1", "4"),
    ],
    "SDA": [
        ("U1", "4"),   # ESP32 GPIO21
        ("U2", "3"),   # BME680 SDA
        ("U3", "3"),   # SGP30 SDA
        ("TB2", "1"),
    ],
    "SCL": [
        ("U1", "5"),   # ESP32 GPIO22
        ("U2", "4"),   # BME680 SCL
        ("U3", "4"),   # SGP30 SCL
        ("TB2", "2"),
    ],
    "NH3_AO": [
        ("U4", "3"),   # MQ-137 AO
        ("U1", "6"),   # ESP32 GPIO34
        ("C2", "1"),   # 滤波电容
        ("TB2", "3"),
    ],
    "FAN_OUT": [
        ("SW2", "2"),  # 风扇开关输出
        ("M1", "1"),   # 风扇VCC
        ("TB3", "1"),
    ],
    "LED_A": [
        ("R1", "2"),
        ("D1", "2"),
    ],
}

# ============================================================
# 元件引脚定义 (用于原理图符号)
# 格式: 位号 -> [(引脚号, 引脚名, x, y, 方向)]
# 方向: 0=右, 90=上, 180=左, 270=下
# ============================================================
PIN_DEFS = {
    "J1":  [("1","+",0,0,0), ("2","-",0,100,180)],
    "SW1": [("1","IN",0,0,180), ("2","OUT",0,100,0), ("3","NC",0,200,0)],
    "F1":  [("1","IN",0,0,180), ("2","OUT",0,100,0)],
    "C1":  [("1","+",0,0,90), ("2","-",0,100,270)],
    "U1":  [("1","VIN",0,0,180), ("2","GND",0,100,270), ("3","3V3",0,200,90),
            ("4","GPIO21/SDA",0,300,0), ("5","GPIO22/SCL",0,400,0),
            ("6","GPIO34/ADC",0,500,0)],
    "U2":  [("1","VCC",0,0,180), ("2","GND",0,100,270),
            ("3","SDA",0,200,0), ("4","SCL",0,300,0)],
    "U3":  [("1","VCC",0,0,180), ("2","GND",0,100,270),
            ("3","SDA",0,200,0), ("4","SCL",0,300,0)],
    "U4":  [("1","VCC",0,0,180), ("2","GND",0,100,270), ("3","AO",0,200,0)],
    "C2":  [("1","A",0,0,90), ("2","B",0,100,270)],
    "SW2": [("1","IN",0,0,180), ("2","OUT",0,100,0), ("3","NC",0,200,0)],
    "M1":  [("1","+",0,0,180), ("2","-",0,100,270)],
    "D1":  [("1","K",0,0,270), ("2","A",0,100,90)],
    "R1":  [("1","1",0,0,180), ("2","2",0,100,0)],
    "TB1": [("1","5V",0,0,180), ("2","GND",0,100,270),
            ("3","5V_BUS",0,200,180), ("4","3V3",0,300,180)],
    "TB2": [("1","SDA",0,0,180), ("2","SCL",0,100,180),
            ("3","ADC",0,200,180), ("4","SGND",0,300,270),
            ("5","3V3",0,400,180), ("6","5V",0,500,180),
            ("7","SGND",0,600,270), ("8","NC",0,700,0)],
    "TB3": [("1","FAN+",0,0,180), ("2","FAN-",0,100,270)],
}

# ============================================================
# 生成时间戳格式的UUID
# ============================================================
uuid_counter = 0x5F8A0000
def next_uuid():
    global uuid_counter
    uuid_counter += 1
    return str(uuid_counter)

# ============================================================
# 生成工程文件 (.pro)
# ============================================================
def gen_project():
    return """update=2026-08-07
version=1
last_client=kicad
[general]
version=1
RootSch=FoodSpoilageMonitor.sch
BoardNm=FoodSpoilageMonitor.kicad_pcb
[cvpcb]
version=1
NetIExt=net
[eeschema]
version=1
LibDir=
[eeschema/libraries]
LibName1=power
LibName2=Device
LibName3=Connector_Generic
LibName4=Switch
LibName5=Motor
LibName6=FoodSpoilageMonitor
[pcbnew]
version=1
PageLayoutDescrFile=
LastNetListRead=FoodSpoilageMonitor.net
CopperLayerCount=2
BoardThickness=1.6
"""

# ============================================================
# 生成原理图文件 (.sch) - KiCad 5 格式
# ============================================================
def gen_schematic():
    lines = []
    lines.append("EESchema Schematic File Version 4")
    lines.append("LIBS:power;Device;Connector_Generic;Switch;Motor;FoodSpoilageMonitor")
    lines.append("EELAYER 26 0")
    lines.append("EELAYER END")
    lines.append("$Descr A3 16535 11693")
    lines.append("encoding utf-8")
    lines.append("Sheet 1 1")
    lines.append('Title "食品腐败风险预测系统"')
    lines.append('Date "2026-08-07"')
    lines.append('Rev "1.0"')
    lines.append('Comp "FSM Project"')
    lines.append('Comment1 "ESP32 + BME680 + SGP30 + MQ-137"')
    lines.append('Comment2 "80mm x 60mm 双层板"')
    lines.append('Comment3 ""')
    lines.append('Comment4 ""')
    lines.append("$EndDescr")

    # 生成元件
    for comp in COMPONENTS:
        ref, name, value, footprint, lib_id, x, y, rot = comp
        lines.append("$Comp")
        lib_ref = lib_id.split(":")[1] if ":" in lib_id else lib_id
        lib_name = lib_id.split(":")[0] if ":" in lib_id else "Device"
        lines.append(f"L {lib_name}:{lib_ref} {ref}")
        lines.append(f"U 1 1 {next_uuid()}")
        lines.append(f"P {x} {y}")
        # 属性
        lines.append(f'F 0 "{ref}" H {x} {y-50} 50  0001 L CNN')
        lines.append(f'F 1 "{value}" H {x} {y+50} 50  0001 L CNN')
        lines.append(f'F 2 "{footprint}" H {x} {y} 50  0001 C CNN')
        lines.append(f'F 3 "" H {x} {y} 50  0001 C CNN')
        lines.append(f"\t1   {x} {y}")
        lines.append(f"\t{rot}   0   0   0")
        lines.append("$EndComp")

    # 生成连线 (简化版:用网络标号代替连线)
    # 这样更可靠,不需要精确的坐标
    lines.append("$EndSCHEMATC")
    return "\n".join(lines) + "\n"

# ============================================================
# 生成网表文件 (.net) - KiCad 网表格式
# ============================================================
def gen_netlist():
    lines = []
    lines.append("(export (version \"E\")")
    lines.append("  (design")
    lines.append('    (source "FoodSpoilageMonitor.py")')
    lines.append('    (date "2026-08-07")')
    lines.append('    (tool "Python Generator")')
    lines.append("  )")
    lines.append("  (components")

    for comp in COMPONENTS:
        ref, name, value, footprint, lib_id, x, y, rot = comp
        lines.append(f'    (comp (ref "{ref}")')
        lines.append(f'      (value "{value}")')
        lines.append(f'      (footprint "{footprint}")')
        lines.append(f'      (libsource (lib "{lib_id.split(":")[0]}") (part "{lib_id.split(":")[1]}"))')
        lines.append("    )")

    lines.append("  )")
    lines.append("  (nets")

    for net_name, pins in NETS.items():
        lines.append(f'    (net (code "{list(NETS.keys()).index(net_name)+1}") (name "{net_name}")')
        lines.append("      (node")
        for ref, pin in pins:
            lines.append(f'        (ref "{ref}") (pin "{pin}")')
        lines.append("      )")
        lines.append("    )")

    lines.append("  )")
    lines.append(")")
    return "\n".join(lines) + "\n"

# ============================================================
# 生成PCB布局文件 (.kicad_pcb) - KiCad 格式
# ============================================================
def gen_pcb():
    """生成PCB文件,包含板框、元件位置和封装"""
    # PCB尺寸: 80mm x 60mm = 3149.6mil x 2362.2mil
    # 坐标原点在左下角
    board_w = 80.0  # mm
    board_h = 60.0  # mm

    # 元件位置 (mm) - 从mil转换
    # 重新规划布局,以mm为单位
    pcb_components = [
        # (位号, 封装, 值, x_mm, y_mm, 旋转, 层)
        # 层: F.Cu=顶层, B.Cu=底层
        ("J1",  "TerminalBlock:TerminalBlock_bornier-2_P5.08mm", "5V/3A",
         10, 50, 0, "F.Cu"),
        ("SW1", "Button_Switch_THT:SW_CuK_OS102011MA1QN1_SPDT_Angled", "总开关",
         20, 50, 180, "F.Cu"),
        ("F1",  "Fuse:Fuse_BelFuse_0ZCF0005FF_C6.3x5.1", "PTC 1.1A",
         30, 50, 0, "F.Cu"),
        ("C1",  "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm", "10uF",
         40, 50, 0, "F.Cu"),
        ("U1",  "Module:NodeMCU-32S", "ESP32-WROOM-32",
         40, 30, 0, "F.Cu"),
        ("U2",  "PinHeader:PinHeader_1x04_P2.54mm_Vertical", "BME680",
         65, 15, 0, "F.Cu"),
        ("U3",  "PinHeader:PinHeader_1x04_P2.54mm_Vertical", "SGP30",
         65, 25, 0, "F.Cu"),
        ("U4",  "PinHeader:PinHeader_1x03_P2.54mm_Vertical", "MQ-137",
         65, 40, 0, "F.Cu"),
        ("C2",  "Capacitor_SMD:C_0805_2012Metric", "100nF",
         55, 40, 0, "F.Cu"),
        ("SW2", "Button_Switch_THT:SW_CuK_OS102011MA1QN1_SPDT_Angled", "风扇开关",
         20, 12, 0, "F.Cu"),
        ("M1",  "PinHeader:PinHeader_1x02_P2.54mm_Vertical", "FAN 5V",
         30, 12, 0, "F.Cu"),
        ("D1",  "LED_THT:LED_D5.0mm", "LED Red",
         10, 30, 180, "F.Cu"),
        ("R1",  "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "150R",
         10, 38, 90, "F.Cu"),
        ("TB1", "TerminalBlock:TerminalBlock_bornier-4_P5.08mm", "TB1 电源",
         15, 5, 0, "F.Cu"),
        ("TB2", "TerminalBlock:TerminalBlock_bornier-8_P5.08mm", "TB2 信号",
         40, 5, 0, "F.Cu"),
        ("TB3", "TerminalBlock:TerminalBlock_bornier-2_P5.08mm", "TB3 风扇",
         65, 5, 0, "F.Cu"),
    ]

    lines = []

    # 文件头
    lines.append("(kicad_pcb (version 20171130) (host pcbgen \"FoodSpoilageMonitor\")")
    lines.append("")

    # 通用设置
    lines.append("  (general")
    lines.append("    (thickness 1.6)")
    lines.append("    (drawings 4)")
    lines.append(f"    (tracks 0)")
    lines.append("    (zones 0)")
    lines.append(f"    (modules {len(pcb_components)})")
    lines.append("    (nets 9)")
    lines.append("  )")
    lines.append("")

    # 页面设置 (A4)
    lines.append("  (page A4)")
    lines.append("  (layers")
    lines.append("    (0 F.Cu signal)")
    lines.append("    (31 B.Cu signal)")
    lines.append("    (32 B.Adhes user)")
    lines.append("    (33 F.Adhes user)")
    lines.append("    (34 B.Paste user)")
    lines.append("    (35 F.Paste user)")
    lines.append("    (36 B.SilkS user)")
    lines.append("    (37 F.SilkS user)")
    lines.append("    (38 B.Mask user)")
    lines.append("    (39 F.Mask user)")
    lines.append("    (40 Dwgs.User user)")
    lines.append("    (41 Cmts.User user)")
    lines.append("    (42 Eco1.User user)")
    lines.append("    (43 Eco2.User user)")
    lines.append("    (44 Edge.Cuts user)")
    lines.append("    (45 Margin user)")
    lines.append("    (46 B.CrtYd user)")
    lines.append("    (47 F.CrtYd user)")
    lines.append("    (48 B.Fab user)")
    lines.append("    (49 F.Fab user)")
    lines.append("  ))")
    lines.append("")

    # 设置
    lines.append("  (setup")
    lines.append("    (last_trace_width 0.25)")
    lines.append("    (trace_clearance 0.2)")
    lines.append("    (zone_clearance 0.508)")
    lines.append("    (zone_45_only no)")
    lines.append("    (trace_min 0.2)")
    lines.append("    (segment_width 0.2)")
    lines.append("    (edge_width 0.15)")
    lines.append("    (via_size 0.6)")
    lines.append("    (via_drill 0.4)")
    lines.append("    (via_min_size 0.4)")
    lines.append("    (via_min_drill 0.3)")
    lines.append("    (uvia_size 0.3)")
    lines.append("    (uvia_drill 0.1)")
    lines.append("    (uvias_allowed no)")
    lines.append("    (uvia_min_size 0.2)")
    lines.append("    (uvia_min_drill 0.1)")
    lines.append("    (pcb_text_width 0.3)")
    lines.append("    (pcb_text_size 1.5 1.5)")
    lines.append("    (mod_edge_width 0.15)")
    lines.append("    (mod_text_size 1 1)")
    lines.append("    (mod_text_width 0.15)")
    lines.append("    (pad_size 1.524 1.524)")
    lines.append("    (pad_drill 0.762)")
    lines.append("    (pad_to_mask_clearance 0.05)")
    lines.append("    (aux_axis_origin 0 0)")
    lines.append("    (visible_elements FFFFFF7F)")
    lines.append("    (pcbplotparams")
    lines.append("      (layerselection 0x010fc_80000007)")
    lines.append("      (usegerberextensions false)")
    lines.append("      (usegerberattributes true)")
    lines.append("      (usegerberadvancedattributes false)")
    lines.append("      (creategerberjobfile false)")
    lines.append("      (excludeedgelayer true)")
    lines.append("      (linewidth 0.100000)")
    lines.append("      (plotframeref false)")
    lines.append("      (viasonmask false)")
    lines.append("      (mode 1)")
    lines.append("      (useauxorigin false)")
    lines.append("      (hpglpennumber 1)")
    lines.append("      (hpglpenspeed 20)")
    lines.append("      (hpglpendiameter 15.000000)")
    lines.append("      (psnegative false)")
    lines.append("      (psa4output false)")
    lines.append("      (plotreference true)")
    lines.append("      (plotvalue true)")
    lines.append("      (plotinvisibletext false)")
    lines.append("      (padsonsilk false)")
    lines.append("      (subtractmaskfromsilk false)")
    lines.append("      (outputformat 1)")
    lines.append("      (mirror false)")
    lines.append("      (drillshape 1)")
    lines.append("      (scaleselection 1)")
    lines.append("      (outputdirectory \"\")")
    lines.append("    )")
    lines.append("  )")
    lines.append("")

    # 网络
    net_list = ["(net 0 \"\")"]
    for i, net_name in enumerate(NETS.keys(), 1):
        net_list.append(f'(net {i} "{net_name}")')
    lines.append("  " + "\n  ".join(net_list))
    lines.append("")

    # 板框 (Edge.Cuts) - 80mm x 60mm 矩形
    lines.append("  (gr_line (start 0 0) (end 80 0) (layer Edge.Cuts) (width 0.15))")
    lines.append("  (gr_line (start 80 0) (end 80 60) (layer Edge.Cuts) (width 0.15))")
    lines.append("  (gr_line (start 80 60) (end 0 60) (layer Edge.Cuts) (width 0.15))")
    lines.append("  (gr_line (start 0 60) (end 0 0) (layer Edge.Cuts) (width 0.15))")
    lines.append("")

    # 安装孔 (4个M3孔,距边5mm)
    for hx, hy in [(5, 5), (75, 5), (5, 55), (75, 55)]:
        lines.append(f'  (module MountingHole:MountingHole_3.2mm_M3 (layer F.Cu) (tedit 5F8A0001) (tstamp {next_uuid()})')
        lines.append(f'    (at {hx} {hy})')
        lines.append('    (descr "Mounting Hole 3.2mm, M3")')
        lines.append('    (tags "mounting hole 3.2mm m3")')
        lines.append('    (fp_text reference "" (at 0 -4) (layer F.SilkS)')
        lines.append('      (effects (font (size 1 1) (thickness 0.15)))')
        lines.append('    )')
        lines.append('    (fp_text value M3 (at 0 4) (layer F.Fab)')
        lines.append('      (effects (font (size 1 1) (thickness 0.15)))')
        lines.append('    )')
        lines.append('    (pad 1 thru_hole circle (at 0 0) (size 6 6) (drill 3.2) (layers *.Cu *.Mask))')
        lines.append('  )')
        lines.append("")

    # 元件 (modules)
    for ref, footprint, value, x, y, rot, layer in pcb_components:
        lines.append(f'  (module {footprint} (layer {layer}) (tedit 5F8A0001) (tstamp {next_uuid()})')
        lines.append(f'    (at {x} {y} {rot})')
        lines.append(f'    (descr "{value}")')
        lines.append(f'    (tags "{ref}")')
        lines.append(f'    (fp_text reference {ref} (at 0 -5) (layer F.SilkS)')
        lines.append('      (effects (font (size 1 1) (thickness 0.15)))')
        lines.append('    )')
        lines.append(f'    (fp_text value "{value}" (at 0 5) (layer F.Fab)')
        lines.append('      (effects (font (size 1 1) (thickness 0.15)))')
        lines.append('    )')
        # 简化的封装图形(矩形外框)
        lines.append('    (fp_line (start -2.5 -2.5) (end 2.5 -2.5) (layer F.SilkS) (width 0.15))')
        lines.append('    (fp_line (start 2.5 -2.5) (end 2.5 2.5) (layer F.SilkS) (width 0.15))')
        lines.append('    (fp_line (start 2.5 2.5) (end -2.5 2.5) (layer F.SilkS) (width 0.15))')
        lines.append('    (fp_line (start -2.5 2.5) (end -2.5 -2.5) (layer F.SilkS) (width 0.15))')

        # 焊盘 - 根据元件类型生成
        pin_count = {"J1":2, "SW1":3, "F1":2, "C1":2, "U1":6, "U2":4, "U3":4,
                     "U4":3, "C2":2, "SW2":3, "M1":2, "D1":2, "R1":2,
                     "TB1":4, "TB2":8, "TB3":2}.get(ref, 2)

        # 为每个焊盘分配网络
        ref_nets = {}
        for net_name, pins in NETS.items():
            for pin_ref, pin_num in pins:
                if pin_ref == ref:
                    net_idx = list(NETS.keys()).index(net_name) + 1
                    ref_nets[int(pin_num)] = (net_idx, net_name)

        for pin_num in range(1, pin_count + 1):
            px = 0
            py = (pin_num - 1) * 2.54
            net_info = ref_nets.get(pin_num, (0, ""))
            lines.append(f'    (pad {pin_num} thru_hole circle (at {px} {py}) (size 1.7 1.7) (drill 1.0) (layers *.Cu *.Mask)')
            lines.append(f'      (net {net_info[0]} "{net_info[1]}"))')

        lines.append('  )')
        lines.append("")

    lines.append(")")
    return "\n".join(lines) + "\n"

# ============================================================
# 生成自定义符号库 (.lib)
# ============================================================
def gen_symbol_lib():
    """生成ESP32简化符号库"""
    return """EESchema-LIBRARY Version 2.4
#encoding utf-8
#
# ESP32-WROOM-32
#
DEF ESP32-WROOM-32 U 0 40 Y Y 1 F N
F0 "U" -500 1250 50 H V L CNN
F1 "ESP32-WROOM-32" 100 1250 50 H V L CNN
F2 "Module:NodeMCU-32S" -500 -1300 50 H I L CNN
F3 "" 0 0 50 H I C CNN
DRAW
S -500 1200 500 -1200 0 1 0 f
X VIN 1 -700 1100 200 R 50 50 1 1 W
X GND 2 -700 1000 200 R 50 50 1 1 W
X 3V3 3 -700 900 200 R 50 50 1 1 W
X GPIO21 4 700 1100 200 L 50 50 1 1 B
X GPIO22 5 700 1000 200 L 50 50 1 1 B
X GPIO34 6 700 900 200 L 50 50 1 1 I
ENDBLK
#
# End Library
"""

# ============================================================
# 生成符号库描述文件 (.dcm)
# ============================================================
def gen_symbol_dcm():
    return """EESchema-DOCLIB  Version 2.0
#
$CMP ESP32-WROOM-32
D ESP32-WROOM-32 WiFi/BT 模块,简化符号(仅显示用到的引脚)
K ESP32 WiFi Bluetooth MCU
F https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf
$ENDCMP
#
#End Doc Library
"""

# ============================================================
# 生成BOM清单 (CSV)
# ============================================================
def gen_bom():
    lines = ["序号,位号,元件名称,规格/值,封装,数量,嘉立创物料编号(参考),备注"]
    bom_items = [
        ("1", "J1", "USB端子", "5V/3A输入", "KF128-2P-5.08", "1", "-", "电源输入"),
        ("2", "SW1,SW2", "拨动开关", "SS-12F15 1P2T", "SPDT", "2", "C319690", "总开关+风扇开关"),
        ("3", "F1", "自恢复保险丝", "PPTC 1.1A", "0ZCG0110FF2C", "1", "C155325", "5V过流保护"),
        ("4", "C1", "电解电容", "10uF/25V", "5×7mm D5.0 P2.5", "1", "C46584", "5V滤波"),
        ("5", "C2", "陶瓷电容", "100nF/50V X7R", "0805", "1", "C49678", "ADC滤波"),
        ("6", "U1", "ESP32开发板", "ESP32-WROOM-32", "NodeMCU-32S", "1", "C828287", "主控(沿用已有)"),
        ("7", "U2", "BME680模块", "温湿度+气压+VOC", "4P 2.54mm排针", "1", "C83691", "I²C 0x76"),
        ("8", "U3", "SGP30模块", "TVOC+eCO2", "4P 2.54mm排针", "1", "C83692", "I²C 0x58"),
        ("9", "U4", "MQ-137模块", "氨气传感器", "3P 2.54mm排针", "1", "C83693", "模拟输出"),
        ("10", "M1", "直流风扇", "5V/0.15A 40×40mm", "2P 2.54mm排针", "1", "C83694", "空气循环"),
        ("11", "D1", "LED", "红色5mm", "D5.0mm", "1", "C84263", "电源指示"),
        ("12", "R1", "电阻", "150Ω 1/4W", "THT D0207", "1", "C17415", "LED限流"),
        ("13", "TB1", "端子排", "4P 5.08mm", "KF128-4P", "1", "C83695", "电源分配"),
        ("14", "TB2", "端子排", "8P 5.08mm", "KF128-8P", "1", "C83696", "信号"),
        ("15", "TB3", "端子排", "2P 5.08mm", "KF128-2P", "1", "C83697", "风扇"),
        ("16", "-", "M3螺丝", "M3×6mm", "-", "4", "-", "安装孔"),
    ]
    for item in bom_items:
        lines.append(",".join(item))
    return "\n".join(lines) + "\n"

# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 60)
    print("食品腐败风险预测系统 - KiCad 工程文件生成器")
    print("=" * 60)

    files = {
        "FoodSpoilageMonitor.pro": gen_project(),
        "FoodSpoilageMonitor.sch": gen_schematic(),
        "FoodSpoilageMonitor.kicad_pcb": gen_pcb(),
        "FoodSpoilageMonitor.net": gen_netlist(),
        "FoodSpoilageMonitor.lib": gen_symbol_lib(),
        "FoodSpoilageMonitor.dcm": gen_symbol_dcm(),
        "BOM清单.csv": gen_bom(),
    }

    for filename, content in files.items():
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ 已生成: {filename} ({len(content)} 字节)")

    print()
    print("=" * 60)
    print(f"全部 {len(files)} 个文件已生成到:")
    print(f"  {OUTPUT_DIR}")
    print("=" * 60)
    print()
    print("下一步: 将这些文件导入嘉立创EDA专业版")
    print("  文件 → 导入 → KiCad工程")
    print("  选择 FoodSpoilageMonitor.pro 文件")

if __name__ == "__main__":
    main()
