# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 15:44:48 2021

@author: Barney

Converted to totals on Thur Apr 21 2022

"""
from wsimod.core import constants

class WSIObj:
    
    def __init__(self, **kwargs):
        #Predefine empty concentrations because copying is quicker than defining
        self.empty_qip_predefined = dict.fromkeys(constants.POLLUTANTS,0)
        self.empty_vqip_predefined = dict.fromkeys(constants.POLLUTANTS + ['volume'],0)
        self.empty_vqtip_predefined = dict.fromkeys(constants.POLLUTANTS + ['volume', 'time'],0)
        
        #Update args
        self.__dict__.update(kwargs)

    def empty_qip(self):
        return self.empty_qip_predefined.copy()
    
    def empty_vqip(self):
        return self.empty_vqip_predefined.copy()
    
    def empty_vqtip(self):
        return self.empty_vqtip_predefined.copy()
    
    def copy_qip(self, t):
        return t.copy()
    
    def copy_vqip(self, t):
        return t.copy()
    
    def copy_vqtip(self, t):
        return tc.copy()    
    
    def blend_vqip(self, c1, c2):
        #Blend two vqips given as concentrations
        c = self.empty_vqip()
        
        c['volume'] = c1['volume'] + c2['volume']
        # if c['volume'] > constants.FLOAT_ACCURACY:
        if c['volume'] > 0:
            for pollutant in constants.POLLUTANTS:
               
                c[pollutant] = (c1[pollutant]*c1['volume'] + c2[pollutant] * c2['volume'])/c['volume']
            
        return c
    
    def sum_vqip(self, t1, t2):
        #Sum two vqips given as totals
        t = self.empty_vqip()
        t['volume'] = t1['volume'] + t2['volume']
        for pollutant in constants.POLLUTANTS:
            t[pollutant] = t1[pollutant] + t2[pollutant]
        return t
        
    def concentration_to_total(self, c):
        c = self.copy_vqip(c)
        for pollutant in constants.ADDITIVE_POLLUTANTS:
            c[pollutant] *= c['volume']
        return c
    
    def total_to_concentration(self, t):
        c = self.copy_vqip(t)
        for pollutant in constants.ADDITIVE_POLLUTANTS:
            c[pollutant] /= c['volume']
        return c
    
    def extract_vqip(self, t1, t2):
        #Directly subtract t2 from t1 for vol and additive pollutants
        t = self.empty_vqip()
        
        for pol in constants.ADDITIVE_POLLUTANTS + ['volume']:
            t[pol] = t1[pol] - t2[pol]
            
        return t
    
    def extract_vqip_c(self, c1, c2):
        #Directly subtract c2 from c1 for vol and additive pollutants
        c = self.empty_vqip()
        
        c1 = self.concentration_to_total(c1)
        c2 = self.concentration_to_total(c2)
        c['volume'] = c1['volume'] - c2['volume']
        if c['volume'] > 0:
            for pollutant in constants.ADDITIVE_POLLUTANTS:
                c[pollutant] = (c1[pollutant] - c2[pollutant])/c['volume']
            
        return c
    
    def v_distill_vqip(self, t, v):
        #Distill v from t
        t = self.copy_vqip(t)
        t['volume'] -= v
        return t
        
    def v_distill_vqip_c(self, c, v):
        #Distill v from c
        c = self.copy_vqip(c)
        d = self.empty_vqip()
        d['volume'] = -v
        c_ = self.blend_vqip(c, d)
        for pollutant in constants.NON_ADDITIVE_POLLUTANTS:
            c_[pollutant] = c[pollutant]
        return c_
    
    def v_change_vqip(self, t, v):
        t = self.copy_vqip(t)
        if t['volume'] > 0:
            #change all values of t by volume v in proportion to volume of t
            ratio = v / t['volume']
            for pol in constants.POLLUTANTS + ['volume']:
                t[pol] *= ratio
        else:
            #Assign volume directly
            t['volume'] = v
        return t
    
    def v_change_vqip_c(self, c, v):
        #Change volume of vqip
        c = self.copy_vqip(c)
        c['volume'] = c
        return t
    
    def t_insert_vqip(self, t, time):
        t = self.copy_vqip(t)
        t['time'] = time
        return t
    
    def t_remove_vqtip(self, t):
        c = self.copy_vqtip(t)
        del t['time']
        return t
    
    def ds_vqip(self, t, t_):
        ds = self.empty_vqip()
        for pol in constants.ADDITIVE_POLLUTANTS + ['volume']:
            ds[pol] = t[pol] - t_[pol]
        return ds
    
    def ds_vqip_c(self, c, c_):
        ds = self.empty_vqip()
        ds['volume'] = c['volume'] - c_ ['volume']
        for pol in constants.ADDITIVE_POLLUTANTS:
            ds[pol] = c['volume'] * c[pol] - \
                      c_['volume'] * c_[pol]
        #TODO what about non-additive ...
        return ds
    
    def generic_temperature_decay(self, t, d, temperature):
        t = self.copy_vqip(t)
        diff = self.empty_vqip()
        for pol, pars in d.items():
            diff[pol] = -t[pol] * min(pars['constant'] * pars['exponent'] ** (temperature - constants.DECAY_REFERENCE_TEMPERATURE), 1)
            t[pol] += diff[pol]

        return t, diff
    
    def generic_temperature_decay_c(self, c, d, temperature):
        c = self.copy_vqip(c)
        diff = self.empty_vqip()
        for pol, pars in d.items():
            diff[pol] = -c[pol] * min(pars['constant'] * pars['exponent'] ** (temperature - constants.DECAY_REFERENCE_TEMPERATURE), 1)
            c[pol] += diff[pol]

            diff[pol] *= c['volume']        
        return c, diff