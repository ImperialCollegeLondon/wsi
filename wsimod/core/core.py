# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 15:44:48 2021

@author: Barney

Converted to totals on Thur Apr 21 2022

"""
from wsimod.core import constants
from math import log10

class WSIObj:
    
    def __init__(self, **kwargs):
        #Predefine empty concentrations because copying is quicker than defining
        self.empty_vqip_predefined = dict.fromkeys(constants.POLLUTANTS + ['volume'],0)
        
        #Update args
        self.__dict__.update(kwargs)

    def empty_vqip(self):
        return self.empty_vqip_predefined.copy()
    
    def copy_vqip(self, t):
        return t.copy()
    
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
        t = self.copy_vqip(t1)
        t['volume'] += t2['volume']
        for pollutant in constants.POLLUTANTS:
            t[pollutant] += t2[pollutant]
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
        #TODO should probably be called 'subtract_vqip'
        #Directly subtract t2 from t1 for vol and additive pollutants
        t = self.copy_vqip(t1)
        
        for pol in constants.ADDITIVE_POLLUTANTS + ['volume']:
            t[pol] -= t2[pol]
            
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
            t['volume'] *= ratio
            for pol in constants.ADDITIVE_POLLUTANTS:
            # for pol in set(t.keys()).intersection(constants.ADDITIVE_POLLUTANTS):
                t[pol] *= ratio
                
        else:
            #Assign volume directly
            t['volume'] = v
        return t
    
    def v_change_vqip_c(self, c, v):
        #Change volume of vqip
        c = self.copy_vqip(c)
        c['volume'] = v
        return c
    
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
    
    def compare_vqip(self, t1, t2):
        reply = True
        for v in t1.keys():
            if abs(t1[v] - t2[v]) > constants.FLOAT_ACCURACY:
                reply = False
        return reply
    
    def mass_balance(self):
        in_ = self.empty_vqip()
        for f in self.mass_balance_in:
            in_ = self.sum_vqip(in_, f())
        
        out_ = self.empty_vqip()
        for f in self.mass_balance_out:
            out_ = self.sum_vqip(out_, f())
            
        ds_ = self.empty_vqip()
        for f in self.mass_balance_ds:
            ds_f = f()
            for v in constants.ADDITIVE_POLLUTANTS + ['volume']:
                ds_[v] += ds_f[v]
        
        for v in ['volume'] + constants.ADDITIVE_POLLUTANTS:
            
            largest = max(in_[v], out_[v], ds_[v])

            if largest > constants.FLOAT_ACCURACY:
                magnitude = 10**int(log10(largest))
                in_10 = in_[v] / magnitude
                out_10 = out_[v] / magnitude
                ds_10 = ds_[v] / magnitude
            else:
                in_10 = in_[v]
                ds_10 = ds_[v]
                out_10 = out_[v]
            
            if abs(in_10 - ds_10 - out_10) > constants.FLOAT_ACCURACY:
                print("mass balance error for {0} of {1} in {2}".format(v,in_[v] - ds_[v] - out_[v], self.name))
                constants.mass_balance_error = True
        return in_, ds_, out_

class DecayObj(WSIObj):
    #TODO - internet says this is a bad idea (diamond will occur when a Node - 
    #a type of WSIObj inherits a DecayObj - also a type of WSIObj). The reason
    #diamonds are problems is because there can be conflicts in functions. But
    #I don't want anyone to overwrite WSIObj functions so I don't see an issue?
    def __init__(self, **kwargs):
        self.decays = {}
        
        super().__init__(**kwargs)
        if 'parent' in dir(self):
            self.data_input_object = self.parent
        elif 'in_port' in dir(self):
            self.data_input_object = self.in_port
        else:
            print('warning: decay arc cannot access temperature data')
            
        self.total_decayed = self.empty_vqip()
        
    def make_decay(self, vqip):
        temperature = self.data_input_object.data_input_dict[('temperature', self.data_input_object.t)]
        vqip_, diff = self.generic_temperature_decay(vqip, self.decays, temperature)
        self.total_decayed = self.sum_vqip(self.total_decayed, diff)
        return vqip_
    
    def generic_temperature_decay(self, t, d, temperature):
        t = self.copy_vqip(t)
        diff = self.empty_vqip()
        for pol, pars in d.items():
            diff[pol] = t[pol] * min(pars['constant'] * pars['exponent'] ** (temperature - constants.DECAY_REFERENCE_TEMPERATURE), 1)
            t[pol] -= diff[pol]

        return t, diff
    
    def generic_temperature_decay_c(self, c, d, temperature):
        c = self.copy_vqip(c)
        diff = self.empty_vqip()
        for pol, pars in d.items():
            diff[pol] = c[pol] * min(pars['constant'] * pars['exponent'] ** (temperature - constants.DECAY_REFERENCE_TEMPERATURE), 1)
            c[pol] -= diff[pol]

            diff[pol] *= c['volume']        
        return c, diff