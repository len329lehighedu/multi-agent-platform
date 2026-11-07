"""Scientific and contract checks for the DAC engine."""
import importlib.util, json
from pathlib import Path
import sys, unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]; NAME="_dac_engine_tests"
spec=importlib.util.spec_from_file_location(NAME,ROOT/"engine.py"); engine=importlib.util.module_from_spec(spec);sys.modules[NAME]=engine;spec.loader.exec_module(engine)


class EngineTests(unittest.TestCase):
    def test_toth_equilibrium_cancels_rate(self):
        for pressure in (20.,42.,200.):
            for temperature in (283.15,298.15,313.15):
                q=engine.equilibrium_loading(pressure,temperature)
                rate=engine.adsorption_rate(pressure/(engine.R*temperature),q,temperature)
                self.assertAlmostEqual(float(rate),0.0,places=12)

    def test_default_is_bounded_and_conservative(self):
        result=engine.simulate()
        for key in ("concentration_mol_m3","loading_mol_kg","temperature_k","rate_mol_kg_s"):
            self.assertTrue(np.isfinite(result[key]).all())
        self.assertGreaterEqual(np.min(result["concentration_mol_m3"]),0)
        self.assertGreaterEqual(np.min(result["loading_mol_kg"]),0)
        self.assertLessEqual(np.max(result["loading_mol_kg"]),engine.Q_S)
        self.assertGreater(np.min(result["temperature_k"]),250)
        self.assertLess(np.max(result["temperature_k"]),450)
        self.assertLess(result["mass_residual_percent"][-1],.1)
        self.assertLess(result["final_outlet_ppm"],result["config"]["inlet_ppm"])

    def test_zero_kinetics_is_stationary_and_closed(self):
        result=engine.simulate({"k_ref_pa":0.0,"horizon_s":3600.0,"output_points":21})
        concentration=np.asarray(result["concentration_ppm"])
        self.assertTrue(np.allclose(concentration,420,rtol=0,atol=1e-8))
        self.assertTrue(np.allclose(result["loading_mol_kg"],0))
        self.assertTrue(np.allclose(result["temperature_k"],298.15))
        self.assertLess(result["mass_residual_percent"][-1],1e-8)

    def test_residence_time_volume_flow_and_wall_trends(self):
        low_flow=engine.simulate({"flow_m3_s":10/60000})
        high_flow=engine.simulate({"flow_m3_s":100/60000})
        self.assertGreater(low_flow["context"]["residence_time_s"],high_flow["context"]["residence_time_s"])
        self.assertGreaterEqual(high_flow["final_outlet_ppm"],low_flow["final_outlet_ppm"])
        small=engine.simulate({"volume_m3":.0002}); large=engine.simulate({"volume_m3":.002})
        self.assertGreater(large["final_uptake_g_co2"],small["final_uptake_g_co2"])
        self.assertLessEqual(large["final_outlet_ppm"],small["final_outlet_ppm"])
        weak=engine.simulate({"wall_key":"polymer"}); strong=engine.simulate({"wall_key":"aluminum"})
        self.assertLessEqual(strong["peak_temperature_k"],weak["peak_temperature_k"]+1e-7)

    def test_valid_endpoint_sweep(self):
        cases=[{"volume_m3":v} for v in (.0002,.002)]+[{"inlet_ppm":v} for v in (300,2000)]+[{"initial_temperature_k":v} for v in (278.15,313.15)]+[{"flow_m3_s":v/60000} for v in (10,100)]+[{"porosity":v} for v in (.30,.55)]+[{"wall_key":v} for v in engine.WALLS]
        for case in cases:
            with self.subTest(case=case):
                result=engine.simulate(case)
                self.assertTrue(result["solver_success"])
                self.assertLess(result["mass_residual_percent"][-1],.1)

    def test_validation_and_json_contract(self):
        for case in ({"volume_m3":.1},{"inlet_ppm":np.nan},{"porosity":True},{"wall_key":"glass"},{"mystery":1}):
            with self.subTest(case=case),self.assertRaises(ValueError): engine.validate_config(case)
        json.dumps(engine.simulate({"horizon_s":60,"output_points":21}),allow_nan=False)


if __name__=="__main__": unittest.main()
