# -*- coding: utf-8 -*-
"""Constantes y mapeos para machine_recipes."""
from .base import BASE_DIR
import os

RECIPES_DIR = os.path.join(BASE_DIR, "machine_recipes")
HISTORY_CSV = os.path.join(RECIPES_DIR, "_history.csv")
os.makedirs(RECIPES_DIR, exist_ok=True)

DATA_SCHEMA_VERSION = 2

# ---------- Excel helpers ----------
EXCEL_MAP = {
    # ---------- Encabezado ----------
    "program": "DEFG:4",
    "mould_desig": "DEFG:5",
    "material": "DEFG:6",
    "date_of_entry": "KLMNO:4",
    "cavities": "KLMNO:5",
    "machine": "KLMNO:6",

    # ---------- Injection unit / Key data (superior) ----------
    "screw_diameter_mm": "J:9",

    # Key data (N–O)
    "cycle_time_s": "NO:8",
    "injection_time_s": "NO:9",
    "holding_press_time_s": "NO:10",
    "rem_cooling_time_s": "NO:11",
    "dosage_time_s": "NO:12",
    "screw_stroke_mm": "NO:13",
    "mould_stroke_mm": "NO:14",
    "ejector_stroke_mm": "NO:15",
    "shot_weight_g": "NO:16",
    "plasticising_flow_kg_h": "NO:17",
    "dosage_capacity_g_s": "NO:18",
    "dosage_volume_ccm": "NO:19",
    "material_cushion_ccm": "NO:20",
    "max_injection_pressure_bar": "NO:21",

    # ---------- Injection (filas 11–15) ----------
    "inj_press_limit_bar_1": "I:11",
    "inj_press_limit_bar_2": "H:11",
    "inj_press_limit_bar_3": "G:11",

    "injection_speed_1": "I:12",
    "injection_speed_2": "H:12",
    "injection_speed_3": "G:12",

    "end_of_stage_mm_1": "I:13",
    "end_of_stage_mm_2": "H:13",
    "end_of_stage_mm_3": "G:13",

    "injection_flow_ccm_s_1": "I:14",
    "injection_flow_ccm_s_2": "H:14",
    "injection_flow_ccm_s_3": "G:14",

    "end_of_stage_ccm_1": "I:15",
    "end_of_stage_ccm_2": "H:15",
    "end_of_stage_ccm_3": "G:15",

    # ---------- Plasticizing (filas 18–20) ----------
    "screw_speed_m_min_1": "E:18",
    "back_pressure_bar": "E:19",
    "plasticizing_end_stage_ccm": "E:20",

    # ---------- Holding pressure (filas 23–24) ----------
    "hold_time_s_1": "F:23",
    "hold_time_s_2": "G:23",
    "hold_time_s_3": "H:23",

    "hold_pressure_bar_1": "F:24",
    "hold_pressure_bar_2": "G:24",
    "hold_pressure_bar_3": "H:24",

    # ---------- Temperatures (filas 27–29) ----------
    "cylinder_temp_c_1": "D:27",
    "cylinder_temp_c_2": "E:27",
    "cylinder_temp_c_3": "F:27",
    "cylinder_temp_c_4": "G:27",
    "cylinder_temp_c_5": "H:27",

    "tolerance_c_1": "D:28",
    "tolerance_c_2": "E:28",
    "tolerance_c_3": "F:28",
    "tolerance_c_4": "G:28",
    "tolerance_c_5": "H:28",

    "feed_yoke_temp_c": "D:29",
    "lower_enable_tol_c": "J:30",
    "upper_switch_off_tol_c": "M:31",

    # ---------- Mould movements (31–33) ----------
    # Opening
    "opening_end_stage_mm_1": "E:31",
    "opening_end_stage_mm_2": "F:31",
    "opening_end_stage_mm_3": "G:31",
    "opening_end_stage_mm_4": "H:31",

    "opening_speed_mm_s_1": "E:32",
    "opening_speed_mm_s_2": "F:32",
    "opening_speed_mm_s_3": "G:32",
    "opening_speed_mm_s_4": "H:32",

    "opening_force_kN_1": "E:33",
    "opening_force_kN_2": "F:33",
    "opening_force_kN_3": "G:33",
    "opening_force_kN_4": "H:33",

    # Closing
    "closing_end_stage_mm_1": "K:31",
    "closing_end_stage_mm_2": "L:31",
    "closing_end_stage_mm_3": "M:31",
    "closing_end_stage_mm_4": "N:31",

    "closing_speed_mm_s_1": "K:32",
    "closing_speed_mm_s_2": "L:32",
    "closing_speed_mm_s_3": "M:32",
    "closing_speed_mm_s_4": "N:32",

    "closing_force_kN_1": "K:33",
    "closing_force_kN_2": "L:33",
    "closing_force_kN_3": "M:33",
    "closing_force_kN_4": "N:33",

    # ---------- Clamping ----------
    "mould_closed_kN": "D:37",
}

# (B) Traducción Excel ↔ UI (alias de claves)

ALIAS_EXCEL_TO_UI = {
    # Encabezado
    "program": "program",
    "mould_desig": "mould_desig",
    "material": "material",
    "date_of_entry": "date_of_entry",
    "cavities": "cavities",
    "machine": "machine",

    # Injection unit / key data
    "screw_diameter_mm": "screw_d_mm",

    "cycle_time_s": "cycle_time_s",
    "injection_time_s": "injection_time_s",
    "holding_press_time_s": "holding_press_time_s",
    "rem_cooling_time_s": "rem_cooling_time_s",
    "dosage_time_s": "dosage_time_s",
    "screw_stroke_mm": "screw_stroke_mm",
    "mould_stroke_mm": "mould_stroke_mm",
    "ejector_stroke_mm": "ejector_stroke_mm",
    "shot_weight_g": "shot_weight_g",
    "plasticising_flow_kg_h": "plasticising_flow_kgh",
    "dosage_capacity_g_s": "dosage_capacity_gs",
    "dosage_volume_ccm": "dosage_volume_ccm",
    "material_cushion_ccm": "material_cushion_ccm",
    "max_injection_pressure_bar": "max_inj_pressure_bar",

    # Injection
    "inj_press_limit_bar_1": "inj_press_lim_1",
    "inj_press_limit_bar_2": "inj_press_lim_2",
    "inj_press_limit_bar_3": "inj_press_lim_3",

    "injection_speed_1": "inj_speed_1",
    "injection_speed_2": "inj_speed_2",
    "injection_speed_3": "inj_speed_3",

    "end_of_stage_mm_1": "inj_end_stage_mm_1",
    "end_of_stage_mm_2": "inj_end_stage_mm_2",
    "end_of_stage_mm_3": "inj_end_stage_mm_3",

    "injection_flow_ccm_s_1": "inj_flow_1",
    "injection_flow_ccm_s_2": "inj_flow_2",
    "injection_flow_ccm_s_3": "inj_flow_3",

    "end_of_stage_ccm_1": "inj_end_stage_ccm_1",
    "end_of_stage_ccm_2": "inj_end_stage_ccm_2",
    "end_of_stage_ccm_3": "inj_end_stage_ccm_3",

    # Plasticizing
    "screw_speed_m_min_1": "plast_screw_speed",
    "back_pressure_bar": "plast_back_pressure",
    "plasticizing_end_stage_ccm": "plast_end_stage_ccm",

    # Holding pressure
    "hold_time_s_1": "hp_time_1",
    "hold_time_s_2": "hp_time_2",
    "hold_time_s_3": "hp_time_3",

    "hold_pressure_bar_1": "hp_press_1",
    "hold_pressure_bar_2": "hp_press_2",
    "hold_pressure_bar_3": "hp_press_3",

    # Temperatures
    "cylinder_temp_c_1": "temp_c1",
    "cylinder_temp_c_2": "temp_c2",
    "cylinder_temp_c_3": "temp_c3",
    "cylinder_temp_c_4": "temp_c4",
    "cylinder_temp_c_5": "temp_c5",

    "tolerance_c_1": "tol_c1",
    "tolerance_c_2": "tol_c2",
    "tolerance_c_3": "tol_c3",
    "tolerance_c_4": "tol_c4",
    "tolerance_c_5": "tol_c5",

    "feed_yoke_temp_c": "feed_yoke_temp",
    "lower_enable_tol_c": "lower_enable_tol",
    "upper_switch_off_tol_c": "upper_switch_off_tol",

    # Movements Opening
    "opening_end_stage_mm_1": "open_end_mm_1",
    "opening_end_stage_mm_2": "open_end_mm_2",
    "opening_end_stage_mm_3": "open_end_mm_3",
    "opening_end_stage_mm_4": "open_end_mm_4",

    "opening_speed_mm_s_1": "open_speed_1",
    "opening_speed_mm_s_2": "open_speed_2",
    "opening_speed_mm_s_3": "open_speed_3",
    "opening_speed_mm_s_4": "open_speed_4",

    "opening_force_kN_1": "open_force_1",
    "opening_force_kN_2": "open_force_2",
    "opening_force_kN_3": "open_force_3",
    "opening_force_kN_4": "open_force_4",

    # Movements Closing
    "closing_end_stage_mm_1": "close_end_mm_1",
    "closing_end_stage_mm_2": "close_end_mm_2",
    "closing_end_stage_mm_3": "close_end_mm_3",
    "closing_end_stage_mm_4": "close_end_mm_4",

    "closing_speed_mm_s_1": "close_speed_1",
    "closing_speed_mm_s_2": "close_speed_2",
    "closing_speed_mm_s_3": "close_speed_3",
    "closing_speed_mm_s_4": "close_speed_4",

    "closing_force_kN_1": "close_force_1",
    "closing_force_kN_2": "close_force_2",
    "closing_force_kN_3": "close_force_3",
    "closing_force_kN_4": "close_force_4",

    # Clamping
    "mould_closed_kN": "mould_closed_kn",
}

NUM_FIELDS = {
    "cycle_time_s","injection_time_s","holding_press_time_s","rem_cooling_time_s",
    "dosage_time_s","screw_stroke_mm","mould_stroke_mm","ejector_stroke_mm",
    "shot_weight_g","plasticising_flow_kgh","dosage_capacity_gs","dosage_volume_ccm",
    "material_cushion_ccm","max_inj_pressure_bar","screw_d_mm","pcs_1",
    "inj_press_lim_1","inj_press_lim_2","inj_press_lim_3",
    "inj_speed_1","inj_speed_2","inj_speed_3",
    "inj_end_stage_mm_1","inj_end_stage_mm_2","inj_end_stage_mm_3",
    "inj_flow_1","inj_flow_2","inj_flow_3",
    "inj_end_stage_ccm_1","inj_end_stage_ccm_2","inj_end_stage_ccm_3",
    "plast_screw_speed","plast_back_pressure","plast_end_stage_ccm",
    "hp_time_1","hp_time_2","hp_time_3",
    "hp_press_1","hp_press_2","hp_press_3","hp_press_4",
    "temp_c1","temp_c2","temp_c3","temp_c4","temp_c5",
    "tol_c1","tol_c2","tol_c3","tol_c4","tol_c5",
    "feed_yoke_temp","lower_enable_tol","upper_switch_off_tol",
    "open_end_mm_1","open_end_mm_2","open_end_mm_3","open_end_mm_4",
    "open_speed_1","open_speed_2","open_speed_3","open_speed_4",
    "open_force_1","open_force_2","open_force_3","open_force_4",
    "close_end_mm_1","close_end_mm_2","close_end_mm_3","close_end_mm_4",
    "close_speed_1","close_speed_2","close_speed_3","close_speed_4",
    "close_force_1","close_force_2","close_force_3","close_force_4",
    "mould_closed_kn",
}

# === Usa tu plantilla predefinida formatorecta.xlsx ===
# Intenta estas rutas en orden; usa la primera que exista.
TEMPLATE_CANDIDATES = [
    os.path.join(BASE_DIR, "formatorecta.xlsx"),
    os.path.join(RECIPES_DIR, "formatorecta.xlsx"),
    os.path.join(BASE_DIR, "assets", "formatorecta.xlsx"),
    "/mnt/data/formatorecta.xlsx",  # por si ya lo tienes ahí
]

# Bloques del template que queremos dejar en blanco si no hay dato en UI
CLEAR_BLOCKS = [
    "D4:G6",   # program/mould/material (entradas)
    "K4:O6",   # date/cavities/machine
    "J9:J9",   # Screw Ø [mm]
    "N8:O21",  # Key data
    "G11:I15", # Injection table
    "F18:F20", # Plasticizing
    "F23:H23","F24:H24", # Holding pressure
    "D27:H29", # Temperatures
    "E31:H33", # Opening
    "K31:N33", # Closing
    "D37:D37", # Clamping
]
