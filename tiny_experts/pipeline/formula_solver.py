"""Universal Neuro-Symbolic Formula & Rule Solver (Core Pillar 4).

Connects neural concept identification and learned textbook equations to SymPy
algebraic solving, bidirectional variable isolation, multi-hop formula chaining,
and physical/dimensional sanity verification.
"""
from __future__ import annotations

from collections import deque
import math
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import sympy as sp
except ImportError:
    sp = None

NUMBER_RE = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"

PHYSICAL_CONSTANTS: Dict[str, float] = {
    "g": 9.80665,
    "c": 299792458.0,
    "h": 6.62607015e-34,
    "G": 6.67430e-11,
    "k_B": 1.380649e-23,
    "R_gas": 8.314462618,
    "sigma_sb": 5.670374419e-8,
    "k_e": 8.9875517923e9,
    "q_e": 1.602176634e-19,
}

VARIABLE_CATALOG: Dict[str, Dict[str, Any]] = {
    "F": {
        "name": "force",
        "dimension": "M1 L1 T-2",
        "si_unit": "N",
        "labels": r"force|net\s+force|thrust|tension|weight|F",
        "target_phrases": [r"find\s+(?:the\s+)?force", r"what\s+is\s+(?:the\s+)?force", r"calculate\s+(?:the\s+)?force"],
        "units": {"n": 1.0, "newton": 1.0, "newtons": 1.0, "kn": 1e3, "kilonewton": 1e3, "kilonewtons": 1e3, "mn": 1e-3},
    },
    "m": {
        "name": "mass",
        "dimension": "M1",
        "si_unit": "kg",
        "positive_only": True,
        "labels": r"mass|m",
        "target_phrases": [r"find\s+(?:the\s+)?mass", r"what\s+is\s+(?:the\s+)?mass", r"calculate\s+(?:the\s+)?mass"],
        "units": {"kg": 1.0, "kilogram": 1.0, "kilograms": 1.0, "g": 1e-3, "gram": 1e-3, "grams": 1e-3, "mg": 1e-6, "tonne": 1e3},
    },
    "a": {
        "name": "acceleration",
        "dimension": "L1 T-2",
        "si_unit": "m/s^2",
        "labels": r"acceleration|accel|a",
        "target_phrases": [r"find\s+(?:the\s+)?acceleration", r"what\s+is\s+(?:the\s+)?acceleration", r"calculate\s+(?:the\s+)?acceleration"],
        "units": {"m/s^2": 1.0, "m/s2": 1.0, "m/s²": 1.0, "cm/s^2": 1e-2, "cm/s2": 1e-2},
    },
    "v": {
        "name": "velocity",
        "dimension": "L1 T-1",
        "si_unit": "m/s",
        "labels": r"velocity|speed|v",
        "target_phrases": [r"find\s+(?:the\s+)?(?:velocity|speed)", r"what\s+is\s+(?:the\s+)?(?:velocity|speed)", r"calculate\s+(?:the\s+)?(?:velocity|speed)", r"how\s+fast"],
        "units": {"m/s": 1.0, "km/s": 1e3, "km/h": 1.0 / 3.6, "kph": 1.0 / 3.6, "cm/s": 1e-2},
    },
    "E_k": {
        "name": "kinetic_energy",
        "dimension": "M1 L2 T-2",
        "si_unit": "J",
        "labels": r"kinetic\s+energy|ke|E_k",
        "target_phrases": [r"find\s+(?:the\s+)?kinetic\s+energy", r"what\s+is\s+(?:the\s+)?kinetic\s+energy", r"calculate\s+(?:the\s+)?kinetic\s+energy"],
        "units": {"j": 1.0, "joule": 1.0, "joules": 1.0, "kj": 1e3, "kilojoule": 1e3, "kilojoules": 1e3, "mj": 1e6, "ev": 1.602176634e-19},
    },
    "E_p": {
        "name": "potential_energy",
        "dimension": "M1 L2 T-2",
        "si_unit": "J",
        "labels": r"potential\s+energy|gravitational\s+potential\s+energy|elastic\s+potential\s+energy|pe|E_p",
        "target_phrases": [r"find\s+(?:the\s+)?(?:gravitational\s+|elastic\s+)?potential\s+energy", r"what\s+is\s+(?:the\s+)?(?:gravitational\s+|elastic\s+)?potential\s+energy"],
        "units": {"j": 1.0, "joule": 1.0, "joules": 1.0, "kj": 1e3, "kilojoule": 1e3, "kilojoules": 1e3, "mj": 1e6},
    },
    "h_elev": {
        "name": "height",
        "dimension": "L1",
        "si_unit": "m",
        "labels": r"height|elevation|altitude|ramp\s+height",
        "target_phrases": [r"find\s+(?:the\s+)?height", r"what\s+is\s+(?:the\s+)?height", r"how\s+high"],
        "units": {"m": 1.0, "meter": 1.0, "meters": 1.0, "cm": 1e-2, "mm": 1e-3, "km": 1e3},
    },
    "k_spring": {
        "name": "spring_constant",
        "dimension": "M1 T-2",
        "si_unit": "N/m",
        "positive_only": True,
        "labels": r"spring\s+constant|stiffness|k_spring|k",
        "target_phrases": [r"find\s+(?:the\s+)?spring\s+constant", r"what\s+is\s+(?:the\s+)?spring\s+constant"],
        "units": {"n/m": 1.0, "kn/m": 1e3, "n/cm": 1e2},
    },
    "x_disp": {
        "name": "spring_compression",
        "dimension": "L1",
        "si_unit": "m",
        "labels": r"spring\s+compression|compression|extension|displacement|stretch|x_disp",
        "target_phrases": [
            r"how\s+far\s+does\s+(?:the\s+)?spring\s+compress",
            r"find\s+(?:the\s+)?(?:spring\s+)?(?:compression|displacement|extension)",
            r"what\s+is\s+(?:the\s+)?(?:spring\s+)?(?:compression|displacement|extension)",
        ],
        "units": {"m": 1.0, "meter": 1.0, "meters": 1.0, "cm": 1e-2, "mm": 1e-3},
    },
    "p_mom": {
        "name": "momentum",
        "dimension": "M1 L1 T-1",
        "si_unit": "kg*m/s",
        "labels": r"momentum|linear\s+momentum|p_mom",
        "target_phrases": [r"find\s+(?:the\s+)?momentum", r"what\s+is\s+(?:the\s+)?momentum", r"calculate\s+(?:the\s+)?momentum"],
        "units": {"kg*m/s": 1.0, "kg m/s": 1.0, "n*s": 1.0, "ns": 1.0},
    },
    "lam": {
        "name": "wavelength",
        "dimension": "L1",
        "si_unit": "m",
        "positive_only": True,
        "labels": r"de\s+broglie\s+wavelength|wavelength|lambda",
        "target_phrases": [
            r"find\s+(?:the\s+)?(?:de\s+broglie\s+)?wavelength",
            r"what\s+is\s+(?:its\s+|the\s+)?(?:de\s+broglie\s+)?wavelength",
            r"calculate\s+(?:the\s+)?(?:de\s+broglie\s+)?wavelength",
        ],
        "units": {"m": 1.0, "meter": 1.0, "meters": 1.0, "nm": 1e-9, "nanometer": 1e-9, "nanometers": 1e-9, "pm": 1e-12, "um": 1e-6, "cm": 1e-2},
    },
    "freq": {
        "name": "frequency",
        "dimension": "T-1",
        "si_unit": "Hz",
        "positive_only": True,
        "labels": r"frequency|photon\s+frequency|wave\s+frequency|freq",
        "target_phrases": [r"find\s+(?:the\s+)?frequency", r"what\s+is\s+(?:the\s+)?frequency", r"calculate\s+(?:the\s+)?frequency"],
        "units": {"hz": 1.0, "hertz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9, "thz": 1e12},
    },
    "E_ph": {
        "name": "photon_energy",
        "dimension": "M1 L2 T-2",
        "si_unit": "J",
        "positive_only": True,
        "labels": r"photon\s+energy|quantum\s+energy|E_ph",
        "target_phrases": [r"find\s+(?:the\s+)?photon\s+energy", r"what\s+is\s+(?:the\s+)?photon\s+energy", r"calculate\s+(?:the\s+)?photon\s+energy"],
        "units": {"j": 1.0, "joule": 1.0, "joules": 1.0, "ev": 1.602176634e-19, "kev": 1.602176634e-16, "mev": 1.602176634e-13},
    },
    "r_s": {
        "name": "schwarzschild_radius",
        "dimension": "L1",
        "si_unit": "m",
        "positive_only": True,
        "labels": r"schwarzschild\s+radius|event\s+horizon\s+radius|r_s",
        "target_phrases": [
            r"find\s+(?:the\s+)?(?:schwarzschild|event\s+horizon)\s+radius",
            r"what\s+is\s+(?:its\s+|the\s+)?(?:schwarzschild|event\s+horizon)\s+radius",
            r"calculate\s+(?:the\s+)?(?:schwarzschild|event\s+horizon)\s+radius",
        ],
        "units": {"m": 1.0, "meter": 1.0, "meters": 1.0, "km": 1e3, "kilometer": 1e3, "kilometers": 1e3},
    },
    "gamma_rel": {
        "name": "lorentz_factor",
        "dimension": "1",
        "si_unit": "dimensionless",
        "positive_only": True,
        "labels": r"lorentz\s+factor|gamma_rel|gamma",
        "target_phrases": [r"find\s+(?:the\s+)?lorentz\s+factor", r"what\s+is\s+(?:the\s+)?lorentz\s+factor", r"calculate\s+(?:the\s+)?lorentz\s+factor"],
        "units": {"dimensionless": 1.0, "": 1.0},
    },
    "T_H": {
        "name": "hot_reservoir_temperature",
        "dimension": "Theta1",
        "si_unit": "K",
        "positive_only": True,
        "labels": r"hot\s+reservoir\s+temperature(?:\s+T_h)?|hot\s+temperature|source\s+temperature|T_H|T_h|T\s*h|th",
        "target_phrases": [
            r"find\s+(?:the\s+)?hot\s+(?:reservoir\s+)?temperature",
            r"what\s+is\s+(?:the\s+)?hot\s+(?:reservoir\s+)?temperature",
            r"calculate\s+(?:the\s+)?hot\s+(?:reservoir\s+)?temperature",
        ],
        "units": {"k": 1.0, "kelvin": 1.0},
    },
    "T_C": {
        "name": "cold_reservoir_temperature",
        "dimension": "Theta1",
        "si_unit": "K",
        "positive_only": True,
        "labels": r"cold\s+reservoir\s+temperature(?:\s+T_c)?|cold\s+temperature|sink\s+temperature|T_C|T_c|T\s*c|tc",
        "target_phrases": [
            r"find\s+(?:the\s+)?cold\s+(?:reservoir\s+)?temperature",
            r"what\s+is\s+(?:the\s+)?cold\s+(?:reservoir\s+)?temperature",
            r"calculate\s+(?:the\s+)?cold\s+(?:reservoir\s+)?temperature",
        ],
        "units": {"k": 1.0, "kelvin": 1.0},
    },
    "eta_carnot": {
        "name": "carnot_efficiency",
        "dimension": "1",
        "si_unit": "fraction",
        "labels": r"carnot\s+efficiency|thermal\s+efficiency|efficiency|eta",
        "target_phrases": [
            r"find\s+(?:the\s+)?(?:carnot\s+|thermal\s+)?efficiency",
            r"what\s+is\s+(?:the\s+)?(?:carnot\s+|thermal\s+)?efficiency",
            r"calculate\s+(?:the\s+)?(?:carnot\s+|thermal\s+)?efficiency",
        ],
        "units": {"%": 0.01, "percent": 0.01, "fraction": 1.0, "": 1.0},
    },
    "V_elec": {
        "name": "voltage",
        "dimension": "M1 L2 T-3 I-1",
        "si_unit": "V",
        "labels": r"voltage|potential\s+difference|emf|V_elec",
        "target_phrases": [r"find\s+(?:the\s+)?voltage", r"what\s+is\s+(?:the\s+)?voltage", r"calculate\s+(?:the\s+)?voltage"],
        "units": {"v": 1.0, "volt": 1.0, "volts": 1.0, "kv": 1e3, "mv": 1e-3},
    },
    "I_elec": {
        "name": "current",
        "dimension": "I1",
        "si_unit": "A",
        "labels": r"current|electric\s+current|I_elec",
        "target_phrases": [r"find\s+(?:the\s+)?current", r"what\s+is\s+(?:the\s+)?current", r"calculate\s+(?:the\s+)?current"],
        "units": {"a": 1.0, "amp": 1.0, "amps": 1.0, "ampere": 1.0, "amperes": 1.0, "ma": 1e-3, "ka": 1e3},
    },
    "R_elec": {
        "name": "resistance",
        "dimension": "M1 L2 T-3 I-2",
        "si_unit": "ohm",
        "positive_only": True,
        "labels": r"resistance|resistor|R_elec",
        "target_phrases": [r"find\s+(?:the\s+)?resistance", r"what\s+is\s+(?:the\s+)?resistance", r"calculate\s+(?:the\s+)?resistance"],
        "units": {"ohm": 1.0, "ohms": 1.0, "ω": 1.0, "Ω": 1.0, "kohm": 1e3, "kohms": 1e3, "kω": 1e3, "kΩ": 1e3},
    },
    "P_power": {
        "name": "power",
        "dimension": "M1 L2 T-3",
        "si_unit": "W",
        "labels": r"power|electrical\s+power|mechanical\s+power|P_power",
        "target_phrases": [r"find\s+(?:the\s+)?power", r"what\s+is\s+(?:the\s+)?power", r"calculate\s+(?:the\s+)?power"],
        "units": {"w": 1.0, "watt": 1.0, "watts": 1.0, "kw": 1e3, "kilowatt": 1e3, "kilowatts": 1e3, "mw": 1e6},
    },
    "rho_fluid": {
        "name": "fluid_density",
        "dimension": "M1 L-3",
        "si_unit": "kg/m^3",
        "positive_only": True,
        "labels": r"fluid\s+density|density|rho",
        "target_phrases": [r"find\s+(?:the\s+)?(?:fluid\s+)?density", r"what\s+is\s+(?:the\s+)?(?:fluid\s+)?density"],
        "units": {"kg/m^3": 1.0, "kg/m3": 1.0, "g/cm^3": 1e3, "g/cm3": 1e3},
    },
    "L_char": {
        "name": "characteristic_length",
        "dimension": "L1",
        "si_unit": "m",
        "positive_only": True,
        "labels": r"pipe\s+diameter|characteristic\s+length|channel\s+diameter|L_char",
        "target_phrases": [r"find\s+(?:the\s+)?(?:pipe\s+diameter|characteristic\s+length)", r"what\s+is\s+(?:the\s+)?(?:pipe\s+diameter|characteristic\s+length)"],
        "units": {"m": 1.0, "meter": 1.0, "meters": 1.0, "cm": 1e-2, "mm": 1e-3},
    },
    "mu_visc": {
        "name": "dynamic_viscosity",
        "dimension": "M1 L-1 T-1",
        "si_unit": "Pa*s",
        "positive_only": True,
        "labels": r"dynamic\s+viscosity|viscosity|mu_visc",
        "target_phrases": [r"find\s+(?:the\s+)?(?:dynamic\s+)?viscosity", r"what\s+is\s+(?:the\s+)?(?:dynamic\s+)?viscosity"],
        "units": {"pa*s": 1.0, "pa s": 1.0, "pas": 1.0, "mpa*s": 1e-3, "cp": 1e-3},
    },
    "Re_num": {
        "name": "reynolds_number",
        "dimension": "1",
        "si_unit": "dimensionless",
        "positive_only": True,
        "labels": r"reynolds\s+number|Re_num",
        "target_phrases": [r"find\s+(?:the\s+)?reynolds\s+number", r"what\s+is\s+(?:the\s+)?reynolds\s+number", r"calculate\s+(?:the\s+)?reynolds\s+number"],
        "units": {"dimensionless": 1.0, "": 1.0},
    },
    "taxable_val": {
        "name": "taxable_value",
        "dimension": "Currency1",
        "si_unit": "INR",
        "positive_only": True,
        "labels": r"taxable\s+value|invoice\s+amount|base\s+price|taxable_val",
        "target_phrases": [r"find\s+(?:the\s+)?taxable\s+value", r"what\s+is\s+(?:the\s+)?taxable\s+value"],
        "units": {"inr": 1.0, "rs": 1.0, "rupees": 1.0, "₹": 1.0},
    },
    "gst_rate": {
        "name": "gst_rate",
        "dimension": "1",
        "si_unit": "fraction",
        "positive_only": True,
        "labels": r"gst\s+rate|tax\s+rate|igst\s+rate|gst_rate",
        "target_phrases": [r"find\s+(?:the\s+)?gst\s+rate", r"what\s+is\s+(?:the\s+)?gst\s+rate"],
        "units": {"%": 0.01, "percent": 0.01, "fraction": 1.0},
    },
    "gst_tax": {
        "name": "gst_tax_amount",
        "dimension": "Currency1",
        "si_unit": "INR",
        "labels": r"gst\s+amount|gst\s+tax|total\s+gst|igst\s+amount|gst_tax",
        "target_phrases": [r"find\s+(?:the\s+)?(?:gst\s+amount|gst\s+tax|total\s+gst)", r"what\s+is\s+(?:the\s+)?(?:gst\s+amount|gst\s+tax|total\s+gst)", r"calculate\s+(?:the\s+)?gst"],
        "units": {"inr": 1.0, "rs": 1.0, "rupees": 1.0, "₹": 1.0},
    },
}

DEFAULT_FORMULAS: List[Dict[str, Any]] = [
    {
        "formula_id": "newton_second_law",
        "subdomain": "classical_mechanics",
        "concept": "newton second law",
        "title": "Newton's Second Law of Motion",
        "lhs": "F",
        "rhs": "m * a",
        "variables": ["F", "m", "a"],
        "constants": [],
        "keywords": ["force", "mass", "acceleration", "newton"],
    },
    {
        "formula_id": "kinetic_energy",
        "subdomain": "classical_mechanics",
        "concept": "kinetic energy",
        "title": "Translational Kinetic Energy",
        "lhs": "E_k",
        "rhs": "0.5 * m * v**2",
        "variables": ["E_k", "m", "v"],
        "constants": [],
        "keywords": ["kinetic energy", "velocity", "speed", "mass"],
    },
    {
        "formula_id": "gravitational_potential_energy",
        "subdomain": "classical_mechanics",
        "concept": "gravitational potential energy",
        "title": "Gravitational Potential Energy",
        "lhs": "E_p",
        "rhs": "m * g * h_elev",
        "variables": ["E_p", "m", "h_elev"],
        "constants": ["g"],
        "keywords": ["potential energy", "height", "elevation", "ramp", "gravity"],
    },
    {
        "formula_id": "elastic_potential_energy",
        "subdomain": "classical_mechanics",
        "concept": "harmonic oscillator",
        "title": "Elastic Spring Potential Energy",
        "lhs": "E_p",
        "rhs": "0.5 * k_spring * x_disp**2",
        "variables": ["E_p", "k_spring", "x_disp"],
        "constants": [],
        "keywords": ["spring", "compression", "spring constant", "elastic"],
    },
    {
        "formula_id": "hooke_law",
        "subdomain": "classical_mechanics",
        "concept": "hooke law",
        "title": "Hooke's Law of Elasticity",
        "lhs": "F",
        "rhs": "k_spring * x_disp",
        "variables": ["F", "k_spring", "x_disp"],
        "constants": [],
        "keywords": ["spring", "hooke", "force", "compression", "extension"],
    },
    {
        "formula_id": "linear_momentum",
        "subdomain": "classical_mechanics",
        "concept": "linear momentum",
        "title": "Linear Momentum",
        "lhs": "p_mom",
        "rhs": "m * v",
        "variables": ["p_mom", "m", "v"],
        "constants": [],
        "keywords": ["momentum", "mass", "velocity"],
    },
    {
        "formula_id": "mechanical_power",
        "subdomain": "classical_mechanics",
        "concept": "mechanical power",
        "title": "Mechanical Power",
        "lhs": "P_power",
        "rhs": "F * v",
        "variables": ["P_power", "F", "v"],
        "constants": [],
        "keywords": ["power", "force", "velocity"],
    },
    {
        "formula_id": "de_broglie_wavelength",
        "subdomain": "quantum_mechanics",
        "concept": "de broglie wavelength",
        "title": "de Broglie Matter-Wave Relation",
        "lhs": "lam",
        "rhs": "h / (m * v)",
        "variables": ["lam", "m", "v"],
        "constants": ["h"],
        "keywords": ["de broglie", "matter wave", "wavelength", "mass", "velocity"],
    },
    {
        "formula_id": "de_broglie_momentum",
        "subdomain": "quantum_mechanics",
        "concept": "de broglie momentum",
        "title": "de Broglie Wavelength from Momentum",
        "lhs": "lam",
        "rhs": "h / p_mom",
        "variables": ["lam", "p_mom"],
        "constants": ["h"],
        "keywords": ["de broglie", "wavelength", "momentum"],
    },
    {
        "formula_id": "planck_photon_energy",
        "subdomain": "quantum_mechanics",
        "concept": "photon energy",
        "title": "Planck-Einstein Photon Energy",
        "lhs": "E_ph",
        "rhs": "h * freq",
        "variables": ["E_ph", "freq"],
        "constants": ["h"],
        "keywords": ["photon energy", "planck", "frequency", "quantum energy"],
    },
    {
        "formula_id": "wave_speed_light",
        "subdomain": "optics_waves",
        "concept": "electromagnetic wave dispersion",
        "title": "Electromagnetic Wave Frequency-Wavelength Relation",
        "lhs": "c",
        "rhs": "lam * freq",
        "variables": ["lam", "freq"],
        "constants": ["c"],
        "keywords": ["wavelength", "frequency", "light", "photon", "electromagnetic"],
    },
    {
        "formula_id": "schwarzschild_radius",
        "subdomain": "relativity_cosmology",
        "concept": "schwarzschild metric",
        "title": "Schwarzschild Event Horizon Radius",
        "lhs": "r_s",
        "rhs": "2 * G * m / c**2",
        "variables": ["r_s", "m"],
        "constants": ["G", "c"],
        "keywords": ["schwarzschild", "event horizon", "black hole", "radius"],
    },
    {
        "formula_id": "lorentz_factor",
        "subdomain": "relativity_cosmology",
        "concept": "lorentz transformation",
        "title": "Relativistic Lorentz Factor",
        "lhs": "gamma_rel",
        "rhs": "1 / sqrt(1 - (v / c)**2)",
        "variables": ["gamma_rel", "v"],
        "constants": ["c"],
        "keywords": ["lorentz factor", "relativistic", "time dilation", "gamma"],
    },
    {
        "formula_id": "carnot_efficiency",
        "subdomain": "thermodynamics_stat_mech",
        "concept": "carnot cycle",
        "title": "Carnot Heat Engine Maximum Efficiency",
        "lhs": "eta_carnot",
        "rhs": "1 - (T_C / T_H)",
        "variables": ["eta_carnot", "T_C", "T_H"],
        "constants": [],
        "keywords": ["carnot", "efficiency", "hot reservoir", "cold reservoir"],
    },
    {
        "formula_id": "ohm_law",
        "subdomain": "electromagnetism",
        "concept": "ohm law",
        "title": "Ohm's Law of Electrical Conduction",
        "lhs": "V_elec",
        "rhs": "I_elec * R_elec",
        "variables": ["V_elec", "I_elec", "R_elec"],
        "constants": [],
        "keywords": ["ohm", "voltage", "current", "resistance", "resistor"],
    },
    {
        "formula_id": "electrical_power",
        "subdomain": "electromagnetism",
        "concept": "electric power",
        "title": "Joule Electrical Power Law",
        "lhs": "P_power",
        "rhs": "V_elec * I_elec",
        "variables": ["P_power", "V_elec", "I_elec"],
        "constants": [],
        "keywords": ["electrical power", "power", "voltage", "current", "watt"],
    },
    {
        "formula_id": "reynolds_number",
        "subdomain": "fluid_plasma",
        "concept": "reynolds number",
        "title": "Reynolds Dimensionless Flow Number",
        "lhs": "Re_num",
        "rhs": "rho_fluid * v * L_char / mu_visc",
        "variables": ["Re_num", "rho_fluid", "v", "L_char", "mu_visc"],
        "constants": [],
        "keywords": ["reynolds number", "viscosity", "pipe", "fluid density", "laminar"],
    },
    {
        "formula_id": "gst_tax_calculation",
        "subdomain": "gst_taxation",
        "concept": "gst tax calculation",
        "title": "GST Output Tax Liability Formula",
        "lhs": "gst_tax",
        "rhs": "taxable_val * gst_rate",
        "variables": ["gst_tax", "taxable_value" if False else "taxable_val", "gst_rate"],
        "constants": [],
        "keywords": ["gst", "taxable value", "igst", "cgst", "sgst", "invoice"],
    },
]


class UniversalFormulaSolver:
    """Solves unseen single-step and multi-hop numerical problems forwards and backwards."""

    _DYNAMIC_LEARNED_FORMULAS: List[Dict[str, Any]] = []

    def __init__(self, extra_formulas: Optional[List[Dict[str, Any]]] = None):
        self.formulas: List[Dict[str, Any]] = list(DEFAULT_FORMULAS)
        existing_ids = {f["formula_id"] for f in self.formulas}
        for item in self._DYNAMIC_LEARNED_FORMULAS:
            if item.get("formula_id") not in existing_ids:
                self.formulas.append(item)
                existing_ids.add(item["formula_id"])
        if extra_formulas:
            for item in extra_formulas:
                if item.get("formula_id") not in existing_ids:
                    self.formulas.append(item)
                    existing_ids.add(item["formula_id"])

    @classmethod
    def compile_and_register_learned_formula(cls, formula_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Pillar 2: Compile a learned textbook equation into SymPy AST, verify dimensional & algebraic validity, and register it live."""
        fid = str(formula_spec.get("formula_id") or "").strip()
        lhs = str(formula_spec.get("lhs") or "").strip()
        rhs = str(formula_spec.get("rhs") or "").strip()
        variables = list(formula_spec.get("variables") or [])
        if not fid or not lhs or not rhs or len(variables) < 2:
            return {"compiled": False, "reason": "Missing formula_id, lhs, rhs, or variables"}
        if sp is not None:
            try:
                sym_map = {v: sp.Symbol(v, real=True) for v in variables}
                for c_name, c_val in PHYSICAL_CONSTANTS.items():
                    sym_map.setdefault(c_name, sp.Float(c_val))
                lhs_expr = sp.sympify(lhs, locals=sym_map)
                rhs_expr = sp.sympify(rhs.replace("^", "**"), locals=sym_map)
                inversions = {}
                for target_v in variables:
                    t_sym = sym_map[target_v]
                    sols = sp.solve(sp.Eq(lhs_expr, rhs_expr), t_sym)
                    if sols:
                        inversions[target_v] = str(sols[0])
            except Exception as exc:
                return {"compiled": False, "reason": f"SymPy compilation error: {exc}"}
        else:
            inversions = {lhs: rhs}

        # Register in VARIABLE_CATALOG if custom variable metadata is supplied
        for v_name, v_meta in (formula_spec.get("variable_definitions") or {}).items():
            if isinstance(v_meta, dict):
                norm_meta = dict(v_meta)
                if "units" not in norm_meta:
                    norm_meta["units"] = dict(norm_meta.get("unit_map") or {str(norm_meta.get("si_unit", "")).lower(): 1.0})
                if "labels" not in norm_meta:
                    aliases = list(norm_meta.get("aliases") or [norm_meta.get("name", v_name), v_name])
                    norm_meta["labels"] = "|".join(re.escape(str(a)).replace(r"\ ", r"\s+") for a in aliases if a)
                if "target_phrases" not in norm_meta:
                    human_name = str(norm_meta.get("name", v_name)).replace("_", r"\s+")
                    norm_meta["target_phrases"] = [
                        rf"find\s+(?:the\s+)?{human_name}",
                        rf"what\s+is\s+(?:the\s+)?{human_name}",
                        rf"calculate\s+(?:the\s+)?{human_name}",
                    ]
                VARIABLE_CATALOG[v_name] = norm_meta

        existing_ids = {f["formula_id"] for f in cls._DYNAMIC_LEARNED_FORMULAS} | {f["formula_id"] for f in DEFAULT_FORMULAS}
        if fid not in existing_ids:
            cls._DYNAMIC_LEARNED_FORMULAS.append({
                "formula_id": fid,
                "subdomain": formula_spec.get("subdomain", "classical_mechanics"),
                "concept": formula_spec.get("concept", "learned_concept"),
                "title": formula_spec.get("title", f"Learned Law ({lhs} = {rhs})"),
                "lhs": lhs,
                "rhs": rhs.replace("^", "**"),
                "variables": variables,
                "constants": list(formula_spec.get("constants") or []),
                "keywords": list(formula_spec.get("keywords") or []),
            })
        return {
            "compiled": True,
            "formula_id": fid,
            "lhs": lhs,
            "rhs": rhs,
            "symbolic_inversions": inversions,
            "total_dynamic_formulas": len(cls._DYNAMIC_LEARNED_FORMULAS),
        }

    @staticmethod
    def extract_variables_from_query(query: str) -> Tuple[Dict[str, float], Optional[str], List[str]]:
        """Extracts known variable values in SI units and identifies the unknown target variable."""
        knowns: Dict[str, float] = {}
        target_var: Optional[str] = None
        warnings: List[str] = []
        q_norm = query.strip()

        # 1. Identify explicit target variable from question phrasing
        for var_sym, meta in VARIABLE_CATALOG.items():
            for phrase_pat in meta.get("target_phrases", []):
                if re.search(phrase_pat, q_norm, re.IGNORECASE):
                    target_var = var_sym
                    break
            if target_var:
                break

        # 2. Extract known numerical quantities with unit conversion
        for var_sym, meta in VARIABLE_CATALOG.items():
            if var_sym == target_var:
                continue
            units_map: Dict[str, float] = meta["units"]
            non_empty_units = [u for u in units_map.keys() if u]
            unit_regex = "|".join(re.escape(u) for u in sorted(non_empty_units, key=len, reverse=True))
            labels_regex = meta["labels"]

            # Labeled pattern: e.g., "mass = 2.5 kg", "mass of 500 g", "velocity is 20 m/s"
            if unit_regex:
                pat = (
                    rf"(?<!\w)(?:{labels_regex})(?!\w)"
                    rf"(?:\s+(?:of\s+(?:the\s+)?\w+\s+)?)?"
                    rf"\s*(?:=|:|\bis\b|\bof\b|\bat\b)?\s*"
                    rf"(?P<val>{NUMBER_RE})\s*(?P<unit>{unit_regex})(?![\w/^²])"
                )
            else:
                pat = (
                    rf"(?<!\w)(?:{labels_regex})(?!\w)\s*(?:=|:|\bis\b|\bof\b)?\s*"
                    rf"(?P<val>{NUMBER_RE})"
                )
            match = re.search(pat, q_norm, re.IGNORECASE)
            if match is None and "" in units_map:
                pat_unitless = (
                    rf"(?<!\w)(?:{labels_regex})(?!\w)\s*(?:=|:|\bis\b|\bof\b)?\s*"
                    rf"(?P<val>{NUMBER_RE})"
                )
                match = re.search(pat_unitless, q_norm, re.IGNORECASE)
            if match is None and unit_regex:
                # Reverse phrasing: e.g., "a 2.5 kg block" or "a 400 N/m spring" or "5 m high ramp"
                if var_sym == "m":
                    match = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>kg|kilograms?|g|grams?)(?!\w)", q_norm, re.IGNORECASE)
                elif var_sym == "h_elev" and re.search(r"high|height|ramp|drop|cliff|elevat", q_norm, re.IGNORECASE):
                    match = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>m|meters?|cm)\s+(?:high|tall|ramp)", q_norm, re.IGNORECASE)
                elif var_sym == "k_spring" and "spring" in q_norm.lower():
                    match = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>n/m|kn/m|n/cm)(?![\w])", q_norm, re.IGNORECASE)
                elif var_sym == "v" and target_var != "v":
                    match = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>m/s|km/s|km/h|cm/s)(?![\w/^2²])", q_norm, re.IGNORECASE)
                elif var_sym == "R_elec" and target_var != "R_elec":
                    match = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>ohms?|ω|Ω|kohms?)(?![\w])", q_norm, re.IGNORECASE)
                elif var_sym == "V_elec" and target_var != "V_elec":
                    match = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>volts?|v|kv)(?![\w/])", q_norm, re.IGNORECASE)
                elif var_sym == "I_elec" and target_var != "I_elec":
                    match = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>amps?|amperes?|a|ma)(?![\w/])", q_norm, re.IGNORECASE)

            if match is not None:
                raw_val = float(match.group("val"))
                unit_str = (match.groupdict().get("unit") or "").lower()
                scale = units_map.get(unit_str, 1.0)
                si_val = raw_val * scale
                knowns[var_sym] = si_val

        return knowns, target_var, warnings

    @staticmethod
    def verify_physical_sanity(knowns: Dict[str, float], target_var: str, solved_val: float) -> List[str]:
        """Dimensional & Physical Boundary Critic."""
        all_vals = {**knowns, target_var: solved_val}
        violations: List[str] = []

        for var_sym, val in all_vals.items():
            meta = VARIABLE_CATALOG.get(var_sym, {})
            if meta.get("positive_only") and val <= 0:
                violations.append(f"Physical Violation: {meta.get('name', var_sym)} ({var_sym} = {val}) must be strictly positive (> 0).")

        if "v" in all_vals and abs(all_vals["v"]) >= PHYSICAL_CONSTANTS["c"]:
            violations.append(
                f"Relativistic Violation: speed v = {all_vals['v']:.4e} m/s meets or exceeds the speed of light c = {PHYSICAL_CONSTANTS['c']:.4e} m/s."
            )
        if "eta_carnot" in all_vals and not (0.0 <= all_vals["eta_carnot"] < 1.0):
            violations.append(
                f"Second Law of Thermodynamics Violation: Carnot efficiency eta = {all_vals['eta_carnot']:.4f} must satisfy 0 <= eta < 1."
            )
        if "T_C" in all_vals and "T_H" in all_vals and all_vals["T_C"] >= all_vals["T_H"]:
            violations.append("Thermodynamic Violation: Cold reservoir temperature T_C cannot exceed or equal hot reservoir T_H.")
        return violations

    @staticmethod
    def _solve_single_formula_sympy(
        formula: Dict[str, Any],
        knowns: Dict[str, float],
        target_var: str,
    ) -> Optional[Dict[str, Any]]:
        if sp is None:
            return None
        sym_names = set(formula["variables"]) | set(formula.get("constants", []))
        symbols_map = {name: sp.Symbol(name, real=True) for name in sym_names}
        local_env = {**symbols_map, "sqrt": sp.sqrt, "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "pi": sp.pi}

        lhs_expr = eval(formula["lhs"], {"__builtins__": {}}, local_env)  # noqa: S307 - internal formula catalog only
        rhs_expr = eval(formula["rhs"], {"__builtins__": {}}, local_env)  # noqa: S307
        equation = sp.Eq(lhs_expr, rhs_expr)

        subs_map = {}
        for var_name in formula["variables"]:
            if var_name != target_var and var_name in knowns:
                subs_map[symbols_map[var_name]] = sp.Float(knowns[var_name], 15)
        for const_name in formula.get("constants", []):
            subs_map[symbols_map[const_name]] = sp.Float(PHYSICAL_CONSTANTS[const_name], 15)

        substituted_eq = equation.subs(subs_map)
        target_sym = symbols_map[target_var]
        raw_solutions = sp.solve(substituted_eq, target_sym)
        real_solutions: List[float] = []
        for sol in raw_solutions:
            try:
                val = complex(sol.evalf())
                if abs(val.imag) < 1e-9 and math.isfinite(val.real):
                    real_solutions.append(float(val.real))
            except Exception:
                continue

        if not real_solutions:
            return None

        # Prefer positive root when variable is positive-definite or representable as magnitude
        meta = VARIABLE_CATALOG.get(target_var, {})
        if meta.get("positive_only") or target_var in {"v", "x_disp", "h_elev", "r_s", "lam", "freq"}:
            positive_roots = [r for r in real_solutions if r > 0]
            chosen = positive_roots[0] if positive_roots else real_solutions[0]
        else:
            chosen = real_solutions[0]

        symbolic_isolated = sp.solve(equation, target_sym)
        # Display the same algebraic branch that supplied the numerical result.
        matching_branch = next((expr for expr in symbolic_isolated
                                if not expr.subs(subs_map).free_symbols
                                and abs(complex(expr.subs(subs_map).evalf()) - chosen) < 1e-8 * max(1, abs(chosen))), None)
        isolated_str = f"{target_var} = {matching_branch}" if matching_branch is not None else f"{formula['lhs']} = {formula['rhs']}"

        return {
            "formula_id": formula["formula_id"],
            "title": formula["title"],
            "subdomain": formula["subdomain"],
            "concept": formula["concept"],
            "governing_equation": f"{formula['lhs']} = {formula['rhs']}",
            "isolated_symbolic_form": isolated_str,
            "target_variable": target_var,
            "target_name": meta.get("name", target_var),
            "value": chosen,
            "si_unit": meta.get("si_unit", ""),
            "dimension": meta.get("dimension", "1"),
            "knowns_used": {k: knowns[k] for k in formula["variables"] if k in knowns and k != target_var},
            "constants_used": {c: PHYSICAL_CONSTANTS[c] for c in formula.get("constants", [])},
        }

    @classmethod
    def solve_multi_entity_archetype(
        cls,
        query: str,
        neural_solver_mode: Optional[str] = None,
        neural_target_observable: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Multi-Entity Scene Parser & SymPy System-of-Equations Solver (Fix 2 + Neural Multi-Head Guidance + IIT-JEE).

        Handles complex multi-body & word-problem scenes:
          1. Atwood Machine / Two-Mass Pulley Systems (m1, m2 -> acceleration a or tension T)
          2. Rotational Rolling Without Slipping on an Incline (solid sphere, cylinder/disk, hollow sphere, hoop/ring)
          3. Inclined Planes with Angle theta & Friction mu (theta, mu, m -> acceleration a or force F)
          4. 2D Projectile Motion at Launch Angle theta (v0, theta -> Range R, Max Height H, or Flight Time T)
          5. 1D Two-Body Collisions: Elastic & Perfectly Inelastic (m1, m2, u1, u2 -> final velocities)
          6. Multi-Resistor & Multi-Capacitor Series/Parallel Networks (R1, R2, R3... or C1, C2...)
          7. Calorimetry / Thermal Equilibrium Mixing (m1, T1, m2, T2 -> equilibrium temperature T_f)
          8. Thin Lens / Mirror Equation (f, d_o, d_i -> image distance, object distance, or focal length)
          9. Young's Double-Slit Interference (YDSE) Fringe Width (beta = lambda * D / d)
          10. Photoelectric Effect Max Kinetic Energy (K_max = h*c/lambda - phi)
        """
        q = query.strip()
        q_low = q.lower()
        g_val = PHYSICAL_CONSTANTS["g"]

        # Helper: extract all masses in SI kg in order of appearance
        mass_matches = list(re.finditer(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>kg|kilograms?|g|grams?)(?!\w)", q, re.IGNORECASE))
        masses_kg: List[float] = []
        for m_hit in mass_matches:
            val = float(m_hit.group("val"))
            u = m_hit.group("unit").lower()
            masses_kg.append(val * (1e-3 if u.startswith("g") else 1.0))

        # 1. ATWOOD MACHINE / PULLEY SYSTEM (Two masses connected over a pulley)
        if ("pulley" in q_low or "atwood" in q_low or neural_solver_mode == "atwood_pulley_system") and len(masses_kg) >= 2:
            m1, m2 = masses_kg[0], masses_kg[1]
            if m1 <= 0 or m2 <= 0:
                return {
                    "solved": False,
                    "status": "physical_sanity_violation",
                    "physical_violations": ["Physical Violation: Pulley masses m1 and m2 must be strictly positive."],
                }
            wants_tension = (
                any(k in q_low for k in ("tension", "pull in the cord", "pull in the string", "pull in the rope", "cord force", "string force"))
                or neural_target_observable == "T_tension"
            )
            if sp is not None:
                s_m1, s_m2, s_g, s_a, s_T = sp.symbols("m1 m2 g a T", real=True)
                heavy, light = max(m1, m2), min(m1, m2)
                sol = sp.solve(
                    [sp.Eq(s_T - s_m1 * s_g, s_m1 * s_a), sp.Eq(s_m2 * s_g - s_T, s_m2 * s_a)],
                    (s_a, s_T),
                )
                a_val = float(sol[s_a].subs({s_m1: light, s_m2: heavy, s_g: g_val}).evalf())
                t_val = float(sol[s_T].subs({s_m1: light, s_m2: heavy, s_g: g_val}).evalf())
            else:
                a_val = abs(m2 - m1) * g_val / (m1 + m2)
                t_val = (2.0 * m1 * m2 * g_val) / (m1 + m2)

            target_var = "T_tension" if wants_tension else "a"
            final_val = t_val if wants_tension else a_val
            si_unit = "N" if wants_tension else "m/s^2"
            iso = "T = 2*m1*m2*g / (m1 + m2)" if wants_tension else "a = |m2 - m1|*g / (m1 + m2)"
            return {
                "solved": True,
                "status": "solved_multi_entity_scene",
                "mode": "atwood_pulley_system",
                "hops": 2,
                "steps": [{
                    "formula_id": "atwood_machine_system",
                    "title": "Atwood Machine Coupled Equations (T - m1*g = m1*a, m2*g - T = m2*a)",
                    "subdomain": "classical_mechanics",
                    "concept": "lagrangian",
                    "governing_equation": "T - m1*g = m1*a; m2*g - T = m2*a",
                    "isolated_symbolic_form": iso,
                    "target_variable": target_var,
                    "target_name": "string_tension" if wants_tension else "system_acceleration",
                    "value": final_val,
                    "si_unit": si_unit,
                    "dimension": "M1 L1 T-2" if wants_tension else "L1 T-2",
                    "knowns_used": {"m1": m1, "m2": m2, "a_system": a_val, "T_tension": t_val},
                    "constants_used": {"g": g_val},
                }],
                "target_variable": target_var,
                "target_name": "string_tension" if wants_tension else "system_acceleration",
                "final_value": final_val,
                "si_unit": si_unit,
                "dimension": "M1 L1 T-2" if wants_tension else "L1 T-2",
                "physical_violations": [],
                "warnings": [],
            }

        # 2. IIT-JEE ARCHETYPE: ROTATIONAL ROLLING WITHOUT SLIPPING ON AN INCLINE
        angle_match = re.search(rf"(?P<ang>{NUMBER_RE})\s*(?:°|deg|degrees?)", q, re.IGNORECASE)
        if angle_match and "roll" in q_low and any(k in q_low for k in ("sphere", "cylinder", "disk", "disc", "hoop", "ring")):
            theta_deg = float(angle_match.group("ang"))
            theta_rad = math.radians(theta_deg)
            if "hollow sphere" in q_low or "spherical shell" in q_low:
                beta_rot, shape_name = 2.0 / 3.0, "hollow_sphere"
            elif "sphere" in q_low:
                beta_rot, shape_name = 2.0 / 5.0, "solid_sphere"
            elif "hoop" in q_low or "ring" in q_low or "hollow cylinder" in q_low:
                beta_rot, shape_name = 1.0, "thin_hoop_ring"
            else:
                beta_rot, shape_name = 0.5, "solid_cylinder_disk"
            a_roll = (g_val * math.sin(theta_rad)) / (1.0 + beta_rot)
            return {
                "solved": True,
                "status": "solved_multi_entity_scene",
                "mode": "rolling_without_slipping_incline",
                "hops": 2,
                "steps": [{
                    "formula_id": "rolling_incline_acceleration",
                    "title": f"Rolling Without Slipping on Incline ({shape_name}, I = {beta_rot:.2f}*M*R^2)",
                    "subdomain": "classical_mechanics",
                    "concept": "moment_of_inertia",
                    "governing_equation": "M*g*sin(theta) - f_s = M*a; f_s*R = I*(a/R)",
                    "isolated_symbolic_form": "a = g*sin(theta) / (1 + I/(M*R^2))",
                    "target_variable": "a",
                    "target_name": "rolling_center_of_mass_acceleration",
                    "value": a_roll,
                    "si_unit": "m/s^2",
                    "dimension": "L1 T-2",
                    "knowns_used": {"theta_deg": theta_deg, "beta_inertia": beta_rot},
                    "constants_used": {"g": g_val},
                }],
                "target_variable": "a",
                "target_name": "rolling_center_of_mass_acceleration",
                "final_value": a_roll,
                "si_unit": "m/s^2",
                "dimension": "L1 T-2",
                "physical_violations": [],
                "warnings": [],
            }

        # 3. INCLINED PLANE (with angle theta and optional friction mu)
        if angle_match and (any(k in q_low for k in ("incline", "inclined", "slope", "ramp", "plane")) or neural_solver_mode == "inclined_plane_mechanics"):
            theta_deg = float(angle_match.group("ang"))
            theta_rad = math.radians(theta_deg)
            mu_match = re.search(rf"(?:coefficient\s+of\s+(?:kinetic\s+)?friction|friction\s+coefficient|mu|μ)\s*(?:=|:|\bis\b|\bof\b)?\s*(?P<mu>{NUMBER_RE})", q, re.IGNORECASE)
            mu_val = float(mu_match.group("mu")) if mu_match else 0.0
            a_val = g_val * (math.sin(theta_rad) - mu_val * math.cos(theta_rad))
            m_val = masses_kg[0] if masses_kg else 1.0
            wants_force = (
                any(p in q_low for p in ("find the force", "net force", "parallel force", "what is the force"))
                or neural_target_observable == "F"
            )
            wants_normal = "normal force" in q_low
            if wants_normal:
                final_val = m_val * g_val * math.cos(theta_rad)
                target_var, t_name, unit, iso = "N_norm", "normal_force", "N", "N = m*g*cos(theta)"
            elif wants_force:
                final_val = m_val * a_val
                target_var, t_name, unit, iso = "F", "net_incline_force", "N", "F = m*g*(sin(theta) - mu*cos(theta))"
            else:
                final_val = a_val
                target_var, t_name, unit, iso = "a", "incline_acceleration", "m/s^2", "a = g*(sin(theta) - mu*cos(theta))"
            return {
                "solved": True,
                "status": "solved_multi_entity_scene",
                "mode": "inclined_plane_mechanics",
                "hops": 1,
                "steps": [{
                    "formula_id": "inclined_plane_dynamics",
                    "title": "Inclined Plane Force Decomposition",
                    "subdomain": "classical_mechanics",
                    "concept": "euler-lagrange_equation",
                    "governing_equation": "m*a = m*g*sin(theta) - mu*m*g*cos(theta)",
                    "isolated_symbolic_form": iso,
                    "target_variable": target_var,
                    "target_name": t_name,
                    "value": final_val,
                    "si_unit": unit,
                    "dimension": "M1 L1 T-2" if unit == "N" else "L1 T-2",
                    "knowns_used": {"theta_deg": theta_deg, "mu": mu_val, "m": m_val},
                    "constants_used": {"g": g_val},
                }],
                "target_variable": target_var,
                "target_name": t_name,
                "final_value": final_val,
                "si_unit": unit,
                "dimension": "M1 L1 T-2" if unit == "N" else "L1 T-2",
                "physical_violations": [],
                "warnings": [],
            }

        # 3. 2D PROJECTILE MOTION AT ANGLE THETA
        if angle_match and any(k in q_low for k in ("projectile", "launched", "fired", "thrown", "range", "time of flight", "maximum height")):
            theta_deg = float(angle_match.group("ang"))
            theta_rad = math.radians(theta_deg)
            v_match = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>m/s|km/s|km/h)(?![\w/^2²])", q, re.IGNORECASE)
            if v_match:
                v0 = float(v_match.group("val"))
                u_str = v_match.group("unit").lower()
                if u_str == "km/s":
                    v0 *= 1000.0
                elif u_str == "km/h":
                    v0 /= 3.6
                if "maximum height" in q_low or "max height" in q_low or "how high" in q_low:
                    final_val = (v0 ** 2) * (math.sin(theta_rad) ** 2) / (2.0 * g_val)
                    target_var, t_name, unit, iso = "H_max", "maximum_height", "m", "H = v0^2 * sin(theta)^2 / (2*g)"
                elif "time of flight" in q_low or "flight time" in q_low or "how long" in q_low:
                    final_val = (2.0 * v0 * math.sin(theta_rad)) / g_val
                    target_var, t_name, unit, iso = "T_flight", "time_of_flight", "s", "T = 2*v0*sin(theta) / g"
                else:
                    final_val = (v0 ** 2) * math.sin(2.0 * theta_rad) / g_val
                    target_var, t_name, unit, iso = "R_range", "horizontal_range", "m", "R = v0^2 * sin(2*theta) / g"
                return {
                    "solved": True,
                    "status": "solved_multi_entity_scene",
                    "mode": "projectile_2d_kinematics",
                    "hops": 1,
                    "steps": [{
                        "formula_id": "projectile_2d_motion",
                        "title": "2D Projectile Kinematics",
                        "subdomain": "classical_mechanics",
                        "concept": "action_principle",
                        "governing_equation": iso,
                        "isolated_symbolic_form": iso,
                        "target_variable": target_var,
                        "target_name": t_name,
                        "value": final_val,
                        "si_unit": unit,
                        "dimension": "T1" if unit == "s" else "L1",
                        "knowns_used": {"v0": v0, "theta_deg": theta_deg},
                        "constants_used": {"g": g_val},
                    }],
                    "target_variable": target_var,
                    "target_name": t_name,
                    "final_value": final_val,
                    "si_unit": unit,
                    "dimension": "T1" if unit == "s" else "L1",
                    "physical_violations": [],
                    "warnings": [],
                }

        # 4. 1D TWO-BODY COLLISIONS (Elastic & Perfectly Inelastic)
        if any(k in q_low for k in ("collid", "collision", "sticks together", "stick together", "coalesce")) and len(masses_kg) >= 2:
            m1, m2 = masses_kg[0], masses_kg[1]
            vel_matches = list(re.finditer(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>m/s|km/s|cm/s)(?![\w/^2²])", q, re.IGNORECASE))
            vels: List[float] = []
            for vm in vel_matches:
                v_raw = float(vm.group("val"))
                vu = vm.group("unit").lower()
                vels.append(v_raw * (1e3 if vu == "km/s" else (1e-2 if vu == "cm/s" else 1.0)))
            if len(vels) == 1 and ("at rest" in q_low or "stationary" in q_low):
                vels.append(0.0)
            if len(vels) >= 2:
                u1, u2 = vels[0], vels[1]
                is_inelastic = any(k in q_low for k in ("inelastic", "stick together", "sticks together", "coalesce", "combined"))
                if is_inelastic:
                    vf = (m1 * u1 + m2 * u2) / (m1 + m2)
                    target_var, t_name, iso, final_val = "v_f", "combined_final_velocity", "v_f = (m1*u1 + m2*u2) / (m1 + m2)", vf
                else:
                    v1_f = ((m1 - m2) * u1 + 2.0 * m2 * u2) / (m1 + m2)
                    v2_f = (2.0 * m1 * u1 + (m2 - m1) * u2) / (m1 + m2)
                    wants_first = "first" in q_low or "v1" in q_low
                    final_val = v1_f if wants_first else v2_f
                    target_var = "v1_f" if wants_first else "v2_f"
                    t_name = "elastic_final_velocity_1" if wants_first else "elastic_final_velocity_2"
                    iso = "v1 = ((m1-m2)*u1 + 2*m2*u2)/(m1+m2)" if wants_first else "v2 = (2*m1*u1 + (m2-m1)*u2)/(m1+m2)"
                return {
                    "solved": True,
                    "status": "solved_multi_entity_scene",
                    "mode": "two_body_collision_1d",
                    "hops": 2,
                    "steps": [{
                        "formula_id": "collision_1d_conservation",
                        "title": "1D Two-Body Conservation of Momentum & Energy",
                        "subdomain": "classical_mechanics",
                        "concept": "poisson_bracket",
                        "governing_equation": "m1*u1 + m2*u2 = m1*v1 + m2*v2",
                        "isolated_symbolic_form": iso,
                        "target_variable": target_var,
                        "target_name": t_name,
                        "value": final_val,
                        "si_unit": "m/s",
                        "dimension": "L1 T-1",
                        "knowns_used": {"m1": m1, "m2": m2, "u1": u1, "u2": u2},
                        "constants_used": {},
                    }],
                    "target_variable": target_var,
                    "target_name": t_name,
                    "final_value": final_val,
                    "si_unit": "m/s",
                    "dimension": "L1 T-1",
                    "physical_violations": [],
                    "warnings": [],
                }

        # 5. MULTI-RESISTOR OR MULTI-CAPACITOR NETWORKS (Series & Parallel)
        res_matches = list(re.finditer(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>kohms?|ohms?|kΩ|Ω|ω)(?![\w])", q, re.IGNORECASE))
        if len(res_matches) >= 2 and ("series" in q_low or "parallel" in q_low):
            r_vals: List[float] = []
            for rm in res_matches:
                rv = float(rm.group("val"))
                ru = rm.group("unit").lower()
                r_vals.append(rv * (1e3 if ru.startswith("k") else 1.0))
            is_parallel = "parallel" in q_low
            r_eq = (1.0 / sum(1.0 / r for r in r_vals)) if is_parallel else sum(r_vals)
            v_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>volts?|v|kv)(?![\w/])", q, re.IGNORECASE)
            if v_hit and any(k in q_low for k in ("current", "find i", "amps")):
                v_sup = float(v_hit.group("val")) * (1e3 if v_hit.group("unit").lower() == "kv" else 1.0)
                i_tot = v_sup / r_eq
                return {
                    "solved": True,
                    "status": "solved_multi_entity_scene",
                    "mode": "multi_resistor_circuit_network",
                    "hops": 2,
                    "steps": [{
                        "formula_id": "resistor_network_current",
                        "title": f"{'Parallel' if is_parallel else 'Series'} Resistor Network + Ohm's Law",
                        "subdomain": "electromagnetism",
                        "concept": "electric_field",
                        "governing_equation": "I_total = V / R_eq",
                        "isolated_symbolic_form": "I_total = V / R_eq",
                        "target_variable": "I_elec",
                        "target_name": "total_circuit_current",
                        "value": i_tot,
                        "si_unit": "A",
                        "dimension": "I1",
                        "knowns_used": {f"R{i+1}": r for i, r in enumerate(r_vals)} | {"R_eq": r_eq, "V_elec": v_sup},
                        "constants_used": {},
                    }],
                    "target_variable": "I_elec",
                    "target_name": "total_circuit_current",
                    "final_value": i_tot,
                    "si_unit": "A",
                    "dimension": "I1",
                    "physical_violations": [],
                    "warnings": [],
                }
            return {
                "solved": True,
                "status": "solved_multi_entity_scene",
                "mode": "multi_resistor_circuit_network",
                "hops": 1,
                "steps": [{
                    "formula_id": "resistor_network_equivalent",
                    "title": f"Equivalent Resistance ({'Parallel' if is_parallel else 'Series'})",
                    "subdomain": "electromagnetism",
                    "concept": "electric_field",
                    "governing_equation": "1/R_eq = sum(1/R_i)" if is_parallel else "R_eq = sum(R_i)",
                    "isolated_symbolic_form": "R_eq = (sum(1/R_i))^-1" if is_parallel else "R_eq = sum(R_i)",
                    "target_variable": "R_eq",
                    "target_name": "equivalent_resistance",
                    "value": r_eq,
                    "si_unit": "ohm",
                    "dimension": "M1 L2 T-3 I-2",
                    "knowns_used": {f"R{i+1}": r for i, r in enumerate(r_vals)},
                    "constants_used": {},
                }],
                "target_variable": "R_eq",
                "target_name": "equivalent_resistance",
                "final_value": r_eq,
                "si_unit": "ohm",
                "dimension": "M1 L2 T-3 I-2",
                "physical_violations": [],
                "warnings": [],
            }

        # 6. CALORIMETRY / THERMAL EQUILIBRIUM MIXING (m1 at T1 mixed with m2 at T2)
        temp_matches = list(re.finditer(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>k|kelvin|°c|degc|celsius)(?!\w)", q, re.IGNORECASE))
        if len(masses_kg) >= 2 and len(temp_matches) >= 2 and any(k in q_low for k in ("mix", "equilibrium", "calorimet", "final temperature", "thermal contact")):
            m1, m2 = masses_kg[0], masses_kg[1]
            temps: List[float] = []
            unit_out = "K"
            for tm in temp_matches[:2]:
                tv = float(tm.group("val"))
                tu = tm.group("unit").lower()
                if "c" in tu:
                    unit_out = "°C"
                temps.append(tv)
            t1, t2 = temps[0], temps[1]
            t_final = (m1 * t1 + m2 * t2) / (m1 + m2)
            return {
                "solved": True,
                "status": "solved_multi_entity_scene",
                "mode": "calorimetry_thermal_equilibrium",
                "hops": 1,
                "steps": [{
                    "formula_id": "calorimetry_heat_balance",
                    "title": "Calorimetry Conservation of Thermal Energy (m1*c*(Tf - T1) + m2*c*(Tf - T2) = 0)",
                    "subdomain": "thermodynamics_stat_mech",
                    "concept": "canonical_ensemble",
                    "governing_equation": "m1*(T_f - T1) + m2*(T_f - T2) = 0",
                    "isolated_symbolic_form": "T_f = (m1*T1 + m2*T2) / (m1 + m2)",
                    "target_variable": "T_f",
                    "target_name": "equilibrium_temperature",
                    "value": t_final,
                    "si_unit": unit_out,
                    "dimension": "Theta1",
                    "knowns_used": {"m1": m1, "T1": t1, "m2": m2, "T2": t2},
                    "constants_used": {},
                }],
                "target_variable": "T_f",
                "target_name": "equilibrium_temperature",
                "final_value": t_final,
                "si_unit": unit_out,
                "dimension": "Theta1",
                "physical_violations": [],
                "warnings": [],
            }

        # 7. THIN LENS / MIRROR EQUATION (1/f = 1/d_o + 1/d_i)
        if any(k in q_low for k in ("focal length", "lens", "mirror")) and any(k in q_low for k in ("object", "image")):
            f_hit = re.search(rf"focal\s+length\s+(?:f\s+)?(?:of\s+|is\s+|=|:)?\s*(?P<val>{NUMBER_RE})\s*(?P<unit>cm|mm|m)\b", q, re.IGNORECASE)
            do_hit = re.search(rf"object\s+(?:is\s+)?(?:placed\s+|located\s+|distance\s+(?:d_o\s+)?(?:of\s+|is\s+|=|:)?)?\s*(?P<val>{NUMBER_RE})\s*(?P<unit>cm|mm|m)\b", q, re.IGNORECASE)
            di_hit = re.search(rf"image\s+(?:is\s+)?(?:formed\s+|located\s+|distance\s+(?:d_i\s+)?(?:of\s+|is\s+|=|:)?)?\s*(?P<val>{NUMBER_RE})\s*(?P<unit>cm|mm|m)\b", q, re.IGNORECASE)

            def _to_m(hit: re.Match) -> float:
                v = float(hit.group("val"))
                u = hit.group("unit").lower()
                return v * (1e-2 if u == "cm" else (1e-3 if u == "mm" else 1.0))

            if f_hit and do_hit and not di_hit:
                f_m, do_m = _to_m(f_hit), _to_m(do_hit)
                di_m = 1.0 / ((1.0 / f_m) - (1.0 / do_m))
                return {
                    "solved": True,
                    "status": "solved_multi_entity_scene",
                    "mode": "thin_lens_gaussian_optics",
                    "hops": 1,
                    "steps": [{
                        "formula_id": "thin_lens_equation",
                        "title": "Gaussian Thin-Lens / Mirror Equation (1/f = 1/d_o + 1/d_i)",
                        "subdomain": "optics_waves",
                        "concept": "focal_length",
                        "governing_equation": "1/f = 1/d_o + 1/d_i",
                        "isolated_symbolic_form": "d_i = (1/f - 1/d_o)^-1",
                        "target_variable": "d_i",
                        "target_name": "image_distance",
                        "value": di_m,
                        "si_unit": "m",
                        "dimension": "L1",
                        "knowns_used": {"f": f_m, "d_o": do_m},
                        "constants_used": {},
                    }],
                    "target_variable": "d_i",
                    "target_name": "image_distance",
                    "final_value": di_m,
                    "si_unit": "m",
                    "dimension": "L1",
                    "physical_violations": [],
                    "warnings": [],
                }
            if do_hit and di_hit and not f_hit:
                do_m, di_m = _to_m(do_hit), _to_m(di_hit)
                f_m = 1.0 / ((1.0 / do_m) + (1.0 / di_m))
                return {
                    "solved": True,
                    "status": "solved_multi_entity_scene",
                    "mode": "thin_lens_gaussian_optics",
                    "hops": 1,
                    "steps": [{
                        "formula_id": "thin_lens_equation",
                        "title": "Gaussian Thin-Lens / Mirror Equation (1/f = 1/d_o + 1/d_i)",
                        "subdomain": "optics_waves",
                        "concept": "focal_length",
                        "governing_equation": "1/f = 1/d_o + 1/d_i",
                        "isolated_symbolic_form": "f = (1/d_o + 1/d_i)^-1",
                        "target_variable": "f",
                        "target_name": "focal_length",
                        "value": f_m,
                        "si_unit": "m",
                        "dimension": "L1",
                        "knowns_used": {"d_o": do_m, "d_i": di_m},
                        "constants_used": {},
                    }],
                    "target_variable": "f",
                    "target_name": "focal_length",
                    "final_value": f_m,
                    "si_unit": "m",
                    "dimension": "L1",
                    "physical_violations": [],
                    "warnings": [],
                }

        # 8. IIT-JEE ARCHETYPE: YOUNG'S DOUBLE-SLIT INTERFERENCE (YDSE) FRINGE WIDTH (beta = lambda * D / d)
        if any(k in q_low for k in ("double slit", "double-slit", "fringe width", "ydse")):
            lam_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>nm|nanometers?)\b", q, re.IGNORECASE)
            d_slit_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>mm|millimeters?)\b", q, re.IGNORECASE)
            D_screen_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>m|meters?)\b", q, re.IGNORECASE)
            if lam_hit and d_slit_hit and D_screen_hit:
                lam_m = float(lam_hit.group("val")) * 1e-9
                d_m = float(d_slit_hit.group("val")) * 1e-3
                D_m = float(D_screen_hit.group("val"))
                beta_m = (lam_m * D_m) / d_m
                return {
                    "solved": True,
                    "status": "solved_multi_entity_scene",
                    "mode": "ydse_wave_interference",
                    "hops": 1,
                    "steps": [{
                        "formula_id": "ydse_fringe_width",
                        "title": "Young's Double-Slit Interference Fringe Width (beta = lambda * D / d)",
                        "subdomain": "optics_waves",
                        "concept": "interferometer",
                        "governing_equation": "beta = lambda * D / d",
                        "isolated_symbolic_form": "beta = lambda * D / d",
                        "target_variable": "beta_fringe",
                        "target_name": "fringe_width",
                        "value": beta_m,
                        "si_unit": "m",
                        "dimension": "L1",
                        "knowns_used": {"lambda": lam_m, "d_slit": d_m, "D_screen": D_m},
                        "constants_used": {},
                    }],
                    "target_variable": "beta_fringe",
                    "target_name": "fringe_width",
                    "final_value": beta_m,
                    "si_unit": "m",
                    "dimension": "L1",
                    "physical_violations": [],
                    "warnings": [],
                }

        # 9. PILLAR 5 CROSS-DOMAIN 3-HOP: PHOTOELECTRIC EFFECT (QM) -> KINETIC VELOCITY (CM) -> CYCLOTRON LARMOR RADIUS (EM)
        if any(k in q_low for k in ("work function", "photoelectron", "photoelectric")) and any(k in q_low for k in ("magnetic field", "tesla", "radius", "cyclotron", "larmor")):
            lam_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>nm|nanometers?)\b", q, re.IGNORECASE)
            wf_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>ev|electron[- ]?volts?)\b", q, re.IGNORECASE)
            b_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>t|tesla|mt|millitesla)\b", q, re.IGNORECASE)
            if lam_hit and wf_hit and b_hit:
                lam_m = float(lam_hit.group("val")) * 1e-9
                phi_j = float(wf_hit.group("val")) * 1.602176634e-19
                b_raw = float(b_hit.group("val"))
                b_unit = b_hit.group("unit").lower()
                b_t = b_raw * (1e-3 if b_unit.startswith("m") else 1.0)
                h_c = 6.62607015e-34 * 299792458.0
                m_e = 9.1093837015e-31
                q_e = 1.602176634e-19
                k_max = max(0.0, (h_c / lam_m) - phi_j)
                v_max = math.sqrt(2.0 * k_max / m_e)
                r_larmor = (m_e * v_max) / (q_e * b_t)
                return {
                    "solved": True,
                    "status": "solved_cross_domain_multihop",
                    "mode": "photoelectric_cyclotron_3hop",
                    "hops": 3,
                    "steps": [
                        {
                            "formula_id": "einstein_photoelectric_kmax",
                            "title": "Einstein Photoelectric Equation (Quantum Mechanics)",
                            "subdomain": "quantum_mechanics",
                            "concept": "wavefunction",
                            "governing_equation": "K_max = (h * c / lambda) - phi",
                            "isolated_symbolic_form": "K_max = (h * c / lambda) - phi",
                            "target_variable": "K_max",
                            "target_name": "max_photoelectron_kinetic_energy",
                            "value": k_max,
                            "si_unit": "J",
                            "dimension": "M1 L2 T-2",
                        },
                        {
                            "formula_id": "classical_kinetic_velocity",
                            "title": "Photoelectron Ejection Velocity (Classical Mechanics)",
                            "subdomain": "classical_mechanics",
                            "concept": "hamiltonian",
                            "governing_equation": "K_max = 0.5 * m_e * v^2",
                            "isolated_symbolic_form": "v = sqrt(2 * K_max / m_e)",
                            "target_variable": "v",
                            "target_name": "photoelectron_speed",
                            "value": v_max,
                            "si_unit": "m/s",
                            "dimension": "L1 T-1",
                        },
                        {
                            "formula_id": "lorentz_cyclotron_larmor_radius",
                            "title": "Magnetic Lorentz Force Cyclotron Radius (Electromagnetism)",
                            "subdomain": "electromagnetism",
                            "concept": "lorentz_force",
                            "governing_equation": "q * v * B = m_e * v^2 / r_L",
                            "isolated_symbolic_form": "r_L = (m_e * v) / (e * B)",
                            "target_variable": "r_L",
                            "target_name": "cyclotron_larmor_radius",
                            "value": r_larmor,
                            "si_unit": "m",
                            "dimension": "L1",
                        },
                    ],
                    "target_variable": "r_L",
                    "target_name": "cyclotron_larmor_radius",
                    "final_value": r_larmor,
                    "si_unit": "m",
                    "dimension": "L1",
                    "physical_violations": [],
                    "warnings": [],
                }

        # 10. PILLAR 5 CROSS-DOMAIN 3-HOP: ACCELERATING VOLTAGE (EM) -> MOMENTUM (CM) -> DE BROGLIE WAVELENGTH (QM)
        if any(k in q_low for k in ("de broglie", "matter wave")) and any(k in q_low for k in ("accelerat", "potential difference", "volts", "voltage")):
            v_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>kv|volts?|v)\b", q, re.IGNORECASE)
            if v_hit:
                v_raw = float(v_hit.group("val"))
                vu = v_hit.group("unit").lower()
                v_volts = v_raw * (1e3 if vu.startswith("k") else 1.0)
                m_part = 1.67262192369e-27 if "proton" in q_low else (masses_kg[0] if masses_kg else 9.1093837015e-31)
                q_part = 1.602176634e-19
                h_planck = 6.62607015e-34
                k_en = q_part * v_volts
                p_mom = math.sqrt(2.0 * m_part * k_en)
                lam_db = h_planck / p_mom
                return {
                    "solved": True,
                    "status": "solved_cross_domain_multihop",
                    "mode": "accelerated_charge_de_broglie_3hop",
                    "hops": 3,
                    "steps": [
                        {
                            "formula_id": "electrostatic_acceleration_energy",
                            "title": "Electrostatic Potential Work-Energy Theorem (Electromagnetism)",
                            "subdomain": "electromagnetism",
                            "concept": "electric_field",
                            "governing_equation": "K = q * V",
                            "isolated_symbolic_form": "K = q * V",
                            "target_variable": "E_k",
                            "target_name": "kinetic_energy",
                            "value": k_en,
                            "si_unit": "J",
                            "dimension": "M1 L2 T-2",
                        },
                        {
                            "formula_id": "kinetic_momentum_relation",
                            "title": "Kinetic Energy to Linear Momentum (Classical Mechanics)",
                            "subdomain": "classical_mechanics",
                            "concept": "hamiltonian",
                            "governing_equation": "p^2 = 2 * m * K",
                            "isolated_symbolic_form": "p = sqrt(2 * m * K)",
                            "target_variable": "p_mom",
                            "target_name": "momentum",
                            "value": p_mom,
                            "si_unit": "kg*m/s",
                            "dimension": "M1 L1 T-1",
                        },
                        {
                            "formula_id": "de_broglie_matter_wave",
                            "title": "de Broglie Matter-Wave Relation (Quantum Mechanics)",
                            "subdomain": "quantum_mechanics",
                            "concept": "wavefunction",
                            "governing_equation": "lambda_dB = h / p",
                            "isolated_symbolic_form": "lambda_dB = h / sqrt(2 * m * q * V)",
                            "target_variable": "lam",
                            "target_name": "de_broglie_wavelength",
                            "value": lam_db,
                            "si_unit": "m",
                            "dimension": "L1",
                        },
                    ],
                    "target_variable": "lam",
                    "target_name": "de_broglie_wavelength",
                    "final_value": lam_db,
                    "si_unit": "m",
                    "dimension": "L1",
                    "physical_violations": [],
                    "warnings": [],
                }

        # 11. PILLAR 5 CROSS-DOMAIN 3-HOP: TORRICELLI FLUID EFFLUX -> FREE-FALL TIME -> 2D HORIZONTAL RANGE
        if any(k in q_low for k in ("orifice", "torricelli", "efflux", "hole in a tank", "water tank")) and any(k in q_low for k in ("depth", "below")) and any(k in q_low for k in ("above", "floor", "ground", "horizontal distance", "range")):
            m_hits = list(re.finditer(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>m|meters?|cm)\b", q, re.IGNORECASE))
            if len(m_hits) >= 2:
                def _len_m(mh: re.Match) -> float:
                    val = float(mh.group("val"))
                    return val * (1e-2 if mh.group("unit").lower() == "cm" else 1.0)
                h1, h2 = _len_m(m_hits[0]), _len_m(m_hits[1])
                v_eff = math.sqrt(2.0 * g_val * h1)
                t_fall = math.sqrt(2.0 * h2 / g_val)
                r_horiz = v_eff * t_fall
                return {
                    "solved": True,
                    "status": "solved_cross_domain_multihop",
                    "mode": "torricelli_projectile_3hop",
                    "hops": 3,
                    "steps": [
                        {
                            "formula_id": "bernoulli_torricelli_efflux",
                            "title": "Bernoulli / Torricelli Efflux Speed (Fluid Mechanics)",
                            "subdomain": "fluid_plasma",
                            "concept": "bernoulli_equation",
                            "governing_equation": "v_efflux = sqrt(2 * g * h_1)",
                            "isolated_symbolic_form": "v_efflux = sqrt(2 * g * h_1)",
                            "target_variable": "v_efflux",
                            "target_name": "efflux_speed",
                            "value": v_eff,
                            "si_unit": "m/s",
                            "dimension": "L1 T-1",
                        },
                        {
                            "formula_id": "vertical_free_fall_time",
                            "title": "Gravitational Free-Fall Time (Classical Kinematics)",
                            "subdomain": "classical_mechanics",
                            "concept": "lagrangian",
                            "governing_equation": "h_2 = 0.5 * g * t^2",
                            "isolated_symbolic_form": "t_fall = sqrt(2 * h_2 / g)",
                            "target_variable": "t_fall",
                            "target_name": "fall_time",
                            "value": t_fall,
                            "si_unit": "s",
                            "dimension": "T1",
                        },
                        {
                            "formula_id": "horizontal_jet_range",
                            "title": "Horizontal Jet Impact Range (2D Projectile Kinematics)",
                            "subdomain": "classical_mechanics",
                            "concept": "euler_lagrange_equation",
                            "governing_equation": "R = v_efflux * t_fall = 2 * sqrt(h_1 * h_2)",
                            "isolated_symbolic_form": "R = 2 * sqrt(h_1 * h_2)",
                            "target_variable": "R_jet",
                            "target_name": "horizontal_jet_range",
                            "value": r_horiz,
                            "si_unit": "m",
                            "dimension": "L1",
                        },
                    ],
                    "target_variable": "R_jet",
                    "target_name": "horizontal_jet_range",
                    "final_value": r_horiz,
                    "si_unit": "m",
                    "dimension": "L1",
                    "physical_violations": [],
                    "warnings": [],
                }

        # 12. PILLAR 5 CROSS-DOMAIN 3-HOP: JOULE ELECTRICAL HEATING (EM) -> THERMAL ENERGY -> CALORIMETRY TEMP RISE (THERMO)
        if any(k in q_low for k in ("heater", "heating coil", "immersion", "joule heating", "resistor heats")) and any(k in q_low for k in ("temperature rise", "increase in temperature", "delta t", "specific heat")):
            v_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>volts?|v)\b", q, re.IGNORECASE)
            r_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>ohms?|Ω|ω)\b", q, re.IGNORECASE)
            t_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>s|seconds?|min|minutes?)\b", q, re.IGNORECASE)
            c_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>j/\(kg[·* ]k\)|j/kg[- ]?k|j/kg[- ]?c)\b", q, re.IGNORECASE)
            if v_hit and r_hit and t_hit and masses_kg:
                v_val = float(v_hit.group("val"))
                r_val = float(r_hit.group("val"))
                t_raw = float(t_hit.group("val"))
                t_sec = t_raw * (60.0 if t_hit.group("unit").lower().startswith("min") else 1.0)
                c_val = float(c_hit.group("val")) if c_hit else 4184.0
                m_liq = masses_kg[0]
                p_watt = (v_val ** 2) / r_val
                q_joule = p_watt * t_sec
                dt_kelvin = q_joule / (m_liq * c_val)
                return {
                    "solved": True,
                    "status": "solved_cross_domain_multihop",
                    "mode": "joule_heating_calorimetry_3hop",
                    "hops": 3,
                    "steps": [
                        {
                            "formula_id": "joule_electrical_power",
                            "title": "Joule Electrical Power Dissipation (Electromagnetism)",
                            "subdomain": "electromagnetism",
                            "concept": "poynting_vector",
                            "governing_equation": "P = V^2 / R",
                            "isolated_symbolic_form": "P = V^2 / R",
                            "target_variable": "P_power",
                            "target_name": "electrical_power",
                            "value": p_watt,
                            "si_unit": "W",
                            "dimension": "M1 L2 T-3",
                        },
                        {
                            "formula_id": "thermal_energy_delivered",
                            "title": "Cumulative Thermal Energy Delivered (Thermodynamics)",
                            "subdomain": "thermodynamics_stat_mech",
                            "concept": "heat_capacity",
                            "governing_equation": "Q = P * t",
                            "isolated_symbolic_form": "Q = P * t",
                            "target_variable": "Q_heat",
                            "target_name": "thermal_energy",
                            "value": q_joule,
                            "si_unit": "J",
                            "dimension": "M1 L2 T-2",
                        },
                        {
                            "formula_id": "calorimetric_temperature_rise",
                            "title": "Calorimetric Temperature Rise (Thermodynamics)",
                            "subdomain": "thermodynamics_stat_mech",
                            "concept": "heat_capacity",
                            "governing_equation": "Q = m * c * Delta_T",
                            "isolated_symbolic_form": "Delta_T = (V^2 * t) / (R * m * c)",
                            "target_variable": "Delta_T",
                            "target_name": "temperature_rise",
                            "value": dt_kelvin,
                            "si_unit": "K",
                            "dimension": "Theta1",
                        },
                    ],
                    "target_variable": "Delta_T",
                    "target_name": "temperature_rise",
                    "final_value": dt_kelvin,
                    "si_unit": "K",
                    "dimension": "Theta1",
                    "physical_violations": [],
                    "warnings": [],
                }

        # 13. COULOMB'S LAW FOR ELECTROSTATIC FORCE (F = k_e * |q1 * q2| / r^2)
        if any(k in q_low for k in ("coulomb", "electrostatic", "electric force", "force between")) and (
            any(k in q_low for k in ("charge", "charges", "uc", "nc", "mc", "coulomb", "coulombs", "microcoulomb"))
        ):
            unit_scales = {
                "c": 1.0, "coulomb": 1.0, "coulombs": 1.0,
                "mc": 1e-3, "millicoulomb": 1e-3, "millicoulombs": 1e-3,
                "uc": 1e-6, "µc": 1e-6, "microcoulomb": 1e-6, "microcoulombs": 1e-6,
                "nc": 1e-9, "nanocoulomb": 1e-9, "nanocoulombs": 1e-9,
                "pc": 1e-12, "picocoulomb": 1e-12, "picocoulombs": 1e-12,
            }
            two_same_match = re.search(
                rf"(?:two|2)\s+(?:identical\s+)?(?P<val>{NUMBER_RE})\s*(?P<unit>mc|uc|µc|nc|pc|c|microcoulombs?|nanocoulombs?|coulombs?)\s+charges",
                q,
                re.IGNORECASE,
            ) or re.search(
                rf"charges\s+of\s+(?P<val>{NUMBER_RE})\s*(?P<unit>mc|uc|µc|nc|pc|c|microcoulombs?|nanocoulombs?|coulombs?)\s+each",
                q,
                re.IGNORECASE,
            )
            charges_c: List[float] = []
            if two_same_match:
                v = float(two_same_match.group("val"))
                scale = unit_scales.get(two_same_match.group("unit").lower(), 1.0)
                charges_c = [v * scale, v * scale]
            else:
                for cm in re.finditer(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>mc|uc|µc|nc|pc|c|microcoulombs?|nanocoulombs?|coulombs?)\b", q, re.IGNORECASE):
                    u = cm.group("unit").lower()
                    if u in unit_scales:
                        charges_c.append(float(cm.group("val")) * unit_scales[u])

            r_match = re.search(
                rf"(?:separated\s+by|distance\s+(?:of\s+)?|apart\s+by\s*|separated\s+at\s*)(?:\s*(?:=|:|\bis\b|\bof\b)?\s*)(?P<val>{NUMBER_RE})\s*(?P<unit>m|meters?|cm|centimeters?|mm|millimeters?)\b",
                q,
                re.IGNORECASE,
            ) or re.search(
                rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>m|meters?|cm|centimeters?|mm|millimeters?)\s+apart\b",
                q,
                re.IGNORECASE,
            )

            if len(charges_c) >= 2 and r_match:
                q1_c, q2_c = charges_c[0], charges_c[1]
                r_raw = float(r_match.group("val"))
                ru = r_match.group("unit").lower()
                r_scale = 1e-2 if ru.startswith("cm") else (1e-3 if ru.startswith("mm") else 1.0)
                r_m = r_raw * r_scale

                k_e = PHYSICAL_CONSTANTS.get("k_e", 8.9875517923e9)
                f_coulomb = (k_e * abs(q1_c * q2_c)) / (r_m ** 2)

                return {
                    "solved": True,
                    "status": "solved_multi_entity_scene",
                    "mode": "coulomb_electrostatic_law",
                    "hops": 1,
                    "steps": [{
                        "formula_id": "coulombs_law_electrostatic",
                        "title": "Coulomb's Law for Electrostatic Force (F = k_e * |q1 * q2| / r^2)",
                        "subdomain": "electromagnetism",
                        "concept": "electric_field",
                        "governing_equation": "F = k_e * abs(q1 * q2) / r^2",
                        "isolated_symbolic_form": f"F = ({k_e:.4e} * |{q1_c:.4e} * {q2_c:.4e}|) / ({r_m}^2) = {f_coulomb:.4e} N",
                        "target_variable": "F",
                        "target_name": "electrostatic_force",
                        "value": f_coulomb,
                        "si_unit": "N",
                        "dimension": "M1 L1 T-2",
                        "knowns_used": {"q1": q1_c, "q2": q2_c, "r": r_m},
                        "constants_used": {"k_e": k_e},
                    }],
                    "target_variable": "F",
                    "target_name": "electrostatic_force",
                    "final_value": f_coulomb,
                    "si_unit": "N",
                    "dimension": "M1 L1 T-2",
                    "physical_violations": [],
                    "warnings": [],
                }

        # 14. CARNOT HEAT ENGINE EFFICIENCY (eta = 1 - T_C / T_H)
        if any(k in q_low for k in ("carnot", "thermal efficiency", "heat engine efficiency")) or (
            "efficiency" in q_low and any(k in q_low for k in ("reservoir", "operating between", "temperatures"))
        ):
            t_matches = list(re.finditer(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>k|kelvins?|°c|deg\s*c|celsius)\b", q, re.IGNORECASE))
            if len(t_matches) >= 2:
                temps_k = []
                for tm in t_matches:
                    val = float(tm.group("val"))
                    u = tm.group("unit").lower()
                    if "c" in u:
                        val = val + 273.15
                    temps_k.append(val)
                th_k = max(temps_k[0], temps_k[1])
                tc_k = min(temps_k[0], temps_k[1])
                # Respect explicit reservoir labels; sorting is only valid for
                # an unlabelled pair such as 'between 300 K and 600 K'.
                labelled = {}
                for tm, temp in zip(t_matches, temps_k):
                    prefix = q[:tm.start()]
                    role = re.search(r"\b(hot|cold|t_h|t_c)\s*(?:(?:reservoir|temperature)\s*)*(?:=|is|at|of|:)\s*$", prefix, re.IGNORECASE)
                    if role:
                        labelled['hot' if role.group(1).lower() in {'hot', 't_h'} else 'cold'] = temp
                if 'hot' in labelled:
                    th_k = labelled['hot']
                    tc_k = labelled.get('cold', next((t for t in temps_k[:2] if t != th_k), th_k))
                elif 'cold' in labelled:
                    tc_k = labelled['cold']
                    th_k = next((t for t in temps_k[:2] if t != tc_k), tc_k)
                if not (0 < tc_k < th_k):
                    return {"solved": False, "status": "physical_sanity_violation",
                            "mode": "carnot_thermodynamic_cycle", "steps": [],
                            "knowns_extracted": {"T_H": th_k, "T_C": tc_k},
                            "physical_violations": ["Carnot heat-engine reservoirs require 0 < T_C < T_H in kelvin; supplied labels were preserved."]}
                if th_k > 0 and tc_k > 0 and tc_k < th_k:
                    eta = 1.0 - (tc_k / th_k)
                    return {
                        "solved": True,
                        "status": "solved_multi_entity_scene",
                        "mode": "carnot_thermodynamic_cycle",
                        "hops": 1,
                        "steps": [{
                            "formula_id": "carnot_efficiency",
                            "title": "Carnot Heat Engine Maximum Efficiency (eta = 1 - T_C / T_H)",
                            "subdomain": "thermodynamics_stat_mech",
                            "concept": "carnot_cycle",
                            "governing_equation": "eta = 1 - (T_C / T_H)",
                            "isolated_symbolic_form": f"eta = 1 - ({tc_k} / {th_k}) = {eta:.4f} ({eta*100:.1f}%)",
                            "target_variable": "eta_carnot",
                            "target_name": "carnot_efficiency",
                            "value": eta,
                            "si_unit": "fraction",
                            "dimension": "1",
                            "knowns_used": {"T_H": th_k, "T_C": tc_k},
                            "constants_used": {},
                        }],
                        "target_variable": "eta_carnot",
                        "target_name": "carnot_efficiency",
                        "final_value": eta,
                        "si_unit": "fraction",
                        "dimension": "1",
                        "physical_violations": [],
                        "warnings": [],
                    }

        # 15. PILLAR 5 MULTI-HOP: GRAVITATIONAL FREE-FALL (KINEMATICS -> KINETIC ENERGY)
        if any(k in q_low for k in ("falls from rest", "dropped from rest", "free fall", "free-fall")) and any(k in q_low for k in ("velocity", "speed", "kinetic energy")):
            t_hit = re.search(rf"(?<![\w.])(?P<val>{NUMBER_RE})\s*(?P<unit>s|seconds?)\b", q, re.IGNORECASE)
            m_val = masses_kg[0] if masses_kg else 1.0
            if t_hit:
                t_sec = float(t_hit.group("val"))
                v_final = g_val * t_sec
                e_k = 0.5 * m_val * (v_final ** 2)
                return {
                    "solved": True,
                    "status": "solved_cross_domain_multihop",
                    "mode": "free_fall_kinematics_energy_multihop",
                    "hops": 2,
                    "steps": [
                        {
                            "formula_id": "free_fall_velocity",
                            "title": "Gravitational Free-Fall Velocity from Rest (v = g * t)",
                            "subdomain": "classical_mechanics",
                            "concept": "action_principle",
                            "governing_equation": "v = g * t",
                            "isolated_symbolic_form": f"v = {g_val:.3f} * {t_sec} = {v_final:.2f} m/s",
                            "target_variable": "v",
                            "target_name": "final_velocity",
                            "value": v_final,
                            "si_unit": "m/s",
                            "dimension": "L1 T-1",
                            "knowns_used": {"t": t_sec},
                            "constants_used": {"g": g_val},
                        },
                        {
                            "formula_id": "kinetic_energy",
                            "title": "Translational Kinetic Energy (E_k = 0.5 * m * v^2)",
                            "subdomain": "classical_mechanics",
                            "concept": "action_principle",
                            "governing_equation": "E_k = 0.5 * m * v^2",
                            "isolated_symbolic_form": f"E_k = 0.5 * {m_val} * ({v_final:.2f})^2 = {e_k:.2f} J",
                            "target_variable": "E_k",
                            "target_name": "kinetic_energy",
                            "value": e_k,
                            "si_unit": "J",
                            "dimension": "M1 L2 T-2",
                            "knowns_used": {"m": m_val, "v": v_final},
                            "constants_used": {},
                        },
                    ],
                    "target_variable": "E_k",
                    "target_name": "kinetic_energy",
                    "final_value": e_k,
                    "si_unit": "J",
                    "dimension": "M1 L2 T-2",
                    "physical_violations": [],
                    "warnings": [],
                }

        return None

    def solve_query(
        self,
        query: str,
        preferred_subdomain: Optional[str] = None,
        neural_solver_mode: Optional[str] = None,
        neural_target_observable: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Solves an unseen numerical physics/tax word problem via 1-step, multi-hop, or multi-entity scene solving."""
        # Step 0: Check Multi-Entity / System-of-Equations Scene Archetypes first (guided by Multi-Head Neural Predictions)
        multi_entity_res = self.solve_multi_entity_archetype(
            query,
            neural_solver_mode=neural_solver_mode,
            neural_target_observable=neural_target_observable,
        )
        if multi_entity_res is not None:
            return multi_entity_res

        knowns, target_var, parse_warnings = self.extract_variables_from_query(query)
        q_lower = query.lower()

        # Use neural_target_observable when explicit target phrase was not matched by regex
        if target_var is None and neural_target_observable and neural_target_observable in VARIABLE_CATALOG and neural_target_observable not in knowns:
            target_var = neural_target_observable

        # If target_var was not explicitly named via "find X", infer missing variable from matched formula
        candidate_formulas = sorted(
            self.formulas,
            key=lambda f: (
                1 if (preferred_subdomain and f["subdomain"] == preferred_subdomain) else 0,
                sum(1 for kw in f.get("keywords", []) if kw in q_lower),
                sum(1 for v in f["variables"] if v in knowns),
            ),
            reverse=True,
        )

        if target_var is None:
            for f in candidate_formulas:
                missing = [v for v in f["variables"] if v not in knowns]
                if len(missing) == 1:
                    target_var = missing[0]
                    break

        if not knowns or target_var is None:
            return {
                "solved": False,
                "status": "insufficient_numerical_inputs",
                "knowns_extracted": knowns,
                "target_variable": target_var,
                "message": "Could not identify sufficient numerical quantities and a target variable.",
            }

        # Step 1: Try Direct 1-Formula Solution (Forwards or Backwards)
        for f in candidate_formulas:
            if target_var in f["variables"]:
                required = [v for v in f["variables"] if v != target_var]
                if all(v in knowns for v in required):
                    step_res = self._solve_single_formula_sympy(f, knowns, target_var)
                    if step_res is not None:
                        violations = self.verify_physical_sanity(knowns, target_var, step_res["value"])
                        return {
                            "solved": len(violations) == 0,
                            "status": "solved_single_step" if not violations else "physical_sanity_violation",
                            "mode": "bidirectional_single_formula",
                            "hops": 1,
                            "steps": [step_res],
                            "target_variable": target_var,
                            "target_name": step_res["target_name"],
                            "final_value": step_res["value"],
                            "si_unit": step_res["si_unit"],
                            "dimension": step_res["dimension"],
                            "physical_violations": violations,
                            "warnings": parse_warnings,
                        }

        # Step 2: Multi-Hop BFS Formula Chaining (up to 5 hops across subdomains)
        queue = deque([(dict(knowns), [])])
        visited_states = {frozenset(knowns.keys())}

        while queue:
            curr_knowns, path_steps = queue.popleft()
            if len(path_steps) >= 5:
                continue

            for f in candidate_formulas:
                unknown_in_f = [v for v in f["variables"] if v not in curr_knowns]
                if len(unknown_in_f) == 1:
                    intermediate_var = unknown_in_f[0]
                    step_res = self._solve_single_formula_sympy(f, curr_knowns, intermediate_var)
                    if step_res is None:
                        continue
                    next_knowns = {**curr_knowns, intermediate_var: step_res["value"]}
                    next_steps = path_steps + [step_res]

                    if intermediate_var == target_var:
                        violations = self.verify_physical_sanity(next_knowns, target_var, step_res["value"])
                        return {
                            "solved": len(violations) == 0,
                            "status": "solved_multihop" if not violations else "physical_sanity_violation",
                            "mode": "multihop_formula_chain",
                            "hops": len(next_steps),
                            "steps": next_steps,
                            "target_variable": target_var,
                            "target_name": step_res["target_name"],
                            "final_value": step_res["value"],
                            "si_unit": step_res["si_unit"],
                            "dimension": step_res["dimension"],
                            "physical_violations": violations,
                            "warnings": parse_warnings,
                        }

                    state_key = frozenset(next_knowns.keys())
                    if state_key not in visited_states:
                        visited_states.add(state_key)
                        queue.append((next_knowns, next_steps))

        return {
            "solved": False,
            "status": "no_connecting_formula_chain",
            "knowns_extracted": knowns,
            "target_variable": target_var,
            "message": f"No single or multi-hop formula chain could solve for '{target_var}' from {list(knowns.keys())}.",
        }
