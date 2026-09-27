#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
食品腐败风险预测系统 - KiCad 6 工程文件生成器
生成 KiCad 6 格式,兼容嘉立创EDA专业版

输出:
  - FoodSpoilageMonitor.kicad_pro  (工程文件 JSON)
  - FoodSpoilageMonitor.kicad_sch  (原理图 S-expression)
  - FoodSpoilageMonitor.kicad_pcb  (PCB布局)
  - FoodSpoilageMonitor.zip        (打包好的ZIP,直接导入用)
"""

import os
import json
import uuid as uuidlib
import zipfile

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def gen_uuid():
    return str(uuidlib.uuid4())

# ============================================================
# 1. 生成 .kicad_pro 工程文件 (JSON格式, KiCad 6)
# ============================================================
def gen_kicad_pro():
    pro = {
        "board": {
            "3dviewports": [],
            "design_settings": {
                "rules": {
                    "min_track_width": 0.2,
                    "min_via_diameter": 0.4,
                    "min_via_drill": 0.3
                }
            },
            "layer_presets": [],
            "viewports": []
        },
        "boards": [],
        "cvpcb": {
            "equivalence_files": []
        },
        "libraries": {
            "pinned_footprint_libs": [],
            "pinned_symbol_libs": []
        },
        "meta": {
            "filename": "FoodSpoilageMonitor.kicad_pro",
            "version": 1
        },
        "net_settings": {
            "classes": [
                {
                    "bus_width": 12,
                    "clearance": 0.2,
                    "diff_pair_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "Default",
                    "pcb_color": "rgba(0, 0, 0, 0.000)",
                    "schematic_color": "rgba(0, 0, 0, 0.000)",
                    "track_width": 0.25,
                    "via_diameter": 0.6,
                    "via_drill": 0.4,
                    "wire_width": 6
                },
                {
                    "bus_width": 12,
                    "clearance": 0.3,
                    "diff_pair_gap": 0.25,
                    "diff_pair_width": 0.2,
                    "line_style": 0,
                    "microvia_diameter": 0.3,
                    "microvia_drill": 0.1,
                    "name": "Power",
                    "pcb_color": "rgba(255, 0, 0, 1.000)",
                    "schematic_color": "rgba(255, 0, 0, 1.000)",
                    "track_width": 0.5,
                    "via_diameter": 0.8,
                    "via_drill": 0.5,
                    "wire_width": 10
                }
            ],
            "meta": {"version": 1},
            "net_colors": None,
            "netclass_assignments": None,
            "netclass_patterns": [
                {"netclass": "Power", "pattern": "+5V"},
                {"netclass": "Power", "pattern": "GND"},
                {"netclass": "Power", "pattern": "+3V3"}
            ]
        },
        "pcbnew": {
            "last_paths": {
                "gencad": "",
                "idf": "",
                "netlist": "",
                "specctra_dsn": "",
                "step": "",
                "vrml": ""
            },
            "page_layout_descr_file": ""
        },
        "schematic": {
            "annotate_start_num": 0,
            "drawing": {
                "dashing": 0,
                "default_line_thickness": 6.0,
                "default_text_size": 50.0,
                "field_names": [],
                "intersheets_ref_own_page": False,
                "intersheets_ref_prefix": "",
                "intersheets_ref_short": False,
                "intersheets_ref_show": False,
                "intersheets_ref_suffix": "",
                "junction_size_choice": 3,
                "label_size_ratio": 0.375,
                "pin_symbol_size": 25.0,
                "text_offset_ratio": 0.15
            },
            "legacy_lib_dir": "",
            "legacy_lib_list": [],
            "meta": {"version": 1},
            "page_format_descr": "A3"
        },
        "sheets": [],
        "text_variables": {}
    }
    return json.dumps(pro, indent=2, ensure_ascii=False)

# ============================================================
# 2. 符号库定义 (lib_symbols)
# ============================================================
def gen_lib_symbols():
    """生成所有用到的符号的完整定义"""
    return '''  (lib_symbols
    (symbol "Device:R"
      (pin_numbers hide)
      (pin_names (offset 0))
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "R" (at 2.032 0 90)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "R" (at 0 0 90)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 1.778 0 90)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "~" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "R_0_1"
        (rectangle (start -1.016 -2.54) (end 1.016 2.54)
          (stroke (width 0.254) (type default))
          (fill (type none))
        )
      )
      (symbol "R_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 0 -3.81 90) (length 1.27)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "Device:C"
      (pin_numbers hide)
      (pin_names (offset 0.254))
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "C" (at 0.635 2.54 0)
        (effects (font (size 1.27 1.27)) (justify left))
      )
      (property "Value" "C" (at 0.635 -2.54 0)
        (effects (font (size 1.27 1.27)) (justify left))
      )
      (property "Footprint" "" (at 0.762 -1.016 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "~" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "C_0_1"
        (polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762))
          (stroke (width 0.508) (type default))
          (fill (type none))
        )
        (polyline (pts (xy -2.032 0.762) (xy 2.032 0.762))
          (stroke (width 0.508) (type default))
          (fill (type none))
        )
      )
      (symbol "C_1_1"
        (pin passive line (at 0 3.81 270) (length 2.286)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 0 -3.81 90) (length 2.286)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "Device:CP"
      (pin_numbers hide)
      (pin_names (offset 0.254))
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "C" (at 0.635 2.54 0)
        (effects (font (size 1.27 1.27)) (justify left))
      )
      (property "Value" "CP" (at 0.635 -2.54 0)
        (effects (font (size 1.27 1.27)) (justify left))
      )
      (property "Footprint" "" (at 0.762 -1.016 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "~" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "CP_0_1"
        (rectangle (start -2.286 0.508) (end 2.286 1.016)
          (stroke (width 0) (type default))
          (fill (type outline))
        )
        (rectangle (start -2.286 -1.016) (end 2.286 -0.508)
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline (pts (xy -1.778 2.286) (xy -0.762 2.286))
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline (pts (xy -1.27 2.794) (xy -1.27 1.778)
          (stroke (width 0) (type default))
          (fill (type none))
        )
      )
      (symbol "CP_1_1"
        (pin passive line (at 0 3.81 270) (length 2.794)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 0 -3.81 90) (length 2.794)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "Device:LED"
      (pin_numbers hide)
      (pin_names (offset 1.016) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "D" (at 0 2.54 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "LED" (at 0 -2.54 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "~" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "LED_0_1"
        (polyline (pts (xy -1.27 -1.27) (xy -1.27 1.27))
          (stroke (width 0.254) (type default))
          (fill (type none))
        )
        (polyline (pts (xy -1.27 0) (xy 1.27 0))
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline (pts (xy 1.27 -1.27) (xy 1.27 1.27) (xy -1.27 0) (xy 1.27 -1.27))
          (stroke (width 0.254) (type default))
          (fill (type outline))
        )
        (polyline (pts (xy -3.048 -0.762) (xy -4.572 -2.286) (xy -3.81 -2.286) (xy -4.572 -2.286) (xy -4.572 -1.524))
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline (pts (xy -1.778 -0.762) (xy -3.302 -2.286) (xy -2.54 -2.286) (xy -3.302 -2.286) (xy -3.302 -1.524))
          (stroke (width 0) (type default))
          (fill (type none))
        )
      )
      (symbol "LED_1_1"
        (pin passive line (at -3.81 0 0) (length 2.54)
          (name "K" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 0 180) (length 2.54)
          (name "A" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "Device:Polyfuse"
      (pin_numbers hide)
      (pin_names (offset 0))
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "F" (at 0 3.81 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "Polyfuse" (at 0 -3.81 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 0 1.27 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "~" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "Polyfuse_0_1"
        (rectangle (start -2.54 1.27) (end 2.54 -1.27)
          (stroke (width 0.254) (type default))
          (fill (type none))
        )
        (polyline (pts (xy -2.54 0) (xy 2.54 0))
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline (pts (xy 0 -1.27) (xy 0 -2.54))
          (stroke (width 0) (type default))
          (fill (type none))
        )
      )
      (symbol "Polyfuse_1_1"
        (pin passive line (at -5.08 0 0) (length 2.54)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 5.08 0 180) (length 2.54)
          (name "~" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "Switch:SW_SPDT"
      (pin_names (offset 0) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "SW" (at 0 4.064 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "SW_SPDT" (at 0 -5.08 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "~" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "SW_SPDT_0_1"
        (circle (center -3.81 0) (radius 0.508)
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (circle (center 3.81 1.27) (radius 0.508)
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (circle (center 3.81 -1.27) (radius 0.508)
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline (pts (xy -3.302 0.508) (xy 3.302 1.27))
          (stroke (width 0.254) (type default))
          (fill (type none))
        )
      )
      (symbol "SW_SPDT_1_1"
        (pin passive line (at -6.35 0 0) (length 2.54)
          (name "A" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 6.35 1.27 180) (length 2.54)
          (name "B" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 6.35 -1.27 180) (length 2.54)
          (name "C" (effects (font (size 1.27 1.27))))
          (number "3" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "Connector_Generic:Conn_01x02"
      (pin_names (offset 1.016) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "J" (at 0 2.54 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "Conn_01x02" (at 0 -5.08 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "~" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "Conn_01x02_1_1"
        (rectangle (start -1.27 1.27) (end 1.27 -3.81)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
        (pin passive line (at 3.81 0 180) (length 2.54)
          (name "Pin_1" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 -2.54 180) (length 2.54)
          (name "Pin_2" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "Connector_Generic:Conn_01x03"
      (pin_names (offset 1.016) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "J" (at 0 5.08 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "Conn_01x03" (at 0 -7.62 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "~" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "Conn_01x03_1_1"
        (rectangle (start -1.27 3.81) (end 1.27 -6.35)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
        (pin passive line (at 3.81 2.54 180) (length 2.54)
          (name "Pin_1" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 0 180) (length 2.54)
          (name "Pin_2" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 -2.54 180) (length 2.54)
          (name "Pin_3" (effects (font (size 1.27 1.27))))
          (number "3" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "Connector_Generic:Conn_01x04"
      (pin_names (offset 1.016) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "J" (at 0 5.08 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "Conn_01x04" (at 0 -7.62 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "~" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "Conn_01x04_1_1"
        (rectangle (start -1.27 3.81) (end 1.27 -6.35)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
        (pin passive line (at 3.81 2.54 180) (length 2.54)
          (name "Pin_1" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 0 180) (length 2.54)
          (name "Pin_2" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 -2.54 180) (length 2.54)
          (name "Pin_3" (effects (font (size 1.27 1.27))))
          (number "3" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 -5.08 180) (length 2.54)
          (name "Pin_4" (effects (font (size 1.27 1.27))))
          (number "4" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "Connector_Generic:Conn_01x08"
      (pin_names (offset 1.016) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "J" (at 0 10.16 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "Conn_01x08" (at 0 -12.7 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "~" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "Conn_01x08_1_1"
        (rectangle (start -1.27 8.89) (end 1.27 -11.43)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
        (pin passive line (at 3.81 7.62 180) (length 2.54)
          (name "Pin_1" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 5.08 180) (length 2.54)
          (name "Pin_2" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 2.54 180) (length 2.54)
          (name "Pin_3" (effects (font (size 1.27 1.27))))
          (number "3" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 0 180) (length 2.54)
          (name "Pin_4" (effects (font (size 1.27 1.27))))
          (number "4" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 -2.54 180) (length 2.54)
          (name "Pin_5" (effects (font (size 1.27 1.27))))
          (number "5" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 -5.08 180) (length 2.54)
          (name "Pin_6" (effects (font (size 1.27 1.27))))
          (number "6" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 -7.62 180) (length 2.54)
          (name "Pin_7" (effects (font (size 1.27 1.27))))
          (number "7" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 3.81 -10.16 180) (length 2.54)
          (name "Pin_8" (effects (font (size 1.27 1.27))))
          (number "8" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "power:+5V"
      (power)
      (pin_numbers hide)
      (pin_names (offset 0) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "#PWR" (at 0 -3.81 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Value" "+5V" (at 0 3.556 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "+5V_0_1"
        (polyline (pts (xy -0.762 1.27) (xy 0 2.54))
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline (pts (xy 0 0) (xy 0 2.54))
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline (pts (xy 0 2.54) (xy 0.762 1.27))
          (stroke (width 0) (type default))
          (fill (type none))
        )
      )
      (symbol "+5V_1_1"
        (pin power_in line (at 0 0 90) (length 0) hide
          (name "+5V" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "power:+3V3"
      (power)
      (pin_numbers hide)
      (pin_names (offset 0) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "#PWR" (at 0 -3.81 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Value" "+3V3" (at 0 3.556 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "+3V3_0_1"
        (polyline (pts (xy -0.762 1.27) (xy 0 2.54))
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline (pts (xy 0 0) (xy 0 2.54))
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline (pts (xy 0 2.54) (xy 0.762 1.27))
          (stroke (width 0) (type default))
          (fill (type none))
        )
      )
      (symbol "+3V3_1_1"
        (pin power_in line (at 0 0 90) (length 0) hide
          (name "+3V3" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
      )
    )
    (symbol "power:GND"
      (power)
      (pin_numbers hide)
      (pin_names (offset 0) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "#PWR" (at 0 -6.35 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Value" "GND" (at 0 -3.81 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "" (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "GND_0_1"
        (polyline (pts (xy -1.27 0) (xy 0 -1.27) (xy 1.27 0) (xy -1.27 0))
          (stroke (width 0.254) (type default))
          (fill (type outline))
        )
        (polyline (pts (xy -1.524 -1.27) (xy 1.524 -1.27))
          (stroke (width 0.254) (type default))
          (fill (type none))
        )
        (polyline (pts (xy -0.508 -2.032) (xy 0.508 -2.032))
          (stroke (width 0.254) (type default))
          (fill (type none))
        )
      )
      (symbol "GND_1_1"
        (pin power_in line (at 0 0 270) (length 0) hide
          (name "GND" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
      )
    )
  )'''

# ============================================================
# 3. 元件定义 (symbol instances)
# 坐标单位: mm, 原理图坐标
# ============================================================
# (ref, lib_id, value, footprint, x, y, rotation, pin_connections)
# pin_connections: {pin_num: net_name}
COMPONENTS = [
    ("J1",  "Connector_Generic:Conn_01x02", "5V/3A",
     "TerminalBlock:TerminalBlock_bornier-2_P5.08mm", 25, 25, 0,
     {"1":"+5V", "2":"GND"}),
    ("SW1", "Switch:SW_SPDT", "总开关",
     "Button_Switch_THT:SW_CuK_OS102011MA1QN1_SPDT_Angled", 50, 25, 0,
     {"1":"+5V", "2":"Net-SW1F1", "3":""}),
    ("F1",  "Device:Polyfuse", "1.1A",
     "Fuse:Fuse_BelFuse_0ZCF0005FF_C6.3x5.1", 75, 25, 0,
     {"1":"Net-SW1F1", "2":"+5V"}),
    ("C1",  "Device:CP", "10uF",
     "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm", 100, 25, 0,
     {"1":"+5V", "2":"GND"}),
    ("U1",  "Connector_Generic:Conn_01x04", "ESP32",
     "PinHeader:PinHeader_1x06_P2.54mm_Vertical", 100, 60, 0,
     {"1":"+5V", "2":"GND", "3":"+3V3", "4":"SDA", "5":"SCL", "6":"NH3_AO"}),
    ("U2",  "Connector_Generic:Conn_01x04", "BME680",
     "PinHeader:PinHeader_1x04_P2.54mm_Vertical", 150, 35, 0,
     {"1":"+3V3", "2":"GND", "3":"SDA", "4":"SCL"}),
    ("U3",  "Connector_Generic:Conn_01x04", "SGP30",
     "PinHeader:PinHeader_1x04_P2.54mm_Vertical", 150, 55, 0,
     {"1":"+3V3", "2":"GND", "3":"SDA", "4":"SCL"}),
    ("U4",  "Connector_Generic:Conn_01x03", "MQ-137",
     "PinHeader:PinHeader_1x03_P2.54mm_Vertical", 150, 80, 0,
     {"1":"+5V", "2":"GND", "3":"NH3_AO"}),
    ("C2",  "Device:C", "100nF",
     "Capacitor_SMD:C_0805_2012Metric", 130, 80, 0,
     {"1":"NH3_AO", "2":"GND"}),
    ("SW2", "Switch:SW_SPDT", "风扇开关",
     "Button_Switch_THT:SW_CuK_OS102011MA1QN1_SPDT_Angled", 50, 90, 0,
     {"1":"+5V", "2":"FAN_OUT", "3":""}),
    ("M1",  "Connector_Generic:Conn_01x02", "FAN",
     "PinHeader:PinHeader_1x02_P2.54mm_Vertical", 80, 90, 0,
     {"1":"FAN_OUT", "2":"GND"}),
    ("D1",  "Device:LED", "Red",
     "LED_THT:LED_D5.0mm", 25, 55, 0,
     {"1":"GND", "2":"LED_A"}),
    ("R1",  "Device:R", "150R",
     "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", 25, 40, 0,
     {"1":"+5V", "2":"LED_A"}),
]

# ============================================================
# 4. 生成 .kicad_sch 原理图 (KiCad 6 S-expression)
# ============================================================
def gen_schematic():
    lines = []
    lines.append('(kicad_sch')
    lines.append('  (version 20211123)')
    lines.append('  (generator "python_gen")')
    lines.append(f'  (uuid "{gen_uuid()}")')
    lines.append('  (paper "A3")')
    lines.append('  (title_block')
    lines.append('    (title "食品腐败风险预测系统")')
    lines.append('    (date "2026-08-07")')
    lines.append('    (rev "1.0")')
    lines.append('    (company "FSM")')
    lines.append('    (comment 1 "ESP32 + BME680 + SGP30 + MQ-137")')
    lines.append('    (comment 2 "5V/3A USB充电头供电")')
    lines.append('  )')

    # lib_symbols
    lines.append(gen_lib_symbols())

    # 元件 (symbol instances)
    for ref, lib_id, value, footprint, x, y, rot, pins in COMPONENTS:
        lines.append(f'  (symbol')
        lines.append(f'    (lib_id "{lib_id}")')
        lines.append(f'    (at {x} {y} {rot})')
        lines.append(f'    (unit 1)')
        lines.append(f'    (in_bom yes)')
        lines.append(f'    (on_board yes)')
        lines.append(f'    (dnp no)')
        lines.append(f'    (uuid "{gen_uuid()}")')
        lines.append(f'    (property "Reference" "{ref}" (at {x+2} {y-2} 0)')
        lines.append(f'      (effects (font (size 1.27 1.27)))')
        lines.append(f'    )')
        lines.append(f'    (property "Value" "{value}" (at {x+2} {y+2} 0)')
        lines.append(f'      (effects (font (size 1.27 1.27)))')
        lines.append(f'    )')
        lines.append(f'    (property "Footprint" "{footprint}" (at {x} {y+4} 0)')
        lines.append(f'      (effects (font (size 1.27 1.27)) hide)')
        lines.append(f'    )')
        lines.append(f'    (property "Datasheet" "~" (at {x} {y} 0)')
        lines.append(f'      (effects (font (size 1.27 1.27)) hide)')
        lines.append(f'    )')
        for pin_num, net_name in pins.items():
            if net_name:
                lines.append(f'    (pin "{pin_num}" (uuid "{gen_uuid()}"))')
        lines.append(f'    (instances')
        lines.append(f'      (project "FoodSpoilageMonitor"')
        lines.append(f'        (path "/{gen_uuid()}"')
        lines.append(f'          (reference "{ref}")')
        lines.append(f'          (unit 1)')
        lines.append(f'        )')
        lines.append(f'      )')
        lines.append(f'    )')
        lines.append(f'  )')

    # 网络标号 (labels) - 用标签代替连线
    # 在每个元件的引脚位置放标签
    label_positions = set()
    for ref, lib_id, value, footprint, x, y, rot, pins in COMPONENTS:
        for pin_num, net_name in pins.items():
            if net_name and net_name not in label_positions:
                # 电源网络用power symbol, 其他用label
                if net_name in ("+5V", "+3V3", "GND"):
                    # 添加power symbol
                    power_sym = net_name
                    px = x - 5
                    py = y + int(pin_num) * 2.54
                    lines.append(f'  (symbol')
                    lines.append(f'    (lib_id "power:{power_sym}")')
                    lines.append(f'    (at {px} {py} 0)')
                    lines.append(f'    (unit 1)')
                    lines.append(f'    (in_bom yes)')
                    lines.append(f'    (on_board yes)')
                    lines.append(f'    (dnp no)')
                    lines.append(f'    (uuid "{gen_uuid()}")')
                    lines.append(f'    (property "Reference" "#PWR{len(label_positions)+1:02d}" (at {px} {py-3} 0)')
                    lines.append(f'      (effects (font (size 1.27 1.27)) hide)')
                    lines.append(f'    )')
                    lines.append(f'    (property "Value" "{power_sym}" (at {px} {py+3} 0)')
                    lines.append(f'      (effects (font (size 1.27 1.27)))')
                    lines.append(f'    )')
                    lines.append(f'    (pin "1" (uuid "{gen_uuid()}"))')
                    lines.append(f'    (instances')
                    lines.append(f'      (project "FoodSpoilageMonitor"')
                    lines.append(f'        (path "/{gen_uuid()}")')
                    lines.append(f'      )')
                    lines.append(f'    )')
                    lines.append(f'  )')
                    label_positions.add(net_name)
                else:
                    # 普通网络用label
                    lx = x + 5
                    ly = y
                    lines.append(f'  (label "{net_name}" (at {lx} {ly} 0)')
                    lines.append(f'    (effects (font (size 1.27 1.27)) (justify left bottom))')
                    lines.append(f'  )')
                    label_positions.add(net_name)

    # sheet_instances
    lines.append('  (sheet_instances')
    lines.append(f'    (path "/" (page "1"))')
    lines.append('  )')
    lines.append(')')

    return "\n".join(lines) + "\n"

# ============================================================
# 5. 生成 .kicad_pcb PCB文件 (KiCad 6格式, footprint)
# ============================================================
def gen_pcb():
    lines = []
    lines.append('(kicad_pcb')
    lines.append('  (version 20211014)')
    lines.append('  (generator "python_gen")')
    lines.append('')
    lines.append('  (general')
    lines.append('    (thickness 1.6)')
    lines.append('    (legacy_teardrops no)')
    lines.append('  )')
    lines.append('')
    lines.append('  (paper "A4")')
    lines.append('  (layers')
    lines.append('    (0 "F.Cu" signal)')
    lines.append('    (31 "B.Cu" signal)')
    lines.append('    (32 "B.Adhes" user "B.Adhesive")')
    lines.append('    (33 "F.Adhes" user "F.Adhesive")')
    lines.append('    (34 "B.Paste" user)')
    lines.append('    (35 "F.Paste" user)')
    lines.append('    (36 "B.SilkS" user "B.Silkscreen")')
    lines.append('    (37 "F.SilkS" user "F.Silkscreen")')
    lines.append('    (38 "B.Mask" user)')
    lines.append('    (39 "F.Mask" user)')
    lines.append('    (40 "Dwgs.User" user "User.Drawings")')
    lines.append('    (41 "Cmts.User" user "User.Comments")')
    lines.append('    (42 "Eco1.User" user "User.Eco1")')
    lines.append('    (43 "Eco2.User" user "User.Eco2")')
    lines.append('    (44 "Edge.Cuts" user)')
    lines.append('    (45 "Margin" user)')
    lines.append('    (46 "B.CrtYd" user "B.Courtyard")')
    lines.append('    (47 "F.CrtYd" user "F.Courtyard")')
    lines.append('    (48 "B.Fab" user)')
    lines.append('    (49 "F.Fab" user)')
    lines.append('  )')
    lines.append('')
    lines.append('  (setup')
    lines.append('    (stackup')
    lines.append('      (layer "F.SilkS" (type "Top Silk Screen"))')
    lines.append('      (layer "F.Paste" (type "Top Solder Paste"))')
    lines.append('      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))')
    lines.append('      (layer "F.Cu" (type "copper") (thickness 0.035))')
    lines.append('      (layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4"))')
    lines.append('      (layer "B.Cu" (type "copper") (thickness 0.035))')
    lines.append('      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))')
    lines.append('      (layer "B.Paste" (type "Bottom Solder Paste"))')
    lines.append('      (layer "B.SilkS" (type "Bottom Silk Screen"))')
    lines.append('      (copper_finish "None")')
    lines.append('      (dielectric_constraints no)')
    lines.append('    )')
    lines.append('    (pad_to_mask_clearance 0)')
    lines.append('    (allow_soldermask_bridges_in_footprints no)')
    lines.append('    (pcbplotparams')
    lines.append('      (layerselection 0x010fc_ffffffff)')
    lines.append('      (plot_on_all_layers_selection 0x0000000_00000000)')
    lines.append('      (disableapertmacroscale false)')
    lines.append('      (usegerberextensions false)')
    lines.append('      (usegerberattributes true)')
    lines.append('      (usegerberadvancedattributes true)')
    lines.append('      (creategerberjobfile true)')
    lines.append('      (dashed_line_dash_ratio 12.000000)')
    lines.append('      (dashed_line_gap_ratio 3.000000)')
    lines.append('      (svgprecision 4)')
    lines.append('      (plotframeref false)')
    lines.append('      (viasonmask false)')
    lines.append('      (mode 1)')
    lines.append('      (useauxorigin false)')
    lines.append('      (hpglpenum 1)')
    lines.append('      (hpglpenspeed 20)')
    lines.append('      (hpglpendiameter 15.000000)')
    lines.append('      (pdf_front_fp_property_popups true)')
    lines.append('      (pdf_back_fp_property_popups true)')
    lines.append('      (dxfpolygonmode true)')
    lines.append('      (dxfimperialunits true)')
    lines.append('      (dxfusepcbtruefont false)')
    lines.append('      (psnegative false)')
    lines.append('      (psa4output false)')
    lines.append('      (plotreference true)')
    lines.append('      (plotvalue true)')
    lines.append('      (plotfptext true)')
    lines.append('      (plotinvisibletext false)')
    lines.append('      (padsonsilk false)')
    lines.append('      (subtractmaskfromsilk false)')
    lines.append('      (outputformat 1)')
    lines.append('      (mirror false)')
    lines.append('      (drillshape 1)')
    lines.append('      (scaleselection 1)')
    lines.append('      (outputdirectory "")')
    lines.append('    )')
    lines.append('  )')
    lines.append('')
    # 网络
    lines.append('  (net 0 "")')
    nets = ["+5V", "GND", "+3V3", "SDA", "SCL", "NH3_AO", "FAN_OUT", "LED_A", "Net-SW1F1"]
    for i, n in enumerate(nets, 1):
        lines.append(f'  (net {i} "{n}")')
    lines.append('')

    # 板框 80x60mm
    lines.append('  (gr_line (start 0 0) (end 80 0)')
    lines.append('    (stroke (width 0.15) (type default))')
    lines.append('    (layer "Edge.Cuts") (uuid "{}"))'.format(gen_uuid()))
    lines.append('  (gr_line (start 80 0) (end 80 60)')
    lines.append('    (stroke (width 0.15) (type default))')
    lines.append('    (layer "Edge.Cuts") (uuid "{}"))'.format(gen_uuid()))
    lines.append('  (gr_line (start 80 60) (end 0 60)')
    lines.append('    (stroke (width 0.15) (type default))')
    lines.append('    (layer "Edge.Cuts") (uuid "{}"))'.format(gen_uuid()))
    lines.append('  (gr_line (start 0 60) (end 0 0)')
    lines.append('    (stroke (width 0.15) (type default))')
    lines.append('    (layer "Edge.Cuts") (uuid "{}"))'.format(gen_uuid()))
    lines.append('')

    # 安装孔
    for hx, hy in [(5, 5), (75, 5), (5, 55), (75, 55)]:
        lines.append(f'  (footprint "MountingHole:MountingHole_3.2mm_M3"')
        lines.append(f'    (layer "F.Cu")')
        lines.append(f'    (uuid "{gen_uuid()}")')
        lines.append(f'    (at {hx} {hy})')
        lines.append(f'    (descr "Mounting Hole 3.2mm, M3")')
        lines.append(f'    (property "Reference" "REF" (at 0 -4 (layer "F.SilkS"))')
        lines.append(f'      (effects (font (size 1 1) (thickness 0.15)))')
        lines.append(f'    )')
        lines.append(f'    (property "Value" "M3" (at 0 4 (layer "F.Fab"))')
        lines.append(f'      (effects (font (size 1 1) (thickness 0.15)))')
        lines.append(f'    )')
        lines.append(f'    (pad "1" thru_hole circle (at 0 0) (size 6 6) (drill 3.2) (layers "*.Cu" "*.Mask"))')
        lines.append(f'  )')
        lines.append('')

    # 元件 (footprint)
    pcb_components = [
        ("J1",  "TerminalBlock:TerminalBlock_bornier-2_P5.08mm", "5V/3A",      10, 50, 0, {"1":"+5V","2":"GND"}),
        ("SW1", "Button_Switch_THT:SW_CuK_OS102011MA1QN1_SPDT_Angled", "总开关", 20, 50, 180, {"1":"+5V","2":"Net-SW1F1","3":""}),
        ("F1",  "Fuse:Fuse_BelFuse_0ZCF0005FF_C6.3x5.1", "PTC 1.1A",     30, 50, 0, {"1":"Net-SW1F1","2":"+5V"}),
        ("C1",  "Capacitor_THT:CP_Radial_D5.0mm_P2.50mm", "10uF",       40, 50, 0, {"1":"+5V","2":"GND"}),
        ("U1",  "PinHeader:PinHeader_1x06_P2.54mm_Vertical", "ESP32",    40, 30, 0, {"1":"+5V","2":"GND","3":"+3V3","4":"SDA","5":"SCL","6":"NH3_AO"}),
        ("U2",  "PinHeader:PinHeader_1x04_P2.54mm_Vertical", "BME680",   65, 15, 0, {"1":"+3V3","2":"GND","3":"SDA","4":"SCL"}),
        ("U3",  "PinHeader:PinHeader_1x04_P2.54mm_Vertical", "SGP30",    65, 25, 0, {"1":"+3V3","2":"GND","3":"SDA","4":"SCL"}),
        ("U4",  "PinHeader:PinHeader_1x03_P2.54mm_Vertical", "MQ-137",   65, 40, 0, {"1":"+5V","2":"GND","3":"NH3_AO"}),
        ("C2",  "Capacitor_SMD:C_0805_2012Metric", "100nF",             55, 40, 0, {"1":"NH3_AO","2":"GND"}),
        ("SW2", "Button_Switch_THT:SW_CuK_OS102011MA1QN1_SPDT_Angled", "风扇开关", 20, 12, 0, {"1":"+5V","2":"FAN_OUT","3":""}),
        ("M1",  "PinHeader:PinHeader_1x02_P2.54mm_Vertical", "FAN 5V",  30, 12, 0, {"1":"FAN_OUT","2":"GND"}),
        ("D1",  "LED_THT:LED_D5.0mm", "LED Red",                      10, 30, 180, {"1":"GND","2":"LED_A"}),
        ("R1",  "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "150R", 10, 38, 90, {"1":"+5V","2":"LED_A"}),
        ("TB1", "TerminalBlock:TerminalBlock_bornier-4_P5.08mm", "TB1",  15, 5, 0, {"1":"+5V","2":"GND","3":"+5V","4":"+3V3"}),
        ("TB2", "TerminalBlock:TerminalBlock_bornier-8_P5.08mm", "TB2",  40, 5, 0, {"1":"SDA","2":"SCL","3":"NH3_AO","4":"GND","5":"+3V3","6":"+5V","7":"GND","8":""}),
        ("TB3", "TerminalBlock:TerminalBlock_bornier-2_P5.08mm", "TB3",  65, 5, 0, {"1":"FAN_OUT","2":"GND"}),
    ]

    for ref, fp, val, x, y, rot, pins in pcb_components:
        lines.append(f'  (footprint "{fp}"')
        lines.append(f'    (layer "F.Cu")')
        lines.append(f'    (uuid "{gen_uuid()}")')
        lines.append(f'    (at {x} {y} {rot})')
        lines.append(f'    (descr "{val}")')
        lines.append(f'    (tags "{ref}")')
        lines.append(f'    (property "Reference" "{ref}" (at 0 -5 (layer "F.SilkS"))')
        lines.append(f'      (effects (font (size 1 1) (thickness 0.15)))')
        lines.append(f'    )')
        lines.append(f'    (property "Value" "{val}" (at 0 5 (layer "F.Fab"))')
        lines.append(f'      (effects (font (size 1 1) (thickness 0.15)))')
        lines.append(f'    )')
        # 简化的丝印外框
        lines.append(f'    (fp_line (start -2.5 -2.5) (end 2.5 -2.5)')
        lines.append(f'      (stroke (width 0.15) (type default))')
        lines.append(f'      (layer "F.SilkS") (uuid "{gen_uuid()}"))')
        lines.append(f'    (fp_line (start 2.5 -2.5) (end 2.5 2.5)')
        lines.append(f'      (stroke (width 0.15) (type default))')
        lines.append(f'      (layer "F.SilkS") (uuid "{gen_uuid()}"))')
        lines.append(f'    (fp_line (start 2.5 2.5) (end -2.5 2.5)')
        lines.append(f'      (stroke (width 0.15) (type default))')
        lines.append(f'      (layer "F.SilkS") (uuid "{gen_uuid()}"))')
        lines.append(f'    (fp_line (start -2.5 2.5) (end -2.5 -2.5)')
        lines.append(f'      (stroke (width 0.15) (type default))')
        lines.append(f'      (layer "F.SilkS") (uuid "{gen_uuid()}"))')
        # 焊盘
        for pin_num, net_name in pins.items():
            px = 0
            py = (int(pin_num) - 1) * 2.54
            net_idx = nets.index(net_name) + 1 if net_name in nets else 0
            lines.append(f'    (pad "{pin_num}" thru_hole circle (at {px} {py})')
            lines.append(f'      (size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask")')
            if net_name:
                lines.append(f'      (net {net_idx} "{net_name}"))')
            else:
                lines.append(f'    )')
        lines.append(f'  )')
        lines.append('')

    lines.append(')')
    return "\n".join(lines) + "\n"

# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 60)
    print("KiCad 6 工程文件生成器 (兼容嘉立创EDA专业版)")
    print("=" * 60)

    files = {}
    files["FoodSpoilageMonitor.kicad_pro"] = gen_kicad_pro()
    files["FoodSpoilageMonitor.kicad_sch"] = gen_schematic()
    files["FoodSpoilageMonitor.kicad_pcb"] = gen_pcb()

    # 写文件
    for filename, content in files.items():
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ {filename} ({len(content)} bytes)")

    # 打包ZIP
    zip_path = os.path.join(OUTPUT_DIR, "FoodSpoilageMonitor.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in files.keys():
            filepath = os.path.join(OUTPUT_DIR, filename)
            zf.write(filepath, filename)
    print(f"  ✓ FoodSpoilageMonitor.zip (打包完成)")

    print()
    print("=" * 60)
    print("导入方法:")
    print("  方式1: 嘉立创EDA → 文件 → 导入 → KiCad → 选ZIP文件")
    print("  方式2: 嘉立创EDA → 文件 → 导入 → KiCad → 选.kicad_pcb")
    print("=" * 60)

if __name__ == "__main__":
    main()
