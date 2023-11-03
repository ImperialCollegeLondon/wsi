# -*- coding: utf-8 -*-
"""Created on Mon Oct 31 15:14:51 2022.

@author: Barney

"""
import os
import unittest

loader = unittest.TestLoader()
start_dir = os.path.abspath("")
suite = loader.discover(start_dir)

runner = unittest.TextTestRunner()
runner.run(suite)
