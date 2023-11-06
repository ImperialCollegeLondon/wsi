# -*- coding: utf-8 -*-
"""Created on Tue Oct 18 10:35:51 2022.

@author: Barney

"""

# import pytest
import unittest
from unittest import TestCase

from wsimod.core import constants
from wsimod.core.core import DecayObj, WSIObj


class MyTestClass(TestCase):
    def setUp(self):
        """"""
        constants.set_simple_pollutants()

    def test_empty(self):
        obj = WSIObj()
        self.assertDictEqual(
            {"volume": 0, "phosphate": 0, "temperature": 0}, obj.empty_vqip()
        )

    def test_copy(self):
        obj = WSIObj()
        d = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        self.assertDictEqual(d, obj.copy_vqip(d))

    def test_blend(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        d2 = {"volume": 5, "phosphate": 0.00005, "temperature": 10}
        blend = {"volume": 15, "phosphate": 0.00125 / 15, "temperature": 40 / 3}
        self.assertDictEqual(blend, obj.blend_vqip(d1, d2))

    def test_sum(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        d2 = {"volume": 5, "phosphate": 0.00005, "temperature": 10}
        blend = {"volume": 15, "phosphate": 0.0001 + 0.00005, "temperature": 40 / 3}
        self.assertDictEqual(blend, obj.sum_vqip(d1, d2))

    def test_to_total(self):
        obj = WSIObj()
        d = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        tot = {"volume": 10, "phosphate": 0.001, "temperature": 15}
        self.assertDictEqual(tot, obj.concentration_to_total(d))

    def test_to_concentration(self):
        obj = WSIObj()
        d = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        tot = {"volume": 10, "phosphate": 0.00001, "temperature": 15}
        self.assertDictEqual(tot, obj.total_to_concentration(d))

    def test_extract(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        d2 = {"volume": 5, "phosphate": 0.00005, "temperature": 10}
        ext = {"volume": 5, "phosphate": 0.0001 - 0.00005, "temperature": 15}
        self.assertDictEqual(ext, obj.extract_vqip(d1, d2))

    def test_extract_c(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        d2 = {"volume": 5, "phosphate": 0.00005, "temperature": 10}
        ext = {
            "volume": 5,
            "phosphate": (0.0001 * 10 - 0.00005 * 5) / 5,
            "temperature": 15,
        }
        self.assertDictEqual(ext, obj.extract_vqip_c(d1, d2))

    def test_distill(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        v = 5
        ext = {"volume": 5, "phosphate": 0.0001, "temperature": 15}
        self.assertDictEqual(ext, obj.v_distill_vqip(d1, v))

    def test_distill_c(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        v = 5
        ext = {"volume": 5, "phosphate": 0.0002, "temperature": 15}
        self.assertDictEqual(ext, obj.v_distill_vqip_c(d1, v))

    def test_vchange(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        v = 5
        d = {"volume": 5, "phosphate": 0.00005, "temperature": 15}
        self.assertDictEqual(d, obj.v_change_vqip(d1, v))

    def test_vchange_c(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        v = 5
        d = {"volume": 5, "phosphate": 0.0001, "temperature": 15}
        self.assertDictEqual(d, obj.v_change_vqip_c(d1, v))

    def test_ds(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        d2 = {"volume": 5, "phosphate": 0.00005, "temperature": 10}
        ext = {"volume": 5, "phosphate": 0.00005, "temperature": 0}
        self.assertDictEqual(ext, obj.ds_vqip(d1, d2))

    def test_ds_c(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        d2 = {"volume": 5, "phosphate": 0.00005, "temperature": 10}
        ext = {"volume": 5, "phosphate": 0.00075, "temperature": 0}
        self.assertDictEqual(ext, obj.ds_vqip_c(d1, d2))

    def test_compare(self):
        obj = WSIObj()
        d1 = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        d2 = {"volume": 5, "phosphate": 0.00005, "temperature": 10}
        self.assertFalse(obj.compare_vqip(d1, d2))
        self.assertTrue(obj.compare_vqip(d1, d1))

    def test_mass_balance(self):
        obj = WSIObj()
        d1 = {"volume": 100000, "phosphate": 0.001, "temperature": 15}

        d2 = {"volume": 99980.5, "phosphate": 0.00087, "temperature": 10}

        d3 = {"volume": 7.5, "phosphate": 0.00003, "temperature": 12}

        d4 = {"volume": 12, "phosphate": 0.0001, "temperature": 10}

        d5 = {"volume": 19.5, "phosphate": 0.0001 + 0.00003, "temperature": 0}
        obj.name = ""
        obj.mass_balance_in = [lambda: d1]
        obj.mass_balance_out = [lambda: d2]
        obj.mass_balance_ds = [lambda: d3, lambda: d4]
        in_, ds_, out_ = obj.mass_balance()

        self.assertDictEqual(in_, d1)
        self.assertDictEqual(out_, d2)
        self.assertDictEqual(ds_, d5)

    def test_generic_decay(self):
        class Do(DecayObj):
            """"""

            def __init__(self):
                self.parent = None
                DecayObj.__init__(self, decays=None)

        dobj = Do()
        temperature = 15
        decays = {"phosphate": {"constant": 0.001, "exponent": 1.005}}
        vq = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        diff = {
            "volume": 0,
            "phosphate": 0.0001 * 0.001 * 1.005 ** (15 - 20),
            "temperature": 0,
        }
        ext = {
            "volume": 10,
            "phosphate": 0.0001 - 0.0001 * 0.001 * 1.005 ** (15 - 20),
            "temperature": 15,
        }

        ext_, diff_ = dobj.generic_temperature_decay(vq, decays, temperature)

        ext_["phosphate"] = round(ext_["phosphate"], 15)
        ext["phosphate"] = round(ext["phosphate"], 15)
        diff["phosphate"] = round(diff["phosphate"], 15)
        diff_["phosphate"] = round(diff_["phosphate"], 15)

        self.assertDictEqual(ext, ext_)
        self.assertDictEqual(diff, diff_)

    def test_make_decay(self):
        class Do(DecayObj):
            """"""

            def __init__(self):
                self.parent = WSIObj()
                DecayObj.__init__(self, decays=None)

        dobj = Do()
        dobj.decays = {"phosphate": {"constant": 0.001, "exponent": 1.005}}
        dobj.data_input_object.data_input_dict = {("temperature", 1): 15}
        dobj.data_input_object.t = 1

        vq = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        diff = {
            "volume": 0,
            "phosphate": 0.0001 * 0.001 * 1.005 ** (15 - 20),
            "temperature": 0,
        }
        ext = {
            "volume": 10,
            "phosphate": 0.0001 - 0.0001 * 0.001 * 1.005 ** (15 - 20),
            "temperature": 15,
        }

        vq_ = dobj.make_decay(vq)
        td_ = dobj.total_decayed

        vq_["phosphate"] = round(vq_["phosphate"], 15)
        ext["phosphate"] = round(ext["phosphate"], 15)
        diff["phosphate"] = round(diff["phosphate"], 15)
        td_["phosphate"] = round(td_["phosphate"], 15)

        self.assertDictEqual(ext, vq_)
        self.assertDictEqual(diff, td_)

    def test_generic_decay_c(self):
        class Do(DecayObj):
            """"""

            def __init__(self):
                self.parent = None
                DecayObj.__init__(self, decays=None)

        dobj = Do()
        temperature = 15
        decays = {"phosphate": {"constant": 0.001, "exponent": 1.005}}
        vq = {"volume": 10, "phosphate": 0.0001, "temperature": 15}
        diff = {
            "volume": 0,
            "phosphate": 0.001 * 0.001 * 1.005 ** (15 - 20),
            "temperature": 0,
        }
        ext = {
            "volume": 10,
            "phosphate": 0.0001 - 0.0001 * 0.001 * 1.005 ** (15 - 20),
            "temperature": 15,
        }

        ext_, diff_ = dobj.generic_temperature_decay_c(vq, decays, temperature)

        ext_["phosphate"] = round(ext_["phosphate"], 15)
        ext["phosphate"] = round(ext["phosphate"], 15)
        diff["phosphate"] = round(diff["phosphate"], 15)
        diff_["phosphate"] = round(diff_["phosphate"], 15)

        self.assertDictEqual(ext, ext_)
        self.assertDictEqual(diff, diff_)


if __name__ == "__main__":
    unittest.main()
