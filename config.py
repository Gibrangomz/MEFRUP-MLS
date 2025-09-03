# -*- coding: utf-8 -*-
"""Configuration and constant definitions for the MEFRUP-MLS project."""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MACHINES = [
    {
        "id": "arburg",
        "name": "ARBURG 320C GOLDEN EDITION",
        "oee_csv": os.path.join(BASE_DIR, "oee_arburg.csv"),
        "down_csv": os.path.join(BASE_DIR, "down_arburg.csv"),
    },
    {
        "id": "yizumi",
        "name": "YIZUMI UN90 A5",
        "oee_csv": os.path.join(BASE_DIR, "oee_yizumi.csv"),
        "down_csv": os.path.join(BASE_DIR, "down_yizumi.csv"),
    },
]

DAILY_CSV_GLOBAL = os.path.join(BASE_DIR, "oee_daily.csv")
DAILY_CSV_INJECTOR = os.path.join(BASE_DIR, "oee_inyeccion_daily.csv")

RECIPES_CSV = os.path.join(BASE_DIR, "recipes.csv")
LOGO_PATH = os.path.join(BASE_DIR, "10b41fef-97af-4e79-90c4-b496e0dd3197.png")

CHART_W = 640
CHART_H = 360

# Planificación y Milestones
PLANNING_CSV = os.path.join(BASE_DIR, "planning.csv")
DELIV_CSV = os.path.join(BASE_DIR, "deliveries.csv")

# Salidas / Embarques, Personal y Clientes
SHIPMENTS_CSV = os.path.join(BASE_DIR, "shipments.csv")
PERSONNEL_CSV = os.path.join(BASE_DIR, "personnel.csv")
CLIENTS_CSV = os.path.join(BASE_DIR, "clients.csv")

OPERADORES = ["OPERADOR 1", "OPERADOR 2", "OPERADOR 3"]
TURNOS_HORAS = {1: 8, 2: 8, 3: 8}
DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

TICK_MS = 1000
DEBOUNCE_MS = 160
DASH_REFRESH_MS = 5000

MOTIVOS_PARO = [
    "Cambio de molde",
    "Pieza Atorada",
    "Sin operador",
    "Calidad",
    "Mantenimiento",
    "Energía (Se fue la luz)",
]
