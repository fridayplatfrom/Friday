from typing import Dict, Any, Optional

class DiagramEngine:
    """
    Tier 5 Visual Scientific Computing: Dynamic SVG Diagram & Schematic Generator.
    Generates scalable, responsive, dark-mode SVG vector schematics for circuits,
    thermodynamic P-V state diagrams, and epidemiological disease triangles.
    """

    @classmethod
    def generate_circuit_svg(cls, config: str = "series", r_vals: Optional[list] = None, v_val: float = 12.0) -> str:
        """Generates an electrical circuit schematic in SVG."""
        resistors = r_vals or [10.0, 20.0]
        r1 = resistors[0]
        r2 = resistors[1] if len(resistors) > 1 else 20.0

        if config.lower() == "parallel":
            svg = f"""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 220" style="width:100%; max-width:460px; height:auto; background:#0f172a; border-radius:8px; border:1px solid #334155;">
              <style>
                .wire {{ stroke: #38bdf8; stroke-width: 2.5; fill: none; }}
                .resistor {{ stroke: #f59e0b; stroke-width: 2.5; fill: none; stroke-linejoin: round; }}
                .label {{ fill: #f8fafc; font-family: monospace; font-size: 13px; font-weight: bold; }}
                .sublabel {{ fill: #94a3b8; font-family: sans-serif; font-size: 11px; }}
                .battery {{ stroke: #22c55e; stroke-width: 3; }}
              </style>
              <!-- Circuit Loop Top -->
              <path class="wire" d="M 60 110 L 60 50 L 180 50" />
              <!-- Resistor 1 Parallel Branch -->
              <path class="wire" d="M 180 50 L 210 50" />
              <path class="resistor" d="M 210 50 L 215 40 L 225 60 L 235 40 L 245 60 L 255 40 L 265 60 L 270 50" />
              <path class="wire" d="M 270 50 L 380 50 L 380 110" />
              <text x="240" y="30" class="label" text-anchor="middle">R1: {r1} Ω</text>
              <!-- Resistor 2 Parallel Branch -->
              <path class="wire" d="M 180 50 L 180 160 L 210 160" />
              <path class="resistor" d="M 210 160 L 215 150 L 225 170 L 235 150 L 245 170 L 255 150 L 265 170 L 270 160" />
              <path class="wire" d="M 270 160 L 380 160 L 380 110" />
              <text x="240" y="195" class="label" text-anchor="middle">R2: {r2} Ω</text>
              <!-- Connecting Back to Battery -->
              <path class="wire" d="M 380 110 L 60 110" />
              <!-- DC Voltage Source -->
              <circle cx="60" cy="110" r="16" fill="#1e293b" stroke="#38bdf8" stroke-width="2" />
              <line x1="53" y1="110" x2="67" y2="110" stroke="#ef4444" stroke-width="2" />
              <line x1="60" y1="103" x2="60" y2="117" stroke="#ef4444" stroke-width="2" />
              <text x="25" y="115" class="label">V: {v_val}V</text>
              <text x="230" y="210" class="sublabel" text-anchor="middle">Parallel Network: 1/Req = 1/R1 + 1/R2</text>
            </svg>
            """.strip()
        else:
            svg = f"""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 190" style="width:100%; max-width:460px; height:auto; background:#0f172a; border-radius:8px; border:1px solid #334155;">
              <style>
                .wire {{ stroke: #38bdf8; stroke-width: 2.5; fill: none; }}
                .resistor {{ stroke: #f59e0b; stroke-width: 2.5; fill: none; stroke-linejoin: round; }}
                .label {{ fill: #f8fafc; font-family: monospace; font-size: 13px; font-weight: bold; }}
                .sublabel {{ fill: #94a3b8; font-family: sans-serif; font-size: 11px; }}
              </style>
              <path class="wire" d="M 60 130 L 60 60 L 120 60" />
              <!-- Resistor 1 -->
              <path class="resistor" d="M 120 60 L 125 48 L 135 72 L 145 48 L 155 72 L 165 48 L 175 72 L 180 60" />
              <text x="150" y="38" class="label" text-anchor="middle">R1: {r1} Ω</text>
              <path class="wire" d="M 180 60 L 260 60" />
              <!-- Resistor 2 -->
              <path class="resistor" d="M 260 60 L 265 48 L 275 72 L 285 48 L 295 72 L 305 48 L 315 72 L 320 60" />
              <text x="290" y="38" class="label" text-anchor="middle">R2: {r2} Ω</text>
              <path class="wire" d="M 320 60 L 400 60 L 400 130 L 60 130" />
              <!-- DC Source -->
              <circle cx="60" cy="130" r="16" fill="#1e293b" stroke="#38bdf8" stroke-width="2" />
              <text x="25" y="135" class="label">V: {v_val}V</text>
              <text x="230" y="165" class="sublabel" text-anchor="middle">Series Network: Req = R1 + R2 = {r1 + r2} Ω</text>
            </svg>
            """.strip()

        return svg

    @classmethod
    def generate_carnot_pv_svg(cls, th_k: float = 600.0, tc_k: float = 300.0) -> str:
        """Generates a Carnot Engine Indicator P-V Diagram in SVG."""
        eta = (1.0 - (tc_k / th_k)) * 100
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 260" style="width:100%; max-width:460px; height:auto; background:#0f172a; border-radius:8px; border:1px solid #334155;">
          <style>
            .axis {{ stroke: #94a3b8; stroke-width: 2; }}
            .isotherm-hot {{ stroke: #ef4444; stroke-width: 3; fill: none; }}
            .isotherm-cold {{ stroke: #38bdf8; stroke-width: 3; fill: none; }}
            .adiabat {{ stroke: #f59e0b; stroke-width: 3; stroke-dasharray: 4,4; fill: none; }}
            .label {{ fill: #f8fafc; font-family: monospace; font-size: 12px; }}
            .work-area {{ fill: rgba(245, 158, 11, 0.15); }}
          </style>
          <!-- Axes -->
          <line x1="50" y1="210" x2="420" y2="210" class="axis" />
          <line x1="50" y1="210" x2="50" y2="30" class="axis" />
          <text x="420" y="235" class="label" text-anchor="end">Volume (V) →</text>
          <text x="20" y="35" class="label">Pressure (P) ↑</text>
          <!-- Cycle Area -->
          <polygon points="120,60 230,100 340,180 190,140" class="work-area" />
          <!-- 1 -> 2: Isothermal Expansion at TH -->
          <path d="M 120 60 Q 170 85 230 100" class="isotherm-hot" />
          <text x="175" y="75" class="label" fill="#ef4444">1→2 (T_H = {th_k}K)</text>
          <!-- 2 -> 3: Reversible Adiabatic Expansion -->
          <path d="M 230 100 Q 285 140 340 180" class="adiabat" />
          <text x="310" y="135" class="label" fill="#f59e0b">2→3 (Q=0)</text>
          <!-- 3 -> 4: Isothermal Compression at TC -->
          <path d="M 340 180 Q 260 160 190 140" class="isotherm-cold" />
          <text x="265" y="195" class="label" fill="#38bdf8">3→4 (T_C = {tc_k}K)</text>
          <!-- 4 -> 1: Reversible Adiabatic Compression -->
          <path d="M 190 140 Q 150 100 120 60" class="adiabat" />
          <text x="110" y="125" class="label" fill="#f59e0b">4→1 (Q=0)</text>
          <!-- Center Work Label -->
          <text x="220" y="130" class="label" font-weight="bold" fill="#fef08a" text-anchor="middle">W_net = Q_H - Q_C</text>
          <text x="230" y="248" class="label" fill="#a7f3d0" text-anchor="middle">Carnot Efficiency: η = 1 - (T_C / T_H) = {eta:.1f}%</text>
        </svg>
        """.strip()
        return svg

    @classmethod
    def generate_disease_triangle_svg(cls, host: str, pathogen: str, env: str, risk: str = "High") -> str:
        """Generates an Epidemiological Disease Triangle Diagram in SVG."""
        risk_color = "#ef4444" if risk.lower() in ["high", "critical", "severe"] else "#f59e0b"
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 240" style="width:100%; max-width:460px; height:auto; background:#0f172a; border-radius:8px; border:1px solid #334155;">
          <style>
            .t-line {{ stroke: #38bdf8; stroke-width: 3; }}
            .vertex-box {{ fill: #1e293b; stroke: #64748b; stroke-width: 1.5; rx: 6; }}
            .v-title {{ fill: #f8fafc; font-family: sans-serif; font-size: 12px; font-weight: bold; }}
            .v-detail {{ fill: #cbd5e1; font-family: monospace; font-size: 11px; }}
            .risk-center {{ fill: {risk_color}; opacity: 0.2; }}
          </style>
          <!-- Triangle Lines -->
          <line x1="230" y1="40" x2="90" y2="180" class="t-line" />
          <line x1="230" y1="40" x2="370" y2="180" class="t-line" />
          <line x1="90" y1="180" x2="370" y2="180" class="t-line" />
          <!-- Center Risk Zone -->
          <polygon points="230,80 150,160 310,160" class="risk-center" />
          <text x="230" y="130" class="v-title" fill="#fca5a5" text-anchor="middle">DISEASE OUTCOME</text>
          <text x="230" y="148" class="v-detail" fill="{risk_color}" font-weight="bold" text-anchor="middle">Risk: {risk.upper()}</text>
          <!-- Vertex 1: Host (Top) -->
          <rect x="155" y="15" width="150" height="36" class="vertex-box" />
          <text x="230" y="30" class="v-title" text-anchor="middle">HOST PLANT</text>
          <text x="230" y="44" class="v-detail" text-anchor="middle">{host[:20]}</text>
          <!-- Vertex 2: Pathogen (Bottom-Left) -->
          <rect x="20" y="180" width="160" height="38" class="vertex-box" />
          <text x="100" y="196" class="v-title" text-anchor="middle">VIRULENT PATHOGEN</text>
          <text x="100" y="210" class="v-detail" text-anchor="middle">{pathogen[:20]}</text>
          <!-- Vertex 3: Environment (Bottom-Right) -->
          <rect x="280" y="180" width="165" height="38" class="vertex-box" />
          <text x="362" y="196" class="v-title" text-anchor="middle">CONDUCIVE ENVIRONMENT</text>
          <text x="362" y="210" class="v-detail" text-anchor="middle">{env[:22]}</text>
        </svg>
        """.strip()
        return svg

    @classmethod
    def generate_inclined_plane_svg(cls, mass_kg: float = 5.0, angle_deg: float = 30.0) -> str:
        """Generates a Mechanics Free-Body Inclined Plane Diagram in SVG."""
        import math
        g = 9.81
        rad = math.radians(angle_deg)
        f_par = mass_kg * g * math.sin(rad)
        f_norm = mass_kg * g * math.cos(rad)
        return f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 220" style="width:100%; max-width:460px; height:auto; background:#0f172a; border-radius:8px; border:1px solid #334155;">
          <polygon points="60,180 380,180 380,60" fill="#1e293b" stroke="#38bdf8" stroke-width="2.5" />
          <rect x="200" y="102" width="48" height="32" transform="rotate(-20.5 224 118)" fill="#f59e0b" stroke="#f8fafc" stroke-width="2" />
          <line x1="224" y1="118" x2="224" y2="172" stroke="#ef4444" stroke-width="2.5" />
          <text x="115" y="172" fill="#f8fafc" font-family="monospace" font-size="12">θ = {angle_deg:.1f}°</text>
          <text x="230" y="32" fill="#a7f3d0" font-family="monospace" font-size="12" text-anchor="middle">m={mass_kg}kg | F_parallel={f_par:.1f}N | N={f_norm:.1f}N</text>
        </svg>
        """.strip()

    @classmethod
    def generate_snell_refraction_svg(cls, n1: float = 1.0, n2: float = 1.5, theta1_deg: float = 45.0) -> str:
        """Generates an Optics Snell's Law Ray Refraction Diagram in SVG."""
        import math
        sin2 = max(-1.0, min(1.0, (n1 / n2) * math.sin(math.radians(theta1_deg))))
        theta2_deg = math.degrees(math.asin(sin2))
        return f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 220" style="width:100%; max-width:460px; height:auto; background:#0f172a; border-radius:8px; border:1px solid #334155;">
          <rect x="20" y="110" width="420" height="95" fill="rgba(56, 189, 248, 0.14)" />
          <line x1="20" y1="110" x2="440" y2="110" stroke="#94a3b8" stroke-width="2" />
          <line x1="230" y1="20" x2="230" y2="200" stroke="#64748b" stroke-width="1.5" stroke-dasharray="4,4" />
          <line x1="120" y1="30" x2="230" y2="110" stroke="#f59e0b" stroke-width="3" />
          <line x1="230" y1="110" x2="305" y2="195" stroke="#22c55e" stroke-width="3" />
          <text x="230" y="25" fill="#f8fafc" font-family="monospace" font-size="12" text-anchor="middle">n1={n1} (θ1={theta1_deg:.1f}°) → n2={n2} (θ2={theta2_deg:.1f}°)</text>
        </svg>
        """.strip()

    @classmethod
    def generate_quantum_energy_levels_svg(cls, n_initial: int = 3, n_final: int = 1) -> str:
        """Generates a Quantum Bohr/Eigenstate Energy Level Transition Diagram in SVG."""
        e_init = -13.6 / (max(1, n_initial) ** 2)
        e_fin = -13.6 / (max(1, n_final) ** 2)
        delta_ev = abs(e_init - e_fin)
        return f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 220" style="width:100%; max-width:460px; height:auto; background:#0f172a; border-radius:8px; border:1px solid #334155;">
          <line x1="80" y1="175" x2="380" y2="175" stroke="#38bdf8" stroke-width="3" />
          <line x1="80" y1="115" x2="380" y2="115" stroke="#38bdf8" stroke-width="2.5" />
          <line x1="80" y1="70" x2="380" y2="70" stroke="#38bdf8" stroke-width="2" />
          <line x1="230" y1="70" x2="230" y2="175" stroke="#f59e0b" stroke-width="3" />
          <text x="230" y="35" fill="#a7f3d0" font-family="monospace" font-size="12" text-anchor="middle">Transition n={n_initial} → n={n_final} | ΔE = hν = {delta_ev:.2f} eV</text>
        </svg>
        """.strip()
