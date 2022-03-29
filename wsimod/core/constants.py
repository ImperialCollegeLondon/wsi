# -*- coding: utf-8 -*-
"""
Created on Fri Dec  6 15:17:07 2019

@author: bdobson
"""

"""Constants
"""
M3_S_TO_ML_D = 86.4 
MM_KM2_TO_ML = 1e-3 * 1e6 * 1e3 * 1e-6 # mm->m, km2->m2, m3->l, l->Ml
MM_M2_TO_ML = 1e-3 * 1e3 * 1e-6 # mm->m, m3->l, l->Ml
MM_M2_TO_SIM_VOLUME = MM_M2_TO_ML #SIM volume is by default ML, but can be changed by changing MM_TO_SIM_VOLUME
MM_M2_TO_M3 = 1e-3 # mm->m
ML_TO_M3 = 1000
PCT_TO_PROP = 1/100
L_TO_ML = 1e-6
FLOAT_ACCURACY = 1e-8
UNBOUNDED_CAPACITY = 1e15
MAX_INFLOW = 1e10
DT_DAYS = 1
POLLUTANTS = ['do','phosphorus','phosphate','ammonia','solids','bod','cod','ph','temp','nitrate','nitrite'] # All assume mg/l
NON_ADDITIVE_POLLUTANTS = ['temp', 'ph'] # e.g. pollutants whose concentration in a vqip should not increase if volume is distilled out
ADDITIVE_POLLUTANTS = ['do','phosphorus','phosphate','ammonia','solids','bod','cod','nitrate','nitrite'] # All assume mg/l
PCT_GARDENS = 0.1 # Percentage of area that is people's gardens
PI = 3.141592653589793
PER_DAY_TO_PER_SECOND = 1/(60*60*24)
PER_DAY_TO_PER_HOUR = 1/24
M3_S_TO_ML_H = M3_S_TO_ML_D * PER_DAY_TO_PER_HOUR
MAXITER = 5# Max iterations in a while loop
M3_S_TO_M3_DT = 86400
UG_L_TO_KG_M3 = 1e-6
MG_L_TO_KG_M3 = 1e-3
MM_TO_M = 1e-3
G_TO_KG = 1000
DECAY_REFERENCE_TEMPERATURE = 20 # C

MM_TO_M = 1e-3
KM_TO_M = 1e3
MJ_M2_TO_CAL_CM2 = 23.889
KPA_TO_MBAR = 10
HPA_TO_KPA = 0.1
KM2_TO_HA = 100
KM2_TO_M2 = 1e6
M2_TO_KM2 = 1e-6

G_M2_TO_KG_KM2 = 1e3
MGMM_L_TO_KG_KM2 = 1e-6 * 1e3 * 1e-3 * 1e6

D_TO_S = 3600 * 24
