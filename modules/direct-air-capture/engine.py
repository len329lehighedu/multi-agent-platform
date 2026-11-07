"""Dimensioned packed-bed CO2 adsorption model, independent of Bokeh."""
from dataclasses import asdict, dataclass, fields
import time

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix

R = 8.314462618
P_TOTAL = 101325.0
Q_S = 3.40
T0 = 353.15
B0_PA = 93.0 / 1e5
DH0 = 95_300.0
TH0 = 0.37
ALPHA = 0.33
EA = 15_200.0
T_REF = 298.15
K_REF_PA = 0.90 / 1e5
RHO_S = 850.0
RHO_G = 1.184
CP_S = 1500.0
CP_G = 1006.0
H_RELEASE = 95_300.0
AREA = 0.001
M_CO2 = 0.0440095
WALLS = {"polymer": 8.0, "stainless": 25.0, "aluminum": 45.0}


@dataclass(frozen=True)
class SimulationConfig:
    volume_m3: float = 0.0005
    inlet_ppm: float = 420.0
    initial_temperature_k: float = 298.15
    flow_m3_s: float = 50.0 / 60000.0
    porosity: float = 0.40
    wall_key: str = "stainless"
    cells: int = 30
    horizon_s: float = 86400.0
    output_points: int = 121
    rtol: float = 1e-6
    max_step_s: float = 600.0
    k_ref_pa: float = K_REF_PA


def _number(name, value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"{name} must be a number")
    value = float(value)
    if not np.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be between {low:g} and {high:g}")
    return value


def validate_config(value):
    if isinstance(value, SimulationConfig):
        raw = asdict(value)
    elif isinstance(value, dict):
        allowed = {item.name for item in fields(SimulationConfig)}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError("Unknown setting(s): " + ", ".join(sorted(unknown)))
        raw = {**asdict(SimulationConfig()), **value}
    else:
        raise ValueError("Configuration must be a mapping")
    raw["volume_m3"] = _number("Reactor volume", raw["volume_m3"], 0.0002, 0.002)
    raw["inlet_ppm"] = _number("Inlet CO2", raw["inlet_ppm"], 300, 2000)
    raw["initial_temperature_k"] = _number("Initial temperature", raw["initial_temperature_k"], 278.15, 313.15)
    raw["flow_m3_s"] = _number("Volumetric flow", raw["flow_m3_s"], 10 / 60000, 100 / 60000)
    raw["porosity"] = _number("Porosity", raw["porosity"], .30, .55)
    if raw["wall_key"] not in WALLS:
        raise ValueError("Wall material is not recognized")
    if isinstance(raw["cells"], bool) or not isinstance(raw["cells"], int) or not 10 <= raw["cells"] <= 80:
        raise ValueError("cells must be an integer from 10 to 80")
    if isinstance(raw["output_points"], bool) or not isinstance(raw["output_points"], int) or not 21 <= raw["output_points"] <= 401:
        raise ValueError("output_points must be an integer from 21 to 401")
    raw["horizon_s"] = _number("Horizon", raw["horizon_s"], 60, 172800)
    raw["rtol"] = _number("Relative tolerance", raw["rtol"], 1e-9, 1e-3)
    raw["max_step_s"] = _number("Maximum step", raw["max_step_s"], 1, 3600)
    raw["k_ref_pa"] = _number("Kinetic scale", raw["k_ref_pa"], 0, 1)
    return SimulationConfig(**raw)


def toth_parameters(temperature_k, k_ref_pa=K_REF_PA):
    temperature = np.asarray(temperature_k, dtype=float)
    b = B0_PA * np.exp(DH0 / (R * T0) * (T0 / temperature - 1.0))
    th = TH0 + ALPHA * (1.0 - T0 / temperature)
    k = k_ref_pa * np.exp(-EA / R * (1.0 / temperature - 1.0 / T_REF))
    return b, th, k


def equilibrium_loading(pressure_pa, temperature_k):
    b, th, _ = toth_parameters(temperature_k)
    bp = np.maximum(b * np.maximum(pressure_pa, 0.0), 0.0)
    return Q_S * bp / np.power(1.0 + np.power(bp, th), 1.0 / th)


def adsorption_rate(concentration, loading, temperature_k, k_ref_pa=K_REF_PA):
    c = np.maximum(np.asarray(concentration, dtype=float), 0.0)
    q_raw = np.asarray(loading, dtype=float)
    q = np.clip(q_raw, 0.0, Q_S)
    temperature = np.asarray(temperature_k, dtype=float)
    b, th, k = toth_parameters(temperature, k_ref_pa)
    coverage = np.clip(q / Q_S, 0.0, 1.0)
    free = np.power(np.maximum(1.0 - np.power(coverage, th), 0.0), 1.0 / th)
    pressure = c * R * temperature
    rate = k * (pressure * free - q / (b * Q_S))
    rate = np.where((q_raw <= 0) & (rate < 0), 0.0, rate)
    rate = np.where((q_raw >= Q_S) & (rate > 0), 0.0, rate)
    return rate


def _jacobian_pattern(n):
    size = 3 * n + 1
    pattern = lil_matrix((size, size), dtype=int)
    for i in range(n):
        for row in (i, n + i, 2*n + i):
            for col in (i, n+i, 2*n+i): pattern[row, col] = 1
        if i:
            pattern[i, i-1] = 1
            pattern[2*n+i, 2*n+i-1] = 1
    pattern[-1, n-1] = 1
    return pattern.tocsr()


def simulate(config=SimulationConfig()):
    cfg = validate_config(config)
    n = cfg.cells
    length = cfg.volume_m3 / AREA
    dz = length / n
    u = cfg.flow_m3_s / AREA
    residence = cfg.porosity * cfg.volume_m3 / cfg.flow_m3_s
    t_in = cfg.initial_temperature_k
    c_in = P_TOTAL * cfg.inlet_ppm * 1e-6 / (R * t_in)
    c_eff = (1-cfg.porosity) * RHO_S * CP_S + cfg.porosity * RHO_G * CP_G
    radius = np.sqrt(AREA / np.pi)
    a_wall = 2.0 / radius
    u_eff = WALLS[cfg.wall_key]
    y0 = np.concatenate([np.full(n, c_in), np.zeros(n), np.full(n, t_in), [0.0]])

    def rhs(_time, y):
        c, q, temp = y[:n], y[n:2*n], y[2*n:3*n]
        rate = adsorption_rate(c, q, temp, cfg.k_ref_pa)
        c_up = np.concatenate(([c_in], c[:-1]))
        t_up = np.concatenate(([t_in], temp[:-1]))
        dc = -(u/cfg.porosity) * (c-c_up)/dz - ((1-cfg.porosity)*RHO_S/cfg.porosity)*rate
        dt = -(u*RHO_G*CP_G/c_eff)*(temp-t_up)/dz
        dt += ((1-cfg.porosity)*RHO_S*H_RELEASE/c_eff)*rate
        dt += (a_wall*u_eff/c_eff)*(t_in-temp)
        return np.concatenate([dc, rate, dt, [cfg.flow_m3_s * max(c[-1], 0.0)]])

    eval_times = np.linspace(0.0, cfg.horizon_s, cfg.output_points)
    atol = np.concatenate([np.full(n, 1e-9), np.full(n, 1e-8), np.full(n, 1e-6), [1e-10]])
    started = time.perf_counter()
    solution = solve_ivp(rhs, (0, cfg.horizon_s), y0, method="BDF", t_eval=eval_times,
                         rtol=cfg.rtol, atol=atol, max_step=cfg.max_step_s,
                         jac_sparsity=_jacobian_pattern(n))
    elapsed = time.perf_counter() - started
    if not solution.success:
        raise ValueError("Simulation failed: " + solution.message)
    c = solution.y[:n].T
    q = solution.y[n:2*n].T
    temp = solution.y[2*n:3*n].T
    n_out = solution.y[-1]
    if not all(np.all(np.isfinite(item)) for item in (c, q, temp, n_out)):
        raise ValueError("Simulation produced a nonfinite value")
    if np.min(c) < -1e-8 or np.min(q) < -1e-8 or np.max(q) > Q_S+1e-8 or np.min(temp) < 250 or np.max(temp) > 450:
        raise ValueError("Simulation left physical bounds")
    c = np.maximum(c, 0.0); q = np.clip(q, 0.0, Q_S)
    pressure = c * R * temp
    ppm = pressure / P_TOTAL * 1e6
    rate = adsorption_rate(c, q, temp, cfg.k_ref_pa)
    uptake = (1-cfg.porosity)*RHO_S*cfg.volume_m3*np.mean(q, axis=1)
    n_in = cfg.flow_m3_s*c_in*solution.t
    delta_gas = cfg.porosity*cfg.volume_m3*np.mean(c-c_in, axis=1)
    residual = n_in-n_out-delta_gas-uptake
    residual_pct = 100*np.abs(residual)/np.maximum(n_in, 1e-12)
    residual_pct[0] = 0.0
    capture = np.clip(1.0-c[:, -1]/c_in, 0.0, 1.0)
    peak_index = np.unravel_index(np.argmax(temp), temp.shape)
    z = (np.arange(n)+.5)*dz
    context = dict(length_m=length, superficial_velocity_m_s=u, residence_time_s=residence,
                   wall_u_w_m2_k=u_eff, wall_area_per_volume_m_inv=a_wall,
                   heat_capacity_j_m3_k=c_eff, cells=n, horizon_h=cfg.horizon_s/3600)
    result = dict(config=asdict(cfg), z_m=z.tolist(), time_s=solution.t.tolist(),
        concentration_mol_m3=c.tolist(), concentration_ppm=ppm.tolist(),
        loading_mol_kg=q.tolist(), loading_fraction=(q/Q_S).tolist(),
        temperature_k=temp.tolist(), rate_mol_kg_s=rate.tolist(),
        outlet_ppm=ppm[:, -1].tolist(), capture_fraction=capture.tolist(),
        uptake_mol=uptake.tolist(), uptake_g_co2=(uptake*M_CO2*1000).tolist(),
        cumulative_in_mol=n_in.tolist(), cumulative_out_mol=n_out.tolist(),
        mass_residual_mol=residual.tolist(), mass_residual_percent=residual_pct.tolist(),
        peak_temperature_k=float(temp[peak_index]), peak_temperature_time_s=float(solution.t[peak_index[0]]),
        peak_temperature_z_m=float(z[peak_index[1]]), peak_rate_mol_kg_s=float(np.max(rate)),
        final_outlet_ppm=float(ppm[-1,-1]), final_capture_fraction=float(capture[-1]),
        final_uptake_g_co2=float(uptake[-1]*M_CO2*1000), solver_seconds=elapsed,
        solver_success=True, solver_message=solution.message, solver_nfev=int(solution.nfev),
        bound_correction_mol=0.0, context=context)
    return result
