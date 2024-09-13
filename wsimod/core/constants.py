# -*- coding: utf-8 -*-
"""Created on Fri Dec  6 15:17:07 2019.

@author: bdobson
"""
from wsimod.core import constants

M3_S_TO_ML_D = 86.4
MM_KM2_TO_ML = 1e-3 * 1e6 * 1e3 * 1e-6  # mm->m, km2->m2, m3->l, l->Ml
MM_M2_TO_ML = 1e-3 * 1e3 * 1e-6  # mm->m, m3->l, l->Ml
MM_M2_TO_SIM_VOLUME = MM_M2_TO_ML  # SIM volume is by default ML, but can be changed by
# changing MM_TO_SIM_VOLUME
MM_M2_TO_M3 = 1e-3  # mm->m
ML_TO_M3 = 1000
PCT_TO_PROP = 1 / 100
L_TO_ML = 1e-6
FLOAT_ACCURACY = 1e-11
UNBOUNDED_CAPACITY = 1e15
MAX_INFLOW = 1e10
DT_DAYS = 1
POLLUTANTS = [
    "do",
    "org-phosphorus",
    "phosphate",
    "ammonia",
    "solids",
    "bod",
    "cod",
    "ph",
    "temperature",
    "nitrate",
    "nitrite",
    "org-nitrogen",
]
NON_ADDITIVE_POLLUTANTS = [
    "do",
    "temperature",
    "ph",
]  # e.g. pollutants whose concentration should not increase if volume is distilled out
ADDITIVE_POLLUTANTS = [
    "org-phosphorus",
    "phosphate",
    "ammonia",
    "solids",
    "bod",
    "cod",
    "nitrate",
    "nitrite",
    "org-nitrogen",
]
NUTRIENTS = ["N", "P"]
PCT_GARDENS = 0.1  # Percentage of area that is people's gardens
PI = 3.141592653589793
PER_DAY_TO_PER_SECOND = 1 / (60 * 60 * 24)
PER_DAY_TO_PER_HOUR = 1 / 24
M3_S_TO_ML_H = M3_S_TO_ML_D * PER_DAY_TO_PER_HOUR
MAXITER = 5  # Max iterations in a while loop
M3_S_TO_M3_DT = 86400
M_S_TO_M_DT = 86400
UG_L_TO_KG_M3 = 1e-6
MG_L_TO_KG_M3 = 1e-3
KG_M3_TO_MG_L = 1e3
MM_TO_M = 1e-3
G_TO_KG = 1e-3
KG_TO_MG = 1e6
DECAY_REFERENCE_TEMPERATURE = 20  # C
PER_30MONTH_TO_PER_DAY = 1 / 30
DAYS_IN_YEAR = 365
L_S_TO_M3_D = 1e-3 / PER_DAY_TO_PER_SECOND

M_TO_MM = 1e3
MM_TO_M = 1e-3
KM_TO_M = 1e3
M_TO_KM = 1e-3
MJ_M2_TO_CAL_CM2 = 23.889
KPA_TO_MBAR = 10
HPA_TO_KPA = 0.1
KM2_TO_HA = 100
KM2_TO_M2 = 1e6
HA_TO_M2 = 1e4
M2_TO_KM2 = 1e-6

G_M2_TO_KG_KM2 = 1e3
G_M2_TO_KG_M2 = 1e-3
MGMM_L_TO_KG_KM2 = 1e-6 * 1e3 * 1e-3 * 1e6
KG_M2_TO_KG_KM2 = 1e6

KG_M3_TO_KG_KM3 = 1e9

D_TO_S = 3600 * 24


def set_simple_pollutants():
    """"""
    constants.POLLUTANTS = ["phosphate", "temperature"]
    constants.ADDITIVE_POLLUTANTS = ["phosphate"]
    constants.NON_ADDITIVE_POLLUTANTS = ["temperature"]


def set_default_pollutants():
    """"""
    constants.POLLUTANTS = [
        "do",
        "org-phosphorus",
        "phosphate",
        "ammonia",
        "solids",
        "bod",
        "cod",
        "ph",
        "temperature",
        "nitrate",
        "nitrite",
        "org-nitrogen",
    ]
    constants.NON_ADDITIVE_POLLUTANTS = [
        "do",
        "temperature",
        "ph",
    ]  # e.g. pollutants whose concentration should not increase if volume is distilled
    # out
    constants.ADDITIVE_POLLUTANTS = [
        "org-phosphorus",
        "phosphate",
        "ammonia",
        "solids",
        "bod",
        "cod",
        "nitrate",
        "nitrite",
        "org-nitrogen",
    ]
