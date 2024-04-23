# -*- coding: utf-8 -*-
"""
Created on Sun Dec 24 10:09:12 2023

@author: leyan
"""

from wsimod.nodes.sewer import Sewer

class CSO(Sewer):
    def __init__(self,
                 **kwargs):
        
        super().__init__(**kwargs)
