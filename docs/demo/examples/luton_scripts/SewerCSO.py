# -*- coding: utf-8 -*-
"""
Created on Sun Dec 24 10:09:12 2023

@author: leyan
"""

from wsimod.nodes.sewer import Sewer
from wsimod.core import constants

class SewerCSO(Sewer):
    def __init__(self,
                 spill_capacity = 172800,
                 **kwargs):
        self.spill_capacity = spill_capacity
        super().__init__(**kwargs)
    
    def make_discharge(self):
        """Function to trigger downstream sewer flow.

        Updates sewer tank travel time, pushes to WWTW, then sewer, then CSO. May
        flood land if, after these attempts, the sewer tank storage is above
        capacity.

        """
        self.sewer_tank.internal_arc.update_queue(direction="push")
        # TODO... do I need to do anything with this backflow... does it ever happen?
        
        # Discharge to CSO first
        
        cso_spill = self.sewer_tank.active_storage['volume'] - self.spill_capacity # [m3/d]
        if cso_spill > 0:
            # cso_spill = self.v_change_vqip(self.sewer_tank.active_storage, cso_spill) # [vqip]
            cso_spill = self.sewer_tank.pull_storage({'volume': cso_spill}) # [vqip]
            
            remaining = self.push_distributed(cso_spill,
                                            of_type = ["CSO"]
                                            )
            _ = self.sewer_tank.push_storage(remaining, force=True)
            # # list of arcs that connect with gw bodies
            # _, arcs = self.get_direction_arcs(direction='push', of_type=['CSO']) # new type
            # cso_arcs = [arc for arc in arcs if 'cso' in arc.name]
            # # if there is only one river arc
            # if len(cso_arcs) == 1:
            #     arc = cso_arcs[0]
            #     remaining = arc.send_push_request(cso_spill)
            #     _ = self.sewer_tank.push_storage(remaining, force = True)
            #     if remaining['volume'] > constants.FLOAT_ACCURACY:
            #         print('Sewer unable to push from '+self.name+' into cso '+arc.name.split('-to-')[-1])
            # else:
            #     print("More than 1 cso corresponds with "+self.name+" - can't model it at this stage and needs further development")
        # Discharge to sewer and river then (based on preferences)
        to_send = self.sewer_tank.pull_storage(self.sewer_tank.active_storage) # [vqip]
        remaining = self.push_distributed(to_send,
                                        of_type = ["Sewer", "River_h"]
                                        )
        _ = self.sewer_tank.push_storage(remaining, force=True)
        # #Discharge to WWTW if possible
        # remaining = self.push_distributed(remaining,
        #                                 of_type = ["WWTW"],
        #                                 tag = 'Sewer'
        #                                 )

        # remaining = self.push_distributed(self.sewer_tank.active_storage)

        # TODO backflow can cause mass balance errors here

        # # Update tank
        # sent = self.extract_vqip(self.sewer_tank.active_storage, remaining)
        # reply = self.sewer_tank.pull_storage_exact(sent)
        # if (reply["volume"] - sent["volume"]) > constants.FLOAT_ACCURACY:
        #     print("Miscalculated tank storage in discharge")

        # Flood excess
        ponded = self.sewer_tank.pull_ponded()
        if ponded["volume"] > constants.FLOAT_ACCURACY:
            reply_ = self.push_distributed(ponded, of_type=["Land"], tag="Sewer")
            reply_ = self.sewer_tank.push_storage(reply_, time=0, force=True)
            if reply_["volume"]:
                print("ponded water cant reenter")