# -*- coding: utf-8 -*-
"""
Created on Wed Jan 25 10:30:46 2023

@author: bdobson
"""

from wsimod.nodes.land import Node, Land, GrowingSurface, VariableAreaSurface
from wsimod.nodes.nodes import Tank, DecayTank
from wsimod.core import constants
class Wetland(Land):
    def __init__(self,
                 name,
                 soil_surface = None,
                 water_surface = {'threshold' : 3.5,
                                  'h_max' : 4,
                                  'p' : 2,
                                  'area' : 10,
                                  'r_coefficient' : 10, # unit: m3/s (determines the outflow at a water level 1m above the threshold) leon set as 1
                                'r_exponent' : 2, # p in the rating curve equation could be set at 2 as a standard value
                                'wetland_infiltration' : 0.06, # 0.001m/d - 0.009m/d
                                'decays' : {'phosphate' : {'constant' : 0.001, 'exponent' : 1.005},
                                            'ammonia': {'constant': 0.1, 'exponent': 1.005}, 
                                            'nitrite': {'constant': 0.05, 'exponent': 1.005}},
                                },
                 **kwargs):
        """Wetland Land node, includes a single soil surface and a single
        wetland water tank. Assumes they have the same area, but the exposed
        surface area varies depending on how much water is in the water tank
        
        wetland_infiltration: 
            Very low - Soils with infiltration rates of less than 0.06 m/d, soils in this group are very high in percentage of clay (Marble 1992).
            Low - Infiltration rates of 0.06 to 0.3 m/d, most of these soils are shallow, high in clay, or low in organic matter.
            Medium - Infiltration rates of 0.3 to 0.6 m/d, soils in this group are loams and silts.
            High - Rates of greater than 0.6 m/d, these are deep sands and deep wellaggregated silt loams. 
        (Reference: Technical Guidance for Creating Wetlands As Part of Unconsolidated Surface Mining Reclamation)
        """
        if soil_surface:
            surfaces = [soil_surface]
        else:
            surfaces = []
        super().__init__(name,
                         surfaces = surfaces,
                         **kwargs)
        
        self.__class__.__name__ = 'Wetland'
        
        self.wetland_tank = WetlandWaterTank(parent = self,
                                                **water_surface)
        #Update handlers
        self.push_set_handler['Wetland'] = self.push_set_land
        self.push_set_handler['Sewer'] = self.push_set_land
        self.push_set_handler['Land'] = self.push_set_land
        self.push_set_handler['default'] = self.push_set_land
        
        self.push_check_handler['default'] = self.push_check_wetland
        
        #Mass balance
        self.mass_balance_ds.append(self.wetland_tank.ds)
        
        self.end_timestep = self.end_timestep_
        self.run = self.run_

    
    def push_set_land(self, vqip):

        vqip = self.wetland_tank.push_storage(vqip, force = True)
        # vqip = self.surfaces[0].push_storage(vqip, force = True)

        return vqip
    
    def push_check_wetland(self, vqip = None):
        """Generic push check, simply looks at excess in wetland tank above soil

        Args:
            vqip (dict, optional): A VQIP that can be used to limit the volume in 
                the return value (only volume key is used). Defaults to None.

        Returns:
            excess (dict): wetland tank excess
        """
        #Get excess
        excess = self.wetland_tank.get_excess()
        if vqip is None:
            return excess
        #Limit respone to vqip volume
        excess = self.v_change_vqip(excess, 
                                       min(excess['volume'], vqip['volume']))
        return excess
    
    def end_timestep_(self):
        """Update mass balance and end timestep of all tanks (and surfaces)
        """
        self.running_inflow_mb = self.empty_vqip()
        self.running_outflow_mb = self.empty_vqip()
        for tanks in self.surfaces + [self.surface_runoff, self.subsurface_runoff, self.percolation, self.wetland_tank]:
            tanks.end_timestep()
    
    def run_(self):
        """Call the run function in all surfaces, update surface/subsurface/
        percolation tanks, discharge to rivers/groundwater
        """
        
        #Run wetland
        flow_to_river, flow_to_soil = self.wetland_tank.run()
        self.flow_to_river = flow_to_river
        self.flow_to_soil = dict(flow_to_soil)
        
        # self.surfaces[0].infiltration_from_wetland_water_tank = flow_to_soil
        
        #Update soil area
        self.surfaces[0].current_soil_surface_area = self.surfaces[0].area - self.wetland_tank.current_surface_area
        
        #Run all surfaces
        self.surfaces[0].run()
        
        #Apply residence time to percolation
        percolation = self.percolation.pull_outflow()
        
        #Distribute percolation
        reply = self.push_distributed(percolation, of_type = ['Groundwater'])
        
        if reply['volume'] > constants.FLOAT_ACCURACY:
            #Update percolation 'tank'
            _ = self.percolation.push_storage(reply, force = True)
        
        # #pull water from soil tank to groundwater
        # percolation_2 = self.surfaces[0].pull_storage({'volume' : (self.surfaces[0].storage['volume']/2)})
        # reply_2 = self.push_distributed(percolation_2, of_type = ['Groundwater'])
        
        # if reply_2['volume'] > constants.FLOAT_ACCURACY:
        #     #Update soil 'tank'
        #     _ = self.surfaces[0].push_storage(reply_2, force = True)
        
        #Apply residence time to subsurface/surface runoff
        surface_runoff = self.surface_runoff.pull_outflow()
        self.surface_runoff_ = surface_runoff
        # print(surface_runoff)
        # print(self.wetland_tank.storage)
        reply_surface = self.wetland_tank.push_storage(surface_runoff, force = True)
        if reply_surface['volume'] > 0:
            self.surface_runoff.push_storage(reply_surface, force = True)
        
        
        # print(flow_to_river, flow_to_soil)
        #Send water to soil (TODO - this would need updating if you had multiple soil surfaces)
        reply = self.surfaces[0].push_storage(flow_to_soil)

        _ = self.wetland_tank.push_storage(reply, force =True)
        
        # percolation_2 = self.surfaces[0].pull_storage({'volume' : flow_to_soil['volume']})
        # reply_2 = self.percolation.push_storage(percolation_2, force = True)
        # if reply_2['volume'] > 0:
        #     self.surfaces[0].push_storage(reply_2, force = True)
            
        #Get subsurface runoff
        subsurface_runoff = self.subsurface_runoff.pull_outflow()
        
        #Total runoff to river
        total_runoff = self.sum_vqip(subsurface_runoff, flow_to_river)
        self.total_runoff = total_runoff
        if total_runoff['volume'] > 0:
            #Send to rivers (or nodes, which are assumed to be junctions)
            reply = self.push_distributed(total_runoff, of_type = ['River','Node','Sewer','Wetland'])
            
            #Redistribute total_runoff not sent
            if reply['volume'] > 0:
                reply_subsurface = self.v_change_vqip(reply, reply['volume'] * subsurface_runoff['volume'] / total_runoff['volume'])
                
                #Update surface/subsurface runoff 'tanks'
                if reply_subsurface['volume'] > 0:
                    self.subsurface_runoff.push_storage(reply_subsurface, force = True)
   
class WetlandWaterTank(DecayTank):
    def __init__(self,
                 parent,
                 threshold = 3.5,
                    h_max = 4,
                    p = 2,
                    area = 10,
                    r_coefficient = 10, # unit: m3/s (determines the outflow at a water level 1m above the threshold) leon set as 1
                    r_exponent = 2, # p in the rating curve equation could be set at 2 as a standard value
                    wetland_infiltration = 0.002, # 0.001m/d - 0.009m/d
                    et0_coefficient = 2.5,
                    **kwargs,
                    ):
        self.parent = parent
        self.S0 = area / (h_max ** (2/p))
        self.p = p
        self.threshold = threshold
        self.r_coefficient = r_coefficient
        self.r_exponent = r_exponent
        self.wetland_infiltration = wetland_infiltration
        self.h_max = h_max
        
        capacity = self.volume_wetland(h_max)
        
        super().__init__(capacity = capacity,
                         initial_storage = self.volume_wetland(threshold),
                         parent = parent,
                         **kwargs)
        
        self.et0_coefficient = et0_coefficient
        '''
        et0_coefficient default: 2.5
        Evapotranspiration Crop Coefficients for Cattail and Bulrush
        https://scholarworks.montana.edu/xmlui/bitstream/handle/1/13425/04-040_Evapotranspiration_Crop_Coefficients.pdf?sequence=1
        Effects of evapotranspiration on treatment performance in constructed wetlands: Experimental studies and modeling
        https://www.sciencedirect.com/science/article/pii/S0925857414003425
        '''
        #Calculate surface area of water
        self.current_surface_area = self.calculate_s_water_surface(self.h_current(self.storage['volume']))
        
        
    def calculate_s_water_surface(self, h):
        return (self.S0 * h ** (2/self.p))        
    '''
    Hayashi, M. & van der Kamp, G. Simple equations to represent the 
    volume–area–depth relations of shallow wetlands in small 
     depressions. Journal of Hydrology 237, 74-85, 
     doi:https://doi.org/10.1016/S0022-1694(00)00300-0 (2000)
     
    Bam, E. K. P. & Ireson, A. M. Quantifying the wetland water balance: 
        A new isotope-based approach that includes precipitation and infiltration. 
        Journal of Hydrology 570, 185-200, doi:10.1016/j.jhydrol.2018.12.032 (2019)
    '''    
    def volume_wetland(self, h):
        return (self.S0 * (2/ self.p + 1)**(-1) * h**(2/self.p + 1))
    
    def h_current(self, V):
        return ((2/self.p+1) * V / self.S0)** (1/(2/self.p + 1))
    
    def wetland_outflow(self, h):
        return self.r_coefficient * (h - self.threshold) ** self.r_exponent
        '''
        From HYPE
        Lindström, G. Lake water levels for calibration of the S-HYPE model. 
        Hydrology Research 47, 672-682, doi:10.2166/nh.2016.019 (2016).
        '''
    def get_data_input(self, var):
        """Read data input from parent Land node (i.e., for precipitation/et0/temp)

        Args:
            var (str): Name of variable

        Returns:
            Data read
        """
        return self.parent.get_data_input(var)
    

    def run(self):
        h_current = self.h_current(self.storage['volume'])
        current_surface_area = self.calculate_s_water_surface(h_current)
        self.h_current_ = h_current
        
        #Updated water surface area
        self.current_surface_area = current_surface_area
        
        #inputs
        #Read data (leave in depth units since that is what IHACRES equations are in)
        precipitation_depth = self.get_data_input('precipitation')
        self.precipitation_depth = precipitation_depth
        evaporation_depth = self.get_data_input('et0') * self.et0_coefficient
        temperature = self.get_data_input('temperature')
        
        precipitation = precipitation_depth * current_surface_area
        precipitation = self.v_change_vqip(self.empty_vqip(), precipitation)
        precipitation['temperature'] = temperature
        self.precipitation = precipitation
        
        evaporation = evaporation_depth * current_surface_area
        
        _ = self.push_storage(precipitation, force = True)
        effective_evaporation = self.v_change_vqip(self.empty_vqip(), self.evaporate(evaporation))
        self.effective_evaporation = effective_evaporation
        
        #flow to soil
        flow_to_soil = self.pull_storage({'volume' : self.wetland_infiltration * current_surface_area})

        #flow to river
        if h_current > self.threshold:
            wetland_outflow = self.wetland_outflow(h_current)
        else:
            wetland_outflow = 0
        
        wetland_outflow = self.pull_storage({'volume' : (wetland_outflow)})
        ponded = self.pull_ponded()
        
        #TODO ponded, if add ponded here, which makes wetland_outflow unuseful 
        flow_to_river = self.sum_vqip(ponded, wetland_outflow)
        
        #Update mass balabnce
        self.parent.running_inflow_mb = self.sum_vqip(self.parent.running_inflow_mb, precipitation)
        self.parent.running_outflow_mb = self.sum_vqip(self.parent.running_outflow_mb, effective_evaporation)
        # self.parent.running_outflow_mb = self.sum_vqip(self.parent.running_outflow_mb, flow_to_soil)
        
        return flow_to_river, flow_to_soil
    