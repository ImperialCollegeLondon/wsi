# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 15:44:48 2021

@author: Barney
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
    
    def copy_qip(self, c):
        return c.copy()
    
    def copy_vqip(self, c):
        return c.copy()
    
    def copy_vqtip(self, c):
        return c.copy()    
    
    def blend_vqip(self, c1, c2):
        c = self.empty_vqip()
        
        c['volume'] = c1['volume'] + c2['volume']
        # if c['volume'] > constants.FLOAT_ACCURACY:
        if c['volume'] > 0:
            for pollutant in constants.POLLUTANTS:
               
                c[pollutant] = (c1[pollutant]*c1['volume'] + c2[pollutant] * c2['volume'])/c['volume']
            
        return c
    
    def sum_vqip(self, t1, t2):
        #Sum two vqips given as totals rather than concentrations
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
    
    def total_to_concentration(self, c):
        c = self.copy_vqip(c)
        for pollutant in constants.ADDITIVE_POLLUTANTS:
            c[pollutant] /= c['volume']
        return c
    
    def extract_vqip(self, c1, c2):
        #Directly subtract c2 from c1 for vol and additive pollutants
        c = self.empty_vqip()
        
        c1 = self.concentration_to_total(c1)
        c2 = self.concentration_to_total(c2)
        c['volume'] = c1['volume'] - c2['volume']
        if c['volume'] > 0:
            for pollutant in constants.ADDITIVE_POLLUTANTS:
                c[pollutant] = (c1[pollutant] - c2[pollutant])/c['volume']
            
        return c
    
    
    
    def v_distill_vqip(self, c, v):
        #Distill v from c
        c = self.copy_vqip(c)
        d = self.empty_vqip()
        d['volume'] = -v
        c_ = self.blend_vqip(c, d)
        for pollutant in constants.NON_ADDITIVE_POLLUTANTS:
            c_[pollutant] = c[pollutant]
        return c_
    
    def v_change_vqip(self, c, v):
        #Change volume of vqip
        c = self.copy_vqip(c)
        c['volume'] = v
        return c
    
    def t_insert_vqip(self, c, t):
        c = self.copy_vqip(c)
        c['time'] = t
        return c
    
    def t_remove_vqtip(self, c):
        c = self.copy_vqtip(c)
        del c['time']
        return c
    
    def ds_vqip(self, c, c_):
        ds = self.empty_vqip()
        ds['volume'] = c['volume'] - c_ ['volume']
        for pol in constants.ADDITIVE_POLLUTANTS:
            ds[pol] = c['volume'] * c[pol] - \
                      c_['volume'] * c_[pol]
        #TODO what about non-additive ...
        return ds
    
    def generic_temperature_decay(self, c, d, temperature):
        c = self.copy_vqip(c)
        diff = self.empty_vqip()
        for pol, pars in d.items():
            diff[pol] = -c[pol] * min(pars['constant'] * pars['exponent'] ** (temperature - constants.DECAY_REFERENCE_TEMPERATURE), 1)
            c[pol] += diff[pol]

            diff[pol] *= c['volume']        
        return c, diff