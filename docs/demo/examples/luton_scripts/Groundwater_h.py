# -*- coding: utf-8 -*-
"""
Created on Sun Dec 24 10:09:12 2023

@author: leyan
"""

from wsimod.nodes.storage import Storage
from wsimod.core import constants

class Groundwater_h(Storage):
    def __init__(self, 
                        h_initial = 200,
                        z_surface = 250,
                        s = 0.1,
                        c_riverbed = 0,
                        c_aquifer = {},
                        infiltration_threshold = 1,
                        infiltration_pct = 0,
                        data_input_dict = {},
                        **kwargs):
        # TODO can infiltrate to sewers?
        """A head-driven storage for groundwater. Can also infiltrate to sewers.

        Args:
            h_initial (float, compulsory): initial groundwater head (m asl). Defaults to 200.
            z_surface (float, compulsoty): elevation of land surface (m asl), 
                which determines the maximum storage capacity. Default to 250.
            s (float, optional): storage coefficient (-). Defaults to 0.1.
            A (float, compulsory): area of the groundwater body (polygon) (m2). Defaults to 0.
            c_riverbed (float, compulsory): the river bed conductance 
                (which could be taken from the BGWM parameterisation) (1/day). Defaults to 0.
            data_input_dict (dict, optional): Dictionary of data inputs relevant for 
                the node (though I don't think it is used). Defaults to {}.
            c_aquifer (dict, optional): aquifer conductance, which can be 
                calculated from parameterisation of British Groundwater Model 
                for any polygonal mesh (m2/day). Defaults to {}.
        
        Functions intended to call in orchestration:
            infiltrate (before sewers are discharged)

            distribute

        Key assumptions:
            - Conceptualises groundwater as a tank. The total volume of storage is controlled by a storage coefficient.
            - Exchange flow between groundwater bodies is driven by head difference through an aquifer conductance.
            - River-groundwater interactions are bi-directional, which is determined by the head difference.
            - Infiltration to `sewer.py/Sewer` nodes occurs when the storage 
                in the tank is greater than a specified threshold, at a rate 
                proportional to the sqrt of volume above the threshold. (Note, 
                this behaviour is __not validated__ and a high uncertainty process 
                in general)
            - If `decays` are provided to model water quality transformations, 
                see `core.py/DecayObj`.

        Input data and parameter requirements:
            - Groundwater tank `capacity`, `area`, and `datum`.
                _Units_: cubic metres, squared metres, metres
            - Infiltration behaviour determined by an `infiltration_threshold` 
                and `infiltration_pct`.
                _Units_: proportion of capacity
            - Optional dictionary of decays with pollutants as keys and decay 
                parameters (a constant and a temperature sensitivity exponent) 
                as values.
                _Units_: -
        """
        self.h = h_initial
        self.z_surface = z_surface
        self.s = s
        self.c_riverbed = c_riverbed
        self.c_aquifer = c_aquifer
        #
        self.infiltration_threshold = infiltration_threshold
        self.infiltration_pct = infiltration_pct
        #TODO not used data_input
        self.data_input_dict = data_input_dict
        super().__init__(data_input_dict=data_input_dict, **kwargs)
        
        # update tank
        self.tank.specific_yield = self.s
        ###########################################################################################
        def wrapper(self):
            def get_head(#self, 
                         datum = None, non_head_storage = 0):
                """Area volume calculation for head calcuations. Datum and storage 
                that does not contribute to head can be specified
        
                Args:
                    datum (float, optional): Value to add to pressure head in tank. 
                        Defaults to None.
                    non_head_storage (float, optional): Amount of storage that does 
                        not contribute to generation of head. The tank must exceed 
                        this value to generate any pressure head. Defaults to 0.
        
                Returns:
                    head (float): Total head in tank
                
                Examples:
                    >>> my_tank = Tank(datum = 10, initial_storage = 5, capacity = 10, area = 2)
                    >>> print(my_tank.get_head())
                    12.5
                    >>> print(my_tank.get_head(non_head_storage = 1))
                    12
                    >>> print(my_tank.get_head(non_head_storage = 1, datum = 0))
                    2
                    
                """        
                #If datum not provided use object datum
                if datum is None:
                    datum = self.datum
                
                #Calculate pressure head generating storage
                head_storage = max(self.storage['volume'] - non_head_storage, 0)
                
                #Perform head calculation
                head = head_storage / self.area / self.specific_yield + datum
                
                return head
            return get_head
        
        self.tank.get_head = wrapper(self.tank)
        ###########################################################################################
        self.tank.storage['volume'] = (self.h - self.datum) * self.area * self.s # [m3]
        self.tank.capacity = (self.z_surface - self.datum) * self.area * self.s # [m3]
        #Update handlers
        self.push_check_handler['Groundwater_h'] = self.push_check_head
        self.push_check_handler[('River_h', 'head')] = self.push_check_head
        self.push_check_handler[('River_h', 'c_riverbed')] = self.push_check_criverbed
      
    def distribute(self):
    # def distribute_gw_rw(self):
        ## pumping rate via pull_request through arcs
        ## recharge rate via push_request through arcs
        """Calculate exchange between Rivers and Groundwater_h
        """
        ## river-groundwater exchange
        # query river elevation
        # list of arcs that connect with gw bodies
        _, arcs = self.get_direction_arcs(direction='push', of_type=['River_h'])
        # if there is only one river arc
        if len(arcs) == 1:
            arc = arcs[0]
            z_river = arc.send_push_check(tag=('Groundwater_h', 'datum'))['volume'] # [m asl]
            length = arc.send_push_check(tag=('Groundwater_h', 'length'))['volume'] # [m]
            width = arc.send_push_check(tag=('Groundwater_h', 'width'))['volume'] # [m]
            # calculate riverbed hydraulic conductance
            C_riverbed = self.c_riverbed * length * width # [m2/day]
            # calculate river-gw flux
            flux = C_riverbed * (self.h - z_river) # [m3/day]
            if flux > 0:
                to_send = self.tank.pull_storage({'volume' : flux}) # vqip afterwards
                retained = self.push_distributed(to_send, of_type = ['River_h'])
                _ = self.tank.push_storage(retained, force = True)
                if retained['volume'] > constants.FLOAT_ACCURACY:
                    print('Groundwater to river: gw baseflow unable to push into river at '+self.name)
            # else: wait river to discharge back
        # TODO may need consider when one river connects to multiple gws
        elif len(arcs) > 1:
            print('WARNING: '+self.name+' connects with more than one river - cannot model this at this stage and please re-setup the model')
         
    # def distribute_gw_gw(self):
        """Calculate exchange between Groundwater_h and Groundwater_h
        """
        ## groundwater-groundwater exchange
        # list of arcs that connect with gw bodies
        _, arcs = self.get_direction_arcs(direction='push', of_type=['Groundwater_h'])
        for arc in arcs:
            h = arc.send_push_check(tag='Groundwater_h')['volume'] # check the head of the adjacent groundwater_h
            # if h < self.h, there will be flux discharged outside
            if h < self.h:
                # get the c_aquifer [m2/day]
                adj_node_name = arc.out_port.name # get the name of the adjacent gw_h
                if adj_node_name in self.c_aquifer.keys():
                    c_aquifer = self.c_aquifer[adj_node_name]
                else:
                    print('ERROR: the name of '+adj_node_name+' is not consistent with the c_aquifer input in '+self.name+', please recheck')
                # calculate the flux
                flux = c_aquifer * (self.h - h) # [m3/day]
                if flux > 0:
                    to_send = self.tank.pull_storage({'volume' : flux}) # vqip afterwards
                    retained = arc.send_push_request(to_send)
                    _ = self.tank.push_storage(retained, force = True)
                    if retained['volume'] > constants.FLOAT_ACCURACY:
                        print('Groundwater to groundwater: gw baseflow unable to push from '+self.name+' into '+adj_node_name)
            # if h > self.h, wait the adjacent node to push flux here
        
    def infiltrate(self):
        # TODO could use head-drive approach here
        """Calculate amount of water available for infiltration and send to sewers
        """
        #Calculate infiltration
        avail = self.tank.get_avail()['volume']
        avail = max(avail - self.tank.capacity * self.infiltration_threshold, 0)
        avail = (avail * self.infiltration_pct) ** 0.5
        
        #Push to sewers
        to_send = self.tank.pull_storage({'volume' : avail})
        retained = self.push_distributed(to_send, of_type = 'Sewer')
        _ = self.tank.push_storage(retained, force = True)
        #Any not sent is left in tank
        if retained['volume'] > constants.FLOAT_ACCURACY:
            #print('unable to infiltrate')
            pass         
    
    def push_check_head(self, vqip = None):
        # TODO should revise arc.get_excess to consider information transfer not in vqip?
        """Return a pseudo vqip whose volume is self.h
        """
        reply = self.empty_vqip()
        reply['volume'] = self.h
        
        return reply
    
    def push_check_criverbed(self, vqip = None):
        # TODO should revise arc.get_excess to consider information transfer not in vqip?
        """Return a pseudo vqip whose volume is self.c_riverbed
        """
        reply = self.empty_vqip()
        reply['volume'] = self.c_riverbed
        
        return reply
    
    def end_timestep(self):
        """Update tank states & self.h
        """
        self.tank.end_timestep()
        self.h = self.tank.get_head()
        