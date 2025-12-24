from pathlib import Path
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import types
import shutil

# WSIMOD core imports
from wsimod.orchestration.model import Model, to_datetime
from wsimod.core import constants
from wsimod.nodes.wetland import Wetland

# =====================================================================
# Global settings
# =====================================================================

DAYS = 365
SURFACE_NAME_KEY = "soil"
OUTPUT_DIR = Path("D:/Data/created_data")


# =====================================================================
# Helper function: Create wetland input CSV files
# =====================================================================

def create_wetland_input_files(temp_dir, days):
    """
    Create daily and monthly input CSV files required by WSIMOD wetland
    components (WetlandWaterTank and VariableAreaSurface).
    """

    dates = pd.date_range("2000-01-01", periods=days, freq="D")
    monthly_dates = dates[dates.day == 1]

    # -----------------------------------------------------------------
    # A. Daily inputs for WetlandWaterTank
    # -----------------------------------------------------------------
    daily_input_filename = temp_dir / "wetland-daily-inputs.csv"

    df_daily = pd.DataFrame({
        "time": dates,
        "precipitation": [0.005] * days,
        "et0": [0.002] * days,
        "temperature": [20.0] * days,
    })

    df_daily_long = pd.melt(
        df_daily,
        id_vars=["time"],
        var_name="variable",
        value_name="value",
    )[["variable", "time", "value"]]

    df_daily_long.to_csv(daily_input_filename, index=False)

    # -----------------------------------------------------------------
    # B. Monthly surface inputs for VariableAreaSurface
    # -----------------------------------------------------------------
    monthly_surface_filename = temp_dir / "wetland-monthly-surface-inputs.csv"

    zero_variables = [
        "nhx-fertiliser", "noy-fertiliser", "srp-fertiliser",
        "nhx-manure", "noy-manure", "srp-manure",
        "nhx-dry", "noy-dry", "srp-dry",
        "nhx-wet", "noy-wet", "srp-wet",
        "noy-residue", "crop-factor", "crop-stage-day",
    ]

    monthly_data = {"time": monthly_dates}
    for var in zero_variables:
        monthly_data[var] = [0.0] * len(monthly_dates)

    df_monthly_long = pd.melt(
        pd.DataFrame(monthly_data),
        id_vars=["time"],
        var_name="variable",
        value_name="value",
    )[["variable", "time", "value"]]

    df_monthly_long.to_csv(monthly_surface_filename, index=False)

    return daily_input_filename.resolve(), monthly_surface_filename.resolve()


# =====================================================================
# Helper function: Plot flow results
# =====================================================================

def plot_results(flows, output_dir):
    """
    Plot daily flows with optimized X-axis labels (Month-Year) 
    without importing additional libraries.
    """
    # Ensure time is in datetime format
    flows = flows.copy()
    flows["time_dt"] = pd.to_datetime(flows["time"].apply(lambda x: x._date))

    if flows.empty:
        return

    # Pivot data for easier plotting
    df_plot = flows.pivot_table(index="time_dt", columns="arc", values="flow")

    plt.figure(figsize=(12, 6))

    # Plot existing arcs
    if "river_arc" in df_plot.columns:
        plt.plot(df_plot.index, df_plot["river_arc"], 
                 label="Surface Runoff (Wetland → River)", color="green")

    if "groundwater_arc" in df_plot.columns:
        plt.plot(df_plot.index, df_plot["groundwater_arc"], 
                 label="Percolation to GW (Wetland → GW)", linestyle="--", color="brown")

    if "baseflow_arc" in df_plot.columns:
        plt.plot(df_plot.index, df_plot["baseflow_arc"], 
                 label="GW Baseflow (GW → River)", linestyle=":", color="red")

    # --- Optimize X-axis labels ---
    # Select only the first day of each month for ticks
    tick_dates = df_plot.index[df_plot.index.day == 1]
    # Format labels as 'MM-YYYY' or 'Jan-2000'
    tick_labels = [d.strftime('%b-%Y') for d in tick_dates]
    
    plt.xticks(tick_dates, tick_labels, rotation=45)
    # ------------------------------

    plt.title("Daily Wetland Flows (m³/s)")
    plt.xlabel("Date (Month-Year)")
    plt.ylabel("Flow (m³/s)")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    
    # Adjust layout to prevent label clipping
    plt.tight_layout()

    output_path = output_dir / "wetland_flows_plot_v22_m3s.png"
    plt.savefig(output_path)
    plt.show()
    plt.close()
# =====================================================================
# Main test function
# =====================================================================

def test_wetland_gw_baseflow():
    """
    Test groundwater percolation and baseflow generation from a single
    wetland connected to a groundwater node and river sink.
    """

    # -----------------------------------------------------------------
    # Clean output directory
    # -----------------------------------------------------------------
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # Create input data
    # -----------------------------------------------------------------
    daily_path, monthly_path = create_wetland_input_files(OUTPUT_DIR, DAYS)

    # -----------------------------------------------------------------
    # Prepare WSIMOD time objects
    # -----------------------------------------------------------------
    dates = pd.date_range("2000-01-01", periods=DAYS, freq="D")
    dates_ws = [to_datetime(str(d.date())) for d in dates]

    # -----------------------------------------------------------------
    # Build daily input dictionary (WetlandWaterTank)
    # -----------------------------------------------------------------
    daily_df = pd.read_csv(daily_path)
    daily_df["time"] = pd.to_datetime(daily_df["time"]).dt.normalize().dt.to_pydatetime()

    ws_time_map = {ws_date._date: ws_date for ws_date in dates_ws}
    daily_data_dict = {}

    for _, row in daily_df.iterrows():
        ws_time = ws_time_map.get(row["time"])
        if ws_time is not None:
            daily_data_dict[(row["variable"], ws_time)] = row["value"]

    # -----------------------------------------------------------------
    # Build monthly input dictionary (VariableAreaSurface)
    # -----------------------------------------------------------------
    monthly_df = pd.read_csv(monthly_path)

    def to_month_key(t):
        dt = pd.to_datetime(t)
        return to_datetime(f"{dt.year}-{str(dt.month).zfill(2)}")

    monthly_df["time_key"] = monthly_df["time"].apply(to_month_key)
    monthly_df["surface_name"] = SURFACE_NAME_KEY

    monthly_data_dict = {
        (row["variable"], row["surface_name"], row["time_key"]): row["value"]
        for _, row in monthly_df.iterrows()
    }

    # -----------------------------------------------------------------
    # WSIMOD configuration
    # -----------------------------------------------------------------
    config = {
        "nodes": {
            "wetland1": {
                "type_": "Wetland",
                "name": "wetland1",
                "data_input_dict": {},
                "soil_surface": [{
                    "type_": "VariableAreaSurface",
                    "data_input_dict": {},
                    "rooting_depth": 1,
                    "ET_depletion_factor": 0.5,
                    "infiltration_capacity": 0.5,
                    "surface_coefficient": 0.05,
                    "percolation_coefficient": 0.75,
                    "pollutant_load": {
                        "nitrate": 1e-9,
                        "ammonia": 1e-9,
                        "nitrite": 1e-9,
                    },
                    "initial_soil_storage": {
                        "phosphate": 0.0,
                        "ammonia": 0.0,
                        "nitrate": 0.0,
                        "nitrite": 0.0,
                        "org-nitrogen": 0.0,
                        "org-phosphorus": 0.0,
                        "solids": 0.0,
                        "bod": 0.0,
                        "cod": 0.0,
                        "do": 0.0,
                        "ph": 7.0,
                        "temperature": 20.0,
                    },
                    "initial_storage": 0.0,
                }],
                "water_surface": {
                    "threshold": 0.1,
                    "h_max": 4,
                    "area": 20000,
                    "r_coefficient": 0.1,
                    "r_exponent": 1.0,
                    "wetland_infiltration": 0.06,
                },
            },
            "river_sink": {"type_": "Waste", "name": "river_sink"},
            "gw1": {"type_": "Groundwater", "name": "gw1", "capacity": 1e9},
        },
        "arcs": {
            "river_arc": {
                "name": "river_arc",
                "in_port": "wetland1",
                "out_port": "river_sink",
                "capacity": constants.UNBOUNDED_CAPACITY,
                "type_": "Arc",
            },
            "groundwater_arc": {
                "name": "groundwater_arc",
                "in_port": "wetland1",
                "out_port": "gw1",
                "capacity": constants.UNBOUNDED_CAPACITY,
                "type_": "Arc",
            },
            "baseflow_arc": {
                "name": "baseflow_arc",
                "in_port": "gw1",
                "out_port": "river_sink",
                "capacity": constants.UNBOUNDED_CAPACITY,
                "type_": "Arc",
            },
        },
    }

    config_path = OUTPUT_DIR / "config_v22.yml"
    with config_path.open("w") as f:
        yaml.safe_dump(config, f)

    # -----------------------------------------------------------------
    # Model initialisation and dynamic data injection
    # -----------------------------------------------------------------
    model = Model()
    model.load(address=str(config_path.parent), config_name=config_path.name)

    wetland = model.nodes["wetland1"]
    surface = wetland.surfaces[0]

    surface.area = 20000
    wetland.data_input_dict = daily_data_dict
    surface.data_input_dict = monthly_data_dict
    surface.name = SURFACE_NAME_KEY

    # Inject time and month accessors required by WSIMOD internals
    wetland.time = types.MethodType(lambda self: model.time, wetland)
    wetland.monthyear = types.MethodType(lambda self: self.time.to_period(), wetland)

    def get_surface_input(self, var):
        return self.data_input_dict.get(
            (var, self.name, self.parent.monthyear), 0.0
        )

    surface.get_data_input_surface = types.MethodType(
        get_surface_input, surface
    )

    # -----------------------------------------------------------------
    # Run model
    # -----------------------------------------------------------------
    flows_list, tank_states_list, _, _ = model.run(dates=dates_ws)
    flows = pd.DataFrame(flows_list)
    flows["time_dt"] = flows["time"].apply(lambda x: pd.Timestamp(x._date))

    # -----------------------------------------------------------------
    # Diagnose and plot results
    # -----------------------------------------------------------------
    print("\n--- Flow summary ---")
    print("Runoff:", flows.loc[flows.arc == "river_arc", "flow"].sum())
    print("Percolation:", flows.loc[flows.arc == "groundwater_arc", "flow"].sum())
    print("Baseflow:", flows.loc[flows.arc == "baseflow_arc", "flow"].sum())

    plot_results(flows, OUTPUT_DIR)

    print("\nV22 wetland–groundwater baseflow test completed successfully.")


# =====================================================================
if __name__ == "__main__":
    test_wetland_gw_baseflow()
