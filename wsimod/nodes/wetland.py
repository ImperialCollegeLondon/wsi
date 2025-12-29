# -*- coding: utf-8 -*-
"""
Created on Wed Jan 25 10:30:46 2023

@author: bdobson, Fangjun
"""

from wsimod.core import constants
from wsimod.nodes.land import Land
from wsimod.nodes.tanks import DecayTank


class Wetland(Land):
    def __init__(
        self,
        name,
        soil_surface=None,
        water_surface={
            "threshold": 3.5,
            "h_max": 4,
            "p": 2,
            "area": 10,
            "r_coefficient": 10,
            "r_exponent": 2,
            "wetland_infiltration": 0.06,
            "decays": {
                "phosphate": {"constant": 0.001, "exponent": 1.005},
                "ammonia": {"constant": 0.1, "exponent": 1.005},
                "nitrite": {"constant": 0.05, "exponent": 1.005},
            },
        },
        **kwargs,
    ):
        """
    A specialized Land node representing a Wetland system. 
        
    It consists of a soil surface and an overlying water tank. The node 
    dynamically calculates the interaction between the water level and the 
    exposed soil area.

    Key features:
        - Dynamic surface area: 
        The exposed soil area decreases as the wetland water volume increases.
        - Water balance: 
        Integrates precipitation, evapotranspiration, infiltration to soil, 
        and rating-curve-based discharge.
        - Water quality: 
        Inherits decay processes for pollutants within the wetland water body.

    Parameters:
        name (str):
            Node name.
        soil_surface (list, optional):
            List of dicts describing soil surface parameters.
            Defaults to [].
        water_surface (dict, optional):
            Parameters for the WetlandWaterTank including:
                - threshold (float):
                  Water level height at which outflow to river begins (m).
                - h_max (float):
                  Maximum possible water depth (m).
                - p (float):
                  Shape parameter for the volume-area-depth relationship.
                - area (float):
                  Total area of the wetland at h_max (m2).
                - r_coefficient (float):
                  Determines the outflow at a water level 1 m above the threshold
                  (m3/s).
                - r_exponent (float):
                  Rating curve exponent (typically 2).
                - wetland_infiltration (float):
                  Daily infiltration rate from water tank to soil
                  (0.001 m/d–0.009 m/d).
                - decays (dict):
                  Pollutant decay constants and temperature exponents.
        **kwargs:
            Additional arguments passed to the Land parent class.

    Key assumptions:
        - Wetland Land node includes a single soil surface and a single wetland
          water tank.
        - The wetland water body and soil surface share the same footprint.
        - Exposed surface area varies with the wetland water volume.
        - Outflow follows a rating curve once the water level exceeds the
          threshold.
        - Infiltration to the underlying soil is driven by the saturated area of
          the wetland.

    Input data requirements:
        wetland_infiltration:
            Very low:
                Infiltration rates < 0.06 m/d. Soils in this group have a high
                clay content (Marble, 1992).
            Low:
                Infiltration rates of 0.06–0.3 m/d. These soils are often shallow,
                clay-rich, or low in organic matter.
            Medium:
                Infiltration rates of 0.3–0.6 m/d. Soils are typically loams and
                silts.
            High:
                Infiltration rates > 0.6 m/d. These are deep sands and well-
                aggregated silt loams.
        (Reference: Technical Guidance for Creating Wetlands As Part of 
         Unconsolidated Surface Mining Reclamation)
        """
        if soil_surface:
            surfaces = soil_surface
        else:
            surfaces = []
        super().__init__(name, surfaces=surfaces, **kwargs)

        self.__class__.__name__ = "Wetland"

        self.wetland_tank = WetlandWaterTank(parent=self, **water_surface)
        # Update handlers
        self.push_set_handler["Wetland"] = self.push_set_land
        self.push_set_handler["Sewer"] = self.push_set_land
        self.push_set_handler["Land"] = self.push_set_land
        self.push_set_handler["default"] = self.push_set_land

        self.push_check_handler["default"] = self.push_check_wetland

        # Mass balance
        self.mass_balance_ds.append(self.wetland_tank.ds)

        self.end_timestep = self.end_timestep_
        self.run = self.run_

    def push_set_land(self, vqip):

        vqip = self.wetland_tank.push_storage(vqip, force=True)
        # vqip = self.surfaces[0].push_storage(vqip, force = True)

        return vqip

    def push_check_wetland(self, vqip=None):
        """Generic push check, simply looks at excess in wetland tank above soil

        Args:
            vqip (dict, optional): A VQIP that can be used to limit the volume in
                the return value (only volume key is used). Defaults to None.

        Returns:
            excess (dict): wetland tank excess
        """
        # Get excess
        excess = self.wetland_tank.get_excess()
        if vqip is None:
            return excess
        # Limit respone to vqip volume
        excess = self.v_change_vqip(excess, min(excess["volume"], vqip["volume"]))
        return excess

    def end_timestep_(self):
        """Update mass balance and end timestep of all tanks (and surfaces)"""
        self.running_inflow_mb = self.empty_vqip()
        self.running_outflow_mb = self.empty_vqip()
        for tanks in self.surfaces + [
            self.surface_runoff,
            self.subsurface_runoff,
            self.percolation,
            self.wetland_tank,
        ]:
            tanks.end_timestep()

    def run_(self):
        """Call the run function in VariableAreaSurface, update surface/subsurface/
        percolation tanks, discharge to rivers/groundwater
        """

        # Run wetland
        flow_to_river, flow_to_soil = self.wetland_tank.run()
        self.flow_to_river = flow_to_river
        self.flow_to_soil = dict(flow_to_soil)

        # self.surfaces[0].infiltration_from_wetland_water_tank = flow_to_soil

        # Update soil area
        self.surfaces[0].current_soil_surface_area = (
            self.surfaces[0].area - self.wetland_tank.current_surface_area
        )

        # Run all surfaces
        self.surfaces[0].run()

        # Apply residence time to percolation
        percolation = self.percolation.pull_outflow()

        # Distribute percolation
        reply = self.push_distributed(percolation, of_type=["Groundwater"])

        if reply["volume"] > constants.FLOAT_ACCURACY:
            # Update percolation 'tank'
            _ = self.percolation.push_storage(reply, force=True)

        # Apply residence time to subsurface/surface runoff
        surface_runoff = self.surface_runoff.pull_outflow()
        self.surface_runoff_ = surface_runoff

        reply_surface = self.wetland_tank.push_storage(surface_runoff, force=True)
        if reply_surface["volume"] > 0:
            self.surface_runoff.push_storage(reply_surface, force=True)

        # Send water to soil (TODO - this would need updating if you had multiple soil surfaces)
        reply = self.surfaces[0].push_storage(flow_to_soil)

        _ = self.wetland_tank.push_storage(reply, force=True)

        # Get subsurface runoff
        subsurface_runoff = self.subsurface_runoff.pull_outflow()

        # Total runoff to river
        total_runoff = self.sum_vqip(subsurface_runoff, flow_to_river)
        self.total_runoff = total_runoff
        if total_runoff["volume"] > 0:
            # Send to rivers (or nodes, which are assumed to be junctions)
            reply = self.push_distributed(
                total_runoff, of_type=["River", "Node", "Sewer", "Wetland", "Waste"]
            )

            # Redistribute total_runoff not sent
            if reply["volume"] > 0:
                reply_subsurface = self.v_change_vqip(
                    reply,
                    reply["volume"]
                    * subsurface_runoff["volume"]
                    / total_runoff["volume"],
                )

                # Update surface/subsurface runoff 'tanks'
                if reply_subsurface["volume"] > 0:
                    self.subsurface_runoff.push_storage(reply_subsurface, force=True)


class WetlandWaterTank(DecayTank):
    def __init__(
        self,
        parent,
        threshold=3.5,
        h_max=4,
        p=2,
        area=10,
        r_coefficient=10,
        r_exponent=2,
        wetland_infiltration=0.002,
        et0_coefficient=2.5,
        **kwargs,
    ):
        """
        A storage tank representing the open water component of a wetland.
        It uses power-law equations to represent the volume-area-depth relationships
        characteristic of shallow depressions.

        Parameters:
            parent (Node): The parent Wetland Land node.
            threshold (float): Height (h) at which the wetland starts spilling to the river (m).
            h_max (float): Maximum height capacity of the wetland (m).
            p (float): Power-law parameter (2/p) relating depth to area (Hayashi & van der Kamp, 2000).
            area (float): Maximum surface area at h_max (m2).
            r_coefficient (float): Determine the outflow at a water level 1m above the threshold, unit: m3/s
            r_exponent (float): Rating curve exponent. 2 as a standard value
            wetland_infiltration (float): Constant infiltration rate to the soil (0.001m/d - 0.009m/d).
            et0_coefficient (float): Scaling factor for potential evapotranspiration (e.g., for cattails/bulrushes).
        """
        self.parent = parent
        self.S0 = area / (h_max ** (2 / p))
        self.p = p
        self.threshold = threshold
        self.r_coefficient = r_coefficient
        self.r_exponent = r_exponent
        self.wetland_infiltration = wetland_infiltration
        self.h_max = h_max

        capacity = self.volume_wetland(h_max)

        super().__init__(
            capacity=capacity,
            initial_storage=self.volume_wetland(threshold),
            parent=parent,
            **kwargs,
        )

        self.et0_coefficient = et0_coefficient
        """
        et0_coefficient default: 2.5
        Evapotranspiration Crop Coefficients for Cattail and Bulrush
        https://scholarworks.montana.edu/xmlui/bitstream/handle/1/13425/04-040_Evapotranspiration_Crop_Coefficients.pdf?sequence=1
        Effects of evapotranspiration on treatment performance in constructed wetlands: Experimental studies and modeling
        https://www.sciencedirect.com/science/article/pii/S0925857414003425
        """
        # Calculate surface area of water
        self.current_surface_area = self.calculate_s_water_surface(
            self.h_current(self.storage["volume"])
        )

    def calculate_s_water_surface(self, h):
        """Calculate surface area (S) for a given depth (h) using S = S0 * h^(2/p)"""
        """
        Hayashi, M. & van der Kamp, G. Simple equations to represent the 
        volume–area–depth relations of shallow wetlands in small 
         depressions. Journal of Hydrology 237, 74-85, 
         doi:https://doi.org/10.1016/S0022-1694(00)00300-0 (2000)
         
        Bam, E. K. P. & Ireson, A. M. Quantifying the wetland water balance: 
            A new isotope-based approach that includes precipitation and infiltration. 
            Journal of Hydrology 570, 185-200, doi:10.1016/j.jhydrol.2018.12.032 (2019)
        """
        return self.S0 * h ** (2 / self.p)

    def volume_wetland(self, h):
        """Integrate area to get volume: V = (S0 / (2/p + 1)) * h^(2/p + 1)"""
        return self.S0 * (2 / self.p + 1) ** (-1) * h ** (2 / self.p + 1)

    def h_current(self, V):
        """Invert the volume equation to find current water depth (h) from volume (V)"""
        return ((2 / self.p + 1) * V / self.S0) ** (1 / (2 / self.p + 1))

    def wetland_outflow(self, h):
        """Calculate discharge using rating curve: Q = r_coeff * (h - threshold)^r_exp"""
        """
        From HYPE
        Lindström, G. Lake water levels for calibration of the S-HYPE model. 
        Hydrology Research 47, 672-682, doi:10.2166/nh.2016.019 (2016).
        """
        return self.r_coefficient * (h - self.threshold) ** self.r_exponent

    def get_data_input(self, var):
        """Read data input from parent Land node (i.e., for precipitation/et0/temp)

        Args:
            var (str): Name of variable

        Returns:
            Data read
        """
        return self.parent.get_data_input(var)

    def run(self):
        h_current = self.h_current(self.storage["volume"])
        current_surface_area = self.calculate_s_water_surface(h_current)
        self.h_current_ = h_current

        # Updated water surface area
        self.current_surface_area = current_surface_area

        # inputs
        # Read data (leave in depth units since that is what IHACRES equations are in)
        precipitation_depth = self.get_data_input("precipitation")
        self.precipitation_depth = precipitation_depth
        evaporation_depth = self.get_data_input("et0") * self.et0_coefficient
        temperature = self.get_data_input("temperature")

        precipitation = precipitation_depth * current_surface_area
        precipitation = self.v_change_vqip(self.empty_vqip(), precipitation)
        precipitation["temperature"] = temperature
        self.precipitation = precipitation

        evaporation = evaporation_depth * current_surface_area

        _ = self.push_storage(precipitation, force=True)
        effective_evaporation = self.v_change_vqip(
            self.empty_vqip(), self.evaporate(evaporation)
        )
        self.effective_evaporation = effective_evaporation

        # flow to soil
        flow_to_soil = self.pull_storage(
            {"volume": self.wetland_infiltration * current_surface_area}
        )

        # flow to river
        if h_current > self.threshold:
            wetland_outflow = self.wetland_outflow(h_current)
        else:
            wetland_outflow = 0

        wetland_outflow = self.pull_storage({"volume": (wetland_outflow)})
        ponded = self.pull_ponded()

        # TODO ponded, if add ponded here, which makes wetland_outflow unuseful
        flow_to_river = self.sum_vqip(ponded, wetland_outflow)

        # Update mass balabnce
        self.parent.running_inflow_mb = self.sum_vqip(
            self.parent.running_inflow_mb, precipitation
        )
        self.parent.running_outflow_mb = self.sum_vqip(
            self.parent.running_outflow_mb, effective_evaporation
        )
        # self.parent.running_outflow_mb = self.sum_vqip(self.parent.running_outflow_mb, flow_to_soil)

        return flow_to_river, flow_to_soil
