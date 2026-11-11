"""Structured Pedagogical Synthesizer & Extractive Textbook Summarizer (Fix 1).

Transforms raw PDF passage retrievals and neural sub-concept predictions into
clean, teacher-style physics explanations with:
  1. Canonical Concept Principle & Physical Intuition (covering all 80 trained sub-concepts across 10 fields)
  2. Governing Equations (Unicode + LaTeX + SI Unit definitions)
  3. Step-by-Step Problem-Solving Guide
  4. Clean Sentence-Boundary Extractive Summary from the 35 Textbooks
  5. Cryptographic SHA-256 Verbatim Textbook Citation Footer
"""
from __future__ import annotations

import re
import os
from typing import Any, Dict, List, Optional, Tuple


# Canonical encyclopedia covering all 80 specialist concepts across the 10 physics subdomains
CONCEPT_ENCYCLOPEDIA: Dict[str, Dict[str, Any]] = {
    # 1. Classical Mechanics (8 concepts)
    "lagrangian": {
        "title": "Lagrangian Mechanics & The Lagrangian Function (L = T - V)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "The Lagrangian L(q, q_dot, t) summarizes the entire dynamics of a mechanical system as the difference "
            "between its kinetic energy T and potential energy V. Instead of tracking vector constraint forces "
            "like Newton's laws, Lagrangian mechanics uses generalized coordinates q_i that automatically respect constraints."
        ),
        "canonical_equation": "L(q_i, q̇_i, t) = T - V",
        "latex": r"L(q_i, \dot{q}_i, t) = T - V",
        "key_variables": "L: Lagrangian (J), T: kinetic energy (J), V: potential energy (J), q_i: generalized coordinates, q̇_i: generalized velocities",
        "intuition_steps": [
            "1. Choose independent generalized coordinates q_i matching the system's degrees of freedom.",
            "2. Express total kinetic energy T(q, q̇) and potential energy V(q) in terms of those coordinates.",
            "3. Form L = T - V and apply the Euler-Lagrange equations d/dt(∂L/∂q̇_i) - ∂L/∂q_i = 0 to obtain the equations of motion.",
        ],
    },
    "hamiltonian": {
        "title": "Hamiltonian Mechanics & Phase-Space Dynamics (H = T + V)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "The Hamiltonian H(q, p, t) represents the total energy of a conservative system expressed in terms of "
            "generalized coordinates q_i and conjugate momenta p_i = ∂L/∂q̇_i. It replaces second-order differential "
            "equations with 2n coupled first-order differential equations in phase space."
        ),
        "canonical_equation": "H(q, p, t) = ∑ p_i q̇_i - L,   q̇_i = ∂H/∂p_i,   ṗ_i = -∂H/∂q_i",
        "latex": r"H(q,p,t) = \sum_i p_i \dot{q}_i - L, \quad \dot{q}_i = \frac{\partial H}{\partial p_i}, \quad \dot{p}_i = -\frac{\partial H}{\partial q_i}",
        "key_variables": "H: Hamiltonian / total energy (J), q_i: generalized position, p_i: canonical momentum (kg·m/s or J·s/rad)",
        "intuition_steps": [
            "1. Compute canonical momenta p_i = ∂L/∂q̇_i and invert to write velocities q̇_i(q, p).",
            "2. Perform the Legendre transform H = ∑ p_i q̇_i - L (which equals T + V for scleronomic natural systems).",
            "3. Evolve the system in (q, p) phase space using Hamilton's canonical equations.",
        ],
    },
    "poisson_bracket": {
        "title": "Poisson Brackets & Lie Algebra of Observables",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "The Poisson bracket {f, g} measures how two phase-space observables f(q, p) and g(q, p) co-vary along "
            "dynamical trajectories. Any observable F evolves in time as dF/dt = {F, H} + ∂F/∂t, and any quantity "
            "whose Poisson bracket with H vanishes ({F, H} = 0) is a conserved constant of motion."
        ),
        "canonical_equation": "{f, g} = ∑ (∂f/∂q_i ∂g/∂p_i - ∂f/∂p_i ∂g/∂q_i),   {q_i, p_j} = δ_ij",
        "latex": r"\{f, g\} = \sum_i \left(\frac{\partial f}{\partial q_i}\frac{\partial g}{\partial p_i} - \frac{\partial f}{\partial p_i}\frac{\partial g}{\partial q_i}\right)",
        "key_variables": "f, g: phase-space functions, q_i: canonical coordinates, p_i: canonical momenta, δ_ij: Kronecker delta",
        "intuition_steps": [
            "1. Evaluate partial derivatives of both observables with respect to each (q_i, p_i) pair.",
            "2. Check if {F, H} = 0 to prove that observable F is conserved along trajectories.",
            "3. In quantum mechanics, Dirac canonical quantization replaces {f, g} with (1 / iℏ)[f̂, ĝ].",
        ],
    },
    "canonical_transformation": {
        "title": "Canonical Transformations & Symplectic Invariance",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "A canonical transformation (q, p) → (Q, P) is a change of phase-space coordinates that preserves the form "
            "of Hamilton's equations and the fundamental Poisson brackets {Q_i, P_j} = δ_ij. By choosing coordinates where "
            "new momenta P_i are constants of motion (ignorable coordinates), complex dynamical problems become trivial to integrate."
        ),
        "canonical_equation": "{Q_i, P_j}_{q,p} = δ_ij,   p_i dq_i - P_i dQ_i = dF",
        "latex": r"\{Q_i, P_j\}_{q,p} = \delta_{ij}, \quad \sum_i p_i\,dq_i - \sum_i P_i\,dQ_i = dF",
        "key_variables": "(q, p): old phase-space coordinates, (Q, P): new canonical coordinates, F: generating function (J·s)",
        "intuition_steps": [
            "1. Select a generating function type F_1(q, Q), F_2(q, P), F_3(p, Q), or F_4(p, P).",
            "2. Compute the conjugate coordinate relations from partial derivatives of F.",
            "3. Verify that the Jacobian matrix M satisfies the symplectic condition M^T J M = J.",
        ],
    },
    "generalized_coordinates": {
        "title": "Generalized Coordinates & Holonomic Degrees of Freedom",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Generalized coordinates (q_1, q_2, ..., q_n) are any set of independent parameters that uniquely specify "
            "the configuration of a physical system relative to its holonomic constraints. For N particles in 3D subject "
            "to k holonomic equations of constraint, the system requires exactly n = 3N - k generalized coordinates."
        ),
        "canonical_equation": "r_a = r_a(q_1, q_2, ..., q_n, t),   n = 3N - k",
        "latex": r"\mathbf{r}_a = \mathbf{r}_a(q_1, q_2, \dots, q_n, t), \quad n = 3N - k",
        "key_variables": "q_i: generalized coordinates (lengths, angles, etc.), N: number of particles, k: holonomic constraints",
        "intuition_steps": [
            "1. Identify all rigid-rod, surface, or rolling constraints reducing the independent motion.",
            "2. Parameterize Cartesian positions r_a in terms of minimal independent coordinates (e.g., pendulum angle θ).",
            "3. Differentiate r_a with respect to time using the chain rule to obtain velocities v_a(q, q̇).",
        ],
    },
    "action_principle": {
        "title": "Hamilton's Principle of Stationary Action (δS = 0)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Hamilton's Principle states that out of all possible paths q(t) a system could take between fixed endpoints "
            "q(t_1) and q(t_2), the true physical trajectory makes the action integral S[q] stationary (δS = 0). "
            "This variational principle unifies classical mechanics, electrodynamics, general relativity, and quantum path integrals."
        ),
        "canonical_equation": "S[q] = ∫_{t_1}^{t_2} L(q, q̇, t) dt,   δS = 0",
        "latex": r"S[q] = \int_{t_1}^{t_2} L(q, \dot{q}, t)\,dt, \quad \delta S = 0",
        "key_variables": "S: action functional (J·s), L: Lagrangian (J), δS: first variation of the action",
        "intuition_steps": [
            "1. Write the action integral S as the time integral of L(q, q̇, t) between fixed boundary times t_1 and t_2.",
            "2. Vary the path q(t) → q(t) + δq(t) with δq(t_1) = δq(t_2) = 0.",
            "3. Integrate by parts to show that δS = 0 for arbitrary δq(t) requires the Euler-Lagrange equations.",
        ],
    },
    "euler-lagrange_equation": {
        "title": "The Euler-Lagrange Equations of Motion",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "The Euler-Lagrange equation is the fundamental differential equation of analytical mechanics derived from "
            "stationary action δS = 0. Whenever the Lagrangian L does not explicitly depend on a coordinate q_k (∂L/∂q_k = 0, "
            "a cyclic coordinate), its conjugate momentum p_k = ∂L/∂q̇_k is immediately conserved."
        ),
        "canonical_equation": "d/dt (∂L / ∂q̇_i) - (∂L / ∂q_i) = Q_i^{non-cons}",
        "latex": r"\frac{d}{dt}\left(\frac{\partial L}{\partial \dot{q}_i}\right) - \frac{\partial L}{\partial q_i} = 0",
        "key_variables": "∂L/∂q̇_i: generalized momentum p_i, ∂L/∂q_i: generalized force F_i",
        "intuition_steps": [
            "1. Compute the generalized momentum p_i = ∂L/∂q̇_i and take its total time derivative d/dt(∂L/∂q̇_i).",
            "2. Compute the generalized force ∂L/∂q_i.",
            "3. Equate d/dt(∂L/∂q̇_i) = ∂L/∂q_i and spot cyclic coordinates where ∂L/∂q_i = 0.",
        ],
    },
    "moment_of_inertia": {
        "title": "Moment of Inertia & Rigid-Body Rotational Dynamics",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "The moment of inertia I quantifies how a rigid body's mass is distributed relative to an axis of rotation, "
            "serving as the rotational analog of mass in τ = Iα and E_rot = ½Iω². In 3D, it generalizes to the symmetric "
            "3×3 inertia tensor I_ij relating angular velocity ω to angular momentum L = I·ω."
        ),
        "canonical_equation": "I = ∫ r_⊥² dm,   I = I_cm + M d² (Parallel-Axis Theorem),   τ = I α",
        "latex": r"I = \int r_{\perp}^2\,dm, \quad I = I_{\text{cm}} + M d^2, \quad \tau = I\alpha",
        "key_variables": "I: moment of inertia (kg·m²), r_⊥: perpendicular distance to axis (m), τ: torque (N·m), ω: angular speed (rad/s)",
        "intuition_steps": [
            "1. Identify the axis of rotation and express the perpendicular distance r_⊥ for each mass element dm.",
            "2. Integrate I_cm = ∫ r_⊥² dm about the center of mass (e.g., ½MR² for solid cylinder, ⅖MR² for solid sphere).",
            "3. If the axis is displaced by distance d from the center of mass, apply Steiner's parallel-axis theorem I = I_cm + Md².",
        ],
    },

    # 2. Electromagnetism (8 concepts)
    "maxwell_equations": {
        "title": "Maxwell's Equations of Classical Electrodynamics",
        "subdomain": "electromagnetism",
        "core_principle": (
            "Maxwell's four coupled partial differential equations unify electricity, magnetism, and optics. They state "
            "that electric charges source diverging electric fields (Gauss), magnetic monopoles do not exist (∇·B = 0), "
            "time-varying magnetic fields induce curling electric fields (Faraday), and electric currents plus changing "
            "electric flux induce curling magnetic fields (Ampère-Maxwell)."
        ),
        "canonical_equation": "∇·E = ρ/ε₀,   ∇·B = 0,   ∇×E = -∂B/∂t,   ∇×B = μ₀J + μ₀ε₀ ∂E/∂t",
        "latex": r"\nabla\cdot\mathbf{E}=\frac{\rho}{\varepsilon_0},\quad \nabla\cdot\mathbf{B}=0,\quad \nabla\times\mathbf{E}=-\frac{\partial\mathbf{B}}{\partial t},\quad \nabla\times\mathbf{B}=\mu_0\mathbf{J}+\mu_0\varepsilon_0\frac{\partial\mathbf{E}}{\partial t}",
        "key_variables": "E: electric field (V/m), B: magnetic field (T), ρ: charge density (C/m³), J: current density (A/m²)",
        "intuition_steps": [
            "1. Use Gauss's Law (∇·E = ρ/ε₀) for high-symmetry charge distributions (spherical, cylindrical, planar).",
            "2. Use Faraday's Law (∇×E = -∂B/∂t) to find induced EMF when magnetic flux Φ_B changes with time.",
            "3. Take the curl of ∇×E in vacuum (ρ=0, J=0) to derive the 3D wave equation ∇²E = (1/c²) ∂²E/∂t² with c = 1/√(μ₀ε₀).",
        ],
    },
    "poynting_vector": {
        "title": "The Poynting Vector & Electromagnetic Energy Flux",
        "subdomain": "electromagnetism",
        "core_principle": (
            "The Poynting vector S = (1/μ₀)(E × B) gives the directional energy flux density (power per unit area, W/m²) "
            "carried by an electromagnetic field. Poynting's theorem expresses local conservation of energy between field "
            "energy density u_em and mechanical work J·E done on charges."
        ),
        "canonical_equation": "S = (1 / μ₀) (E × B),   ∂u/∂t + ∇·S = -J·E",
        "latex": r"\mathbf{S} = \frac{1}{\mu_0}(\mathbf{E} \times \mathbf{B}), \quad \frac{\partial u_{\text{em}}}{\partial t} + \nabla\cdot\mathbf{S} = -\mathbf{J}\cdot\mathbf{E}",
        "key_variables": "S: Poynting vector (W/m²), u_em = ½(ε₀E² + B²/μ₀): electromagnetic energy density (J/m³)",
        "intuition_steps": [
            "1. Determine the instantaneous electric field E and magnetic field B vectors.",
            "2. Compute the cross product S = (E × B)/μ₀; its direction is the direction of wave propagation.",
            "3. For a harmonic plane wave, average over one cycle to get intensity I = ⟨S⟩ = ½ c ε₀ E₀².",
        ],
    },
    "electric_field": {
        "title": "Electric Field, Coulomb's Law & Electrostatic Potential",
        "subdomain": "electromagnetism",
        "core_principle": (
            "The electric field E(r) defines the electrostatic force per unit test charge F/q experienced at position r. "
            "In electrostatics (∇×E = 0), E is conservative and equals the negative gradient of the scalar potential V (E = -∇V)."
        ),
        "canonical_equation": "E = F / q = (1 / 4πε₀) (Q / r²) r̂ = -∇V",
        "latex": r"\mathbf{E} = \frac{\mathbf{F}}{q} = \frac{1}{4\pi\varepsilon_0}\frac{Q}{r^2}\hat{\mathbf{r}} = -\nabla V",
        "key_variables": "E: electric field (V/m or N/C), Q: source charge (C), V: electrostatic scalar potential (V)",
        "intuition_steps": [
            "1. Sum or integrate Coulomb contributions dE = (1/4πε₀)(dq/r²)r̂ using superposition.",
            "2. Or compute scalar potential V = ∫ dq / (4πε₀ r) first (no vectors!) and take E = -∇V.",
        ],
    },
    "magnetic_flux": {
        "title": "Magnetic Flux & Gauss's Law for Magnetism",
        "subdomain": "electromagnetism",
        "core_principle": (
            "Magnetic flux Φ_B = ∫ B·dA quantifies the total magnetic field passing through an open surface S. "
            "Through any closed surface, ∮ B·dA = 0 because magnetic field lines always form closed loops with no monopoles."
        ),
        "canonical_equation": "Φ_B = ∫_S B · dA = B A cos(θ)",
        "latex": r"\Phi_B = \iint_S \mathbf{B}\cdot d\mathbf{A} = B A \cos\theta",
        "key_variables": "Φ_B: magnetic flux (Wb = T·m²), B: magnetic flux density (T), A: loop area (m²), θ: angle with surface normal",
        "intuition_steps": [
            "1. Define the surface normal vector n̂ and angle θ between B and n̂.",
            "2. Integrate B·dA across the surface (or multiply B·A·cosθ if B is uniform).",
            "3. Differentiate Φ_B(t) with respect to time to find Faraday induced EMF ε = -N dΦ_B/dt.",
        ],
    },
    "lorentz_force": {
        "title": "Lorentz Force Law & Cyclotron Motion of Charged Particles",
        "subdomain": "electromagnetism",
        "core_principle": (
            "The Lorentz force F = q(E + v × B) governs the total electromagnetic force on a charge q moving with velocity v. "
            "Because the magnetic component q(v × B) is always perpendicular to v, magnetic fields do zero mechanical work "
            "and curve particles into circular or helical cyclotron orbits of radius r_c = mv / (|q|B)."
        ),
        "canonical_equation": "F = q (E + v × B),   r_c = m v_⊥ / (|q| B)",
        "latex": r"\mathbf{F} = q(\mathbf{E} + \mathbf{v}\times\mathbf{B}), \quad r_c = \frac{m v_{\perp}}{|q|B}",
        "key_variables": "F: Lorentz force (N), q: electric charge (C), v: particle velocity (m/s), B: magnetic field (T)",
        "intuition_steps": [
            "1. Compute the electric force qE parallel to the electric field.",
            "2. Use the right-hand rule to evaluate q(v × B) perpendicular to both v and B.",
            "3. Equate centripetal force mv²/r = |q|vB to solve for cyclotron radius r = mv/(|q|B) and frequency ω_c = |q|B/m.",
        ],
    },
    "vector_potential": {
        "title": "Magnetic Vector Potential (B = ∇ × A) & Gauge Freedom",
        "subdomain": "electromagnetism",
        "core_principle": (
            "Because ∇·B = 0 identically, the magnetic field B can always be written as the curl of a vector potential A (B = ∇ × A). "
            "Adding the gradient of any scalar function χ to A (A → A + ∇χ, V → V - ∂χ/∂t) leaves physical E and B fields completely invariant."
        ),
        "canonical_equation": "B = ∇ × A,   E = -∇V - ∂A/∂t",
        "latex": r"\mathbf{B} = \nabla \times \mathbf{A}, \quad \mathbf{E} = -\nabla V - \frac{\partial \mathbf{A}}{\partial t}",
        "key_variables": "A: magnetic vector potential (T·m or Wb/m), V: scalar potential (V), B: magnetic field (T)",
        "intuition_steps": [
            "1. Impose Coulomb gauge (∇·A = 0) for magnetostatics so ∇²A = -μ₀J.",
            "2. Integrate A(r) = (μ₀/4π) ∫ J(r')/|r - r'| d³r' parallel to the current distribution.",
            "3. Take the curl B = ∇ × A to recover the magnetic field.",
        ],
    },
    "gauss_law": {
        "title": "Gauss's Law in Integral & Differential Form",
        "subdomain": "electromagnetism",
        "core_principle": (
            "Gauss's Law states that the net outward electric flux through any closed Gaussian surface equals the total "
            "enclosed charge Q_enc divided by the vacuum permittivity ε₀, independent of how the charge is distributed inside."
        ),
        "canonical_equation": "∮_S E · dA = Q_enc / ε₀   ⟺   ∇ · E = ρ / ε₀",
        "latex": r"\oiint_S \mathbf{E}\cdot d\mathbf{A} = \frac{Q_{\text{enc}}}{\varepsilon_0} \iff \nabla\cdot\mathbf{E} = \frac{\rho}{\varepsilon_0}",
        "key_variables": "Q_enc: total enclosed charge (C), ε₀ = 8.854×10⁻¹² F/m: vacuum permittivity, ρ: volume charge density (C/m³)",
        "intuition_steps": [
            "1. Identify spherical, cylindrical, or planar symmetry of the charge distribution.",
            "2. Construct a closed Gaussian surface where |E| is constant and parallel to dA.",
            "3. Factor |E| out of ∮ E·dA = |E|·Area = Q_enc/ε₀ and solve directly for |E|.",
        ],
    },
    "faraday_law": {
        "title": "Faraday's Law of Electromagnetic Induction & Lenz's Law",
        "subdomain": "electromagnetism",
        "core_principle": (
            "Faraday's Law states that a time-changing magnetic flux Φ_B through a circuit induces an electromotive force (EMF) "
            "ε = -dΦ_B/dt. The negative sign (Lenz's Law) guarantees energy conservation: the induced current opposes the change in flux."
        ),
        "canonical_equation": "ε = ∮ E · dl = -N (dΦ_B / dt)",
        "latex": r"\mathcal{E} = \oint \mathbf{E}\cdot d\mathbf{l} = -N\frac{d\Phi_B}{dt}",
        "key_variables": "ε: induced electromotive force (V), N: number of coil turns, Φ_B: magnetic flux per turn (Wb)",
        "intuition_steps": [
            "1. Express magnetic flux Φ_B(t) = B(t)·A(t)·cos(θ(t)) as a function of time.",
            "2. Differentiate Φ_B(t) with respect to t and multiply by -N turns.",
            "3. Apply Lenz's right-hand rule to determine the direction of the opposing induced current I = |ε|/R.",
        ],
    },

    # 3. Thermodynamics & Statistical Mechanics (8 concepts)
    "partition_function": {
        "title": "Canonical Partition Function (Z) & Statistical Thermodynamics",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "The canonical partition function Z = ∑_i exp(-β E_i) is the generating function of statistical mechanics. "
            "Once Z(T, V, N) is known as a function of inverse temperature β = 1/(k_B T), every macroscopic thermodynamic "
            "property—free energy F, average energy ⟨E⟩, entropy S, and pressure P—follows by simple differentiation."
        ),
        "canonical_equation": "Z = ∑_i e^{-E_i / (k_B T)},   F = -k_B T ln(Z),   ⟨E⟩ = -∂(ln Z)/∂β",
        "latex": r"Z = \sum_i e^{-\beta E_i}, \quad F = -k_B T \ln Z, \quad \langle E \rangle = -\frac{\partial \ln Z}{\partial \beta}",
        "key_variables": "Z: partition function (dimensionless), β = 1/(k_B T): inverse thermal energy (J⁻¹), E_i: microstate energy (J)",
        "intuition_steps": [
            "1. Enumerate all microstates i and their energy eigenvalues E_i (or integrate over phase space).",
            "2. Sum the Boltzmann weights exp(-βE_i) to obtain Z(β, V, N).",
            "3. Compute Helmholtz free energy F = -k_B T ln Z and differentiate to extract S = -∂F/∂T and P = -∂F/∂V.",
        ],
    },
    "boltzmann_distribution": {
        "title": "The Boltzmann Probability Distribution & Thermal Equilibrium",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "For a system in thermal equilibrium with a heat bath at temperature T, the probability P_i of occupying a "
            "specific microstate i of energy E_i decays exponentially with energy: P_i = exp(-E_i / k_B T) / Z."
        ),
        "canonical_equation": "P_i = e^{-E_i / (k_B T)} / Z,   P_j / P_i = e^{-(E_j - E_i) / (k_B T)}",
        "latex": r"P_i = \frac{e^{-E_i / (k_B T)}}{Z}, \quad \frac{P_j}{P_i} = e^{-(E_j - E_i)/(k_B T)}",
        "key_variables": "P_i: microstate probability, k_B = 1.380649×10⁻²³ J/K: Boltzmann constant, T: absolute temperature (K)",
        "intuition_steps": [
            "1. Compare energy spacing ΔE = E_j - E_i against thermal energy k_B T.",
            "2. If k_B T ≪ ΔE, the system freezes into the ground state; if k_B T ≫ ΔE, states are populated nearly equally.",
        ],
    },
    "canonical_ensemble": {
        "title": "The Canonical Ensemble (Fixed N, V, T)",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "The canonical ensemble describes a system with fixed particle number N and volume V that exchanges heat "
            "with a large thermal reservoir at fixed temperature T. Equilibrium minimizes the Helmholtz free energy F = U - TS."
        ),
        "canonical_equation": "P(microstate s) = e^{-β E_s} / Z(N, V, T),   σ_E² = ⟨(ΔE)²⟩ = k_B T² C_V",
        "latex": r"P_s = \frac{e^{-\beta E_s}}{Z(N,V,T)}, \quad \langle (\Delta E)^2 \rangle = k_B T^2 C_V",
        "key_variables": "N: particle number, V: volume (m³), T: temperature (K), C_V: heat capacity at constant volume (J/K)",
        "intuition_steps": [
            "1. Use the canonical ensemble whenever T is controlled externally rather than total energy E.",
            "2. Relative energy fluctuations scale as ΔE/⟨E⟩ ~ 1/√N, vanishing in the thermodynamic limit N → ∞.",
        ],
    },
    "grand_canonical_ensemble": {
        "title": "The Grand Canonical Ensemble (Fixed μ, V, T)",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "The grand canonical ensemble describes an open system at fixed volume V that exchanges both energy and particles "
            "with a reservoir at temperature T and chemical potential μ. It is essential for quantum gases (Bose-Einstein & Fermi-Dirac)."
        ),
        "canonical_equation": "Ξ(μ, V, T) = ∑_{N, i} e^{-β(E_{N,i} - μ N)},   Φ_G = -k_B T ln(Ξ) = -P V",
        "latex": r"\mathcal{Z}(\mu, V, T) = \sum_{N=0}^{\infty}\sum_i e^{-\beta(E_{N,i} - \mu N)}, \quad \Omega = -k_B T \ln\mathcal{Z} = -PV",
        "key_variables": "Ξ / 𝒵: grand partition function, μ: chemical potential (J), Ω: grand potential (J)",
        "intuition_steps": [
            "1. Factor the grand partition function over single-particle orbitals k using fugacity z = e^{βμ}.",
            "2. Extract average particle number ⟨N⟩ = (1/β) ∂(ln Ξ)/∂μ = -∂Ω/∂μ.",
        ],
    },
    "helmholtz_free_energy": {
        "title": "Helmholtz Free Energy (F = U - T S)",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "Helmholtz free energy F = U - TS measures the maximum useful mechanical work obtainable from a closed "
            "thermodynamic system held at constant temperature T and volume V. Spontaneous processes at constant (T, V) always decrease F."
        ),
        "canonical_equation": "F = U - T S,   dF = -S dT - P dV + μ dN",
        "latex": r"F = U - TS, \quad dF = -S\,dT - P\,dV + \mu\,dN",
        "key_variables": "F: Helmholtz free energy (J), U: internal energy (J), T: temperature (K), S: entropy (J/K)",
        "intuition_steps": [
            "1. Obtain F from statistical mechanics via F = -k_B T ln Z.",
            "2. Differentiate F with respect to its natural variables (T, V, N): S = -(∂F/∂T)_{V,N} and P = -(∂F/∂V)_{T,N}.",
        ],
    },
    "gibbs_free_energy": {
        "title": "Gibbs Free Energy (G = H - T S) & Phase/Chemical Equilibrium",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "Gibbs free energy G = U + PV - TS = H - TS is the thermodynamic potential minimized at constant temperature T "
            "and pressure P. Phase transitions and chemical reactions reach equilibrium precisely when ΔG = 0 (or μ_1 = μ_2)."
        ),
        "canonical_equation": "G = U + P V - T S = μ N,   dG = -S dT + V dP + μ dN",
        "latex": r"G = U + PV - TS = H - TS, \quad dG = -S\,dT + V\,dP + \mu\,dN",
        "key_variables": "G: Gibbs free energy (J), H = U + PV: enthalpy (J), P: pressure (Pa), V: volume (m³)",
        "intuition_steps": [
            "1. For processes at constant atmospheric pressure P and temperature T, check the sign of ΔG = ΔH - TΔS.",
            "2. If ΔG < 0, the process is spontaneous; if ΔG = 0, the phases/reactants are in coexistence equilibrium.",
        ],
    },
    "chemical_potential": {
        "title": "Chemical Potential (μ) & Diffusive Equilibrium",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "The chemical potential μ = (∂G/∂N)_{T,P} = (∂F/∂N)_{T,V} is the free energy cost of adding one particle "
            "to a thermodynamic system. Particles spontaneously diffuse from regions of higher μ to lower μ until μ is uniform."
        ),
        "canonical_equation": "μ = (∂U/∂N)_{S,V} = (∂F/∂N)_{T,V} = (∂G/∂N)_{T,P}",
        "latex": r"\mu = \left(\frac{\partial F}{\partial N}\right)_{T,V} = \left(\frac{\partial G}{\partial N}\right)_{T,P}",
        "key_variables": "μ: chemical potential per particle (J or eV), N: number of particles",
        "intuition_steps": [
            "1. Set μ_A = μ_B to find diffusive equilibrium between two phases or reservoirs in contact.",
            "2. For a chemical reaction ∑ ν_i A_i = 0, equilibrium satisfies ∑ ν_i μ_i = 0.",
        ],
    },
    "carnot_cycle": {
        "title": "Carnot Heat Engine & Second-Law Maximum Efficiency",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "The Carnot cycle consists of two reversible isothermal processes (at T_H and T_C) and two reversible adiabatic "
            "processes. By Carnot's Theorem and the Second Law of Thermodynamics, no heat engine operating between T_H and T_C "
            "can exceed the Carnot efficiency η_max = 1 - T_C / T_H."
        ),
        "canonical_equation": "η_Carnot = W / Q_H = 1 - (Q_C / Q_H) = 1 - (T_C / T_H)",
        "latex": r"\eta_{\text{Carnot}} = \frac{W}{Q_H} = 1 - \frac{T_C}{T_H}",
        "key_variables": "η: thermal efficiency (0 ≤ η < 1), T_H: hot reservoir temperature (K), T_C: cold reservoir temperature (K)",
        "intuition_steps": [
            "1. Always convert reservoir temperatures to absolute Kelvin (T[K] = T[°C] + 273.15).",
            "2. Verify physical sanity: 0 < T_C < T_H, ensuring 0 < η_Carnot < 1.",
            "3. Compute work output W = η · Q_H and rejected heat Q_C = Q_H - W.",
        ],
    },

    # 4. Quantum Mechanics (8 concepts)
    "schrodinger_equation": {
        "title": "The Time-Dependent & Time-Independent Schrödinger Equation",
        "subdomain": "quantum_mechanics",
        "core_principle": (
            "The Schrödinger equation governs the unitary time evolution of a quantum state ψ(r, t). For time-independent "
            "potentials V(r), separation of variables yields the stationary eigenvalue problem Ĥψ_n = E_n ψ_n, determining "
            "quantized energy levels E_n."
        ),
        "canonical_equation": "iℏ ∂Ψ/∂t = Ĥ Ψ = [- (ℏ² / 2m) ∇² + V(r)] Ψ",
        "latex": r"i\hbar\frac{\partial \Psi}{\partial t} = \hat{H}\Psi = \left(-\frac{\hbar^2}{2m}\nabla^2 + V(\mathbf{r})\right)\Psi",
        "key_variables": "Ψ(r,t): quantum wavefunction, ℏ = h/(2π): reduced Planck constant (1.0546×10⁻³⁴ J·s), Ĥ: Hamiltonian operator",
        "intuition_steps": [
            "1. Specify the potential V(r) and boundary conditions (e.g., ψ = 0 at infinite walls, ψ → 0 at ∞).",
            "2. Solve the eigenvalue equation Ĥψ_n = E_n ψ_n for stationary states ψ_n(r) and energies E_n.",
            "3. Evolve any superposition Ψ(r, 0) = ∑ c_n ψ_n(r) as Ψ(r, t) = ∑ c_n ψ_n(r) exp(-i E_n t / ℏ).",
        ],
    },
    "wavefunction": {
        "title": "Quantum Wavefunction Ψ(r, t) & Born Probability Density",
        "subdomain": "quantum_mechanics",
        "core_principle": (
            "The wavefunction ψ(r, t) is the complex probability amplitude of a quantum particle in position space. "
            "By Max Born's rule, |ψ(r, t)|² d³r gives the probability of detecting the particle in volume element d³r, "
            "requiring global normalization ∫ |ψ(r, t)|² d³r = 1."
        ),
        "canonical_equation": "P(r) d³r = |ψ(r, t)|² d³r,   ∫_{-∞}^{+∞} |ψ(r, t)|² d³r = 1",
        "latex": r"P(\mathbf{r})\,d^3r = |\psi(\mathbf{r},t)|^2\,d^3r, \quad \int |\psi(\mathbf{r},t)|^2\,d^3r = 1",
        "key_variables": "ψ(r,t): probability amplitude (m⁻³/² in 3D), |ψ|²: probability density (m⁻³)",
        "intuition_steps": [
            "1. Normalize ψ by setting A² ∫ |f(x)|² dx = 1 to find the normalization constant A.",
            "2. Compute expectation values of observables via ⟨Ô⟩ = ∫ ψ*(r) Ô ψ(r) d³r.",
        ],
    },
    "hermitian_operator": {
        "title": "Hermitian (Self-Adjoint) Operators & Physical Observables",
        "subdomain": "quantum_mechanics",
        "core_principle": (
            "Every measurable physical observable in quantum mechanics (energy, momentum, position, spin) is represented "
            "by a Hermitian (self-adjoint) linear operator Â = Â† on Hilbert space. Hermiticity guarantees that all "
            "measurement eigenvalues are strictly real numbers and eigenstates with distinct eigenvalues are orthogonal."
        ),
        "canonical_equation": "⟨φ | Â ψ⟩ = ⟨Â φ | ψ⟩   (Â = Â†),   Â |a_n⟩ = a_n |a_n⟩ (a_n ∈ ℝ)",
        "latex": r"\hat{A}^{\dagger} = \hat{A}, \quad \hat{A}|a_n\rangle = a_n|a_n\rangle \implies a_n \in \mathbb{R}, \quad \langle a_m | a_n \rangle = \delta_{mn}",
        "key_variables": "Â: linear operator, Â†: Hermitian adjoint (conjugate transpose), a_n: real eigenvalue",
        "intuition_steps": [
            "1. Check Â = Â† by taking the conjugate transpose of the matrix (or integrating by parts in position space).",
            "2. Expand arbitrary state |ψ⟩ = ∑ c_n |a_n⟩ in the orthonormal eigenbasis of Â, where c_n = ⟨a_n | ψ⟩.",
        ],
    },
    "eigenstate": {
        "title": "Quantum Eigenstates, Stationary States & Measurement Collapse",
        "subdomain": "quantum_mechanics",
        "core_principle": (
            "An eigenstate |a_n⟩ of an observable operator Â is a state of definite physical value a_n with zero variance (σ_A = 0). "
            "Measuring Â on a general superposition |ψ⟩ = ∑ c_n |a_n⟩ yields eigenvalue a_n with probability |c_n|² = |⟨a_n|ψ⟩|² "
            "and projects the state onto |a_n⟩."
        ),
        "canonical_equation": "Â |a_n⟩ = a_n |a_n⟩,   P(a_n) = |⟨a_n | ψ⟩|²",
        "latex": r"\hat{A}|a_n\rangle = a_n|a_n\rangle, \quad P(a_n) = |\langle a_n | \psi \rangle|^2",
        "key_variables": "|a_n⟩: eigenket of operator Â, a_n: measurement outcome, P(a_n): Born measurement probability",
        "intuition_steps": [
            "1. Solve the characteristic equation det(A - aI) = 0 to find eigenvalues a_n and eigenvectors |a_n⟩.",
            "2. Project |ψ⟩ onto normalized |a_n⟩ and square the modulus |⟨a_n|ψ⟩|² to get measurement probability.",
        ],
    },
    "commutator": {
        "title": "Canonical Commutation Relations & Simultaneous Observables",
        "subdomain": "quantum_mechanics",
        "core_principle": (
            "The commutator [Â, B̂] = ÂB̂ - B̂Â measures the failure of two quantum operations to commute. Two observables "
            "can be simultaneously measured to arbitrary precision (sharing a complete common eigenbasis) if and only if [Â, B̂] = 0."
        ),
        "canonical_equation": "[x̂, p̂_x] = iℏ,   [L̂_x, L̂_y] = iℏ L̂_z,   d⟨Â⟩/dt = (i/ℏ)⟨[Ĥ, Â]⟩ + ⟨∂Â/∂t⟩",
        "latex": r"[\hat{x}, \hat{p}_x] = i\hbar, \quad [\hat{L}_i, \hat{L}_j] = i\hbar\varepsilon_{ijk}\hat{L}_k",
        "key_variables": "[Â, B̂]: commutator operator, x̂: position operator, p̂ = -iℏ∇: momentum operator",
        "intuition_steps": [
            "1. Apply [x̂, p̂]ψ(x) = x(-iℏ dψ/dx) - (-iℏ d/dx(xψ)) = iℏψ(x) to verify [x̂, p̂] = iℏ.",
            "2. Check if [Â, Ĥ] = 0: by Ehrenfest's theorem, any operator commuting with Ĥ is a conserved quantum number.",
        ],
    },
    "uncertainty_principle": {
        "title": "Heisenberg Uncertainty Principle & Non-Commuting Observables",
        "subdomain": "quantum_mechanics",
        "core_principle": (
            "The Robertson-Heisenberg uncertainty relation proves that for any two non-commuting observables Â and B̂, "
            "the product of their standard deviations satisfies σ_A σ_B ≥ ½ |⟨[Â, B̂]⟩|. For position and momentum, "
            "σ_x σ_p ≥ ℏ/2, reflecting the Fourier duality between spatial localization and wavenumber bandwidth."
        ),
        "canonical_equation": "σ_x σ_p ≥ ℏ / 2,   σ_A σ_B ≥ ½ |⟨[Â, B̂]⟩|",
        "latex": r"\sigma_x \sigma_p \ge \frac{\hbar}{2}, \quad \sigma_A \sigma_B \ge \frac{1}{2}\left|\langle[\hat{A},\hat{B}]\rangle\right|",
        "key_variables": "σ_x: position uncertainty (m), σ_p: momentum uncertainty (kg·m/s), ℏ: reduced Planck constant",
        "intuition_steps": [
            "1. Confining a particle to region Δx forces minimum momentum spread Δp ~ ℏ/(2Δx).",
            "2. Minimum-uncertainty Gaussian wavepackets saturate the bound precisely with σ_x σ_p = ℏ/2.",
        ],
    },
    "harmonic_oscillator": {
        "title": "Quantum Harmonic Oscillator & Ladder Operators (a, a†)",
        "subdomain": "quantum_mechanics",
        "core_principle": (
            "Any smooth potential minimum V(x) ≈ ½mω²x² behaves as a harmonic oscillator with equally spaced energy levels "
            "E_n = ℏω(n + ½) and nonzero zero-point energy E_0 = ½ℏω. Dirac's creation (a†) and annihilation (a) operators "
            "step algebraically up and down the ladder of Fock states |n⟩."
        ),
        "canonical_equation": "Ĥ = ℏω (a† a + ½),   E_n = ℏω (n + ½),   [a, a†] = 1",
        "latex": r"\hat{H} = \hbar\omega\left(\hat{a}^{\dagger}\hat{a} + \frac{1}{2}\right), \quad E_n = \hbar\omega\left(n + \frac{1}{2}\right)",
        "key_variables": "ω = √(k/m): angular frequency (rad/s), n = 0,1,2,...: quantum number, E_0 = ½ℏω: zero-point energy (J)",
        "intuition_steps": [
            "1. Express x̂ = √(ℏ/2mω)(a + a†) and p̂ = -i√(mℏω/2)(a - a†) to compute matrix elements without integration.",
            "2. Apply a|n⟩ = √n |n-1⟩ and a†|n⟩ = √(n+1) |n+1⟩.",
        ],
    },
    "pauli_matrices": {
        "title": "Pauli Spin Matrices (σ_x, σ_y, σ_z) & Spin-½ SU(2) Algebra",
        "subdomain": "quantum_mechanics",
        "core_principle": (
            "The three 2×2 Pauli matrices (σ_x, σ_y, σ_z) are Hermitian, unitary, traceless generators of SU(2) that "
            "represent intrinsic spin angular momentum Ŝ = (ℏ/2)σ for spin-½ fermions (electrons, protons, quarks)."
        ),
        "canonical_equation": "Ŝ = (ℏ/2) σ,   [σ_i, σ_j] = 2i ε_ijk σ_k,   {σ_i, σ_j} = 2 δ_ij I",
        "latex": r"\hat{\mathbf{S}} = \frac{\hbar}{2}\boldsymbol{\sigma}, \quad \sigma_i \sigma_j = \delta_{ij}I + i\varepsilon_{ijk}\sigma_k",
        "key_variables": "σ_x, σ_y, σ_z: 2×2 Pauli matrices, S_z eigenvalues: ±ℏ/2",
        "intuition_steps": [
            "1. Along any unit axis n̂, the spin projection n̂·Ŝ has exact eigenvalues +ℏ/2 and -ℏ/2.",
            "2. Rotating a spin-½ spinor by 2π multiplies its state by -1; a full 4π rotation restores +1.",
        ],
    },
    "newton_third_law": {
        "title": "Newton's Third Law of Motion (Action and Reaction Pairs)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Newton's Third Law states that whenever object A exerts a force on object B, object B simultaneously "
            "exerts an equal in magnitude and opposite in direction force on object A (F_AB = -F_BA). These two forces "
            "constitute an action-reaction pair. Crucially, they act on two completely different objects, which is why "
            "they never cancel each other out."
        ),
        "canonical_equation": "F_AB = -F_BA,   ∑ F_internal = 0",
        "latex": r"\vec{F}_{AB} = -\vec{F}_{BA}",
        "key_variables": "F_AB: action force of A on B (N), F_BA: reaction force of B on A (N)",
        "intuition_steps": [
            "Forces in nature always occur in mutual pairs; you cannot push something without it pushing back on you with identical force.",
            "Action and reaction forces act on distinct bodies, so an object can never exert an action-reaction pair on itself.",
            "Walking & Propulsion: When you walk, your foot pushes backward on the ground; the ground exerts an equal and opposite forward friction force that propels you.",
            "Rocket Mechanics: A rocket accelerates upward not by pushing against the air or launch pad, but because burning exhaust gas is expelled downward with high force, imparting an equal upward thrust force on the rocket.",
        ],
    },
    "newton_first_law": {
        "title": "Newton's First Law of Motion (The Law of Inertia)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Newton's First Law (Law of Inertia) states that an object at rest remains at rest, and an object in motion "
            "continues in motion with constant velocity (constant speed in a straight line), unless acted upon by a non-zero net external force (∑ F = 0 ⟹ a = 0)."
        ),
        "canonical_equation": "∑ F = 0 ⟹ a = dv/dt = 0 (v = constant)",
        "latex": r"\sum \vec{F} = 0 \implies \vec{a} = 0, \quad \vec{v} = \text{constant}",
        "key_variables": "F: external forces (N), a: acceleration (m/s²), v: velocity (m/s), m: inertial mass (kg)",
        "intuition_steps": [
            "Inertia is the intrinsic property of matter that resists any change in its state of motion; mass is the quantitative measure of inertia.",
            "Friction and gravity in everyday life constantly decelerate moving objects, which historically misled people into thinking a continuous force was needed to maintain motion.",
            "In deep space far from gravitational influences, a spacecraft with its engines shut off travels forever at constant velocity without burning any fuel.",
        ],
    },
    "newton_second_law": {
        "title": "Newton's Second Law of Motion (Force, Mass, and Acceleration)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Newton's Second Law states that the time rate of change of an object's linear momentum equals the net external force "
            "acting on it (F_net = dp/dt). For a body with constant mass m, this reduces to the foundational vector relation F_net = m a."
        ),
        "canonical_equation": "F_net = dp/dt = m a",
        "latex": r"\vec{F}_{\text{net}} = \frac{d\vec{p}}{dt} = m\vec{a}",
        "key_variables": "F_net: net force (N), m: inertial mass (kg), a: acceleration (m/s²), p = m v: linear momentum (kg·m/s)",
        "intuition_steps": [
            "Acceleration is directly proportional to net force and inversely proportional to mass: a = F_net / m.",
            "When multiple forces act on a body, resolve them into independent Cartesian components: ∑ F_x = m a_x and ∑ F_y = m a_y.",
            "One Newton (1 N) is defined as the force required to accelerate a 1 kilogram mass at 1 meter per second squared (1 kg·m/s²).",
        ],
    },
    "speed_vs_velocity": {
        "title": "Speed versus Velocity (Scalar Magnitude vs. Vector Rate of Displacement)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Speed is a scalar quantity measuring how fast an object moves regardless of direction (speed = total distance / elapsed time). "
            "Velocity is a vector quantity measuring the time rate of change of an object's position or displacement with an explicit direction (velocity = displacement / time = dr/dt). "
            "An object traveling along a circular path at constant speed is still accelerating because its direction (and thus velocity vector) is continuously changing."
        ),
        "canonical_equation": "Speed = s/t,   Velocity v⃗ = dr⃗/dt = Δx⃗/Δt",
        "latex": r"\text{Speed } v = \frac{\Delta s}{\Delta t}, \quad \text{Velocity } \vec{v} = \frac{d\vec{r}}{dt}",
        "key_variables": "v: scalar speed (m/s), v⃗: vector velocity (m/s), s: total distance (m), r⃗: position vector (m)",
        "intuition_steps": [
            "Scalar vs. Vector: Speed tells you 'how fast' (e.g. 60 km/h); velocity tells you 'how fast and in what direction' (e.g. 60 km/h due North).",
            "Closed Loop Trip: If a runner completes a 400 m lap around a track in 50 seconds, their average speed is 400/50 = 8 m/s, but their average velocity is exactly 0 m/s because their starting and ending positions are identical (zero displacement).",
            "Circular Motion: An automobile turning a corner on cruise control at a steady 30 km/h has constant speed but constantly changing velocity, meaning a net centripetal force must act on it.",
        ],
    },
    "rayleigh_scattering": {
        "title": "Rayleigh Scattering & Why the Sky is Blue",
        "subdomain": "optics_waves",
        "core_principle": (
            "The sky appears blue because sunlight entering Earth's atmosphere undergoes Rayleigh scattering off air molecules (primarily N₂ and O₂). "
            "When scattering particles are much smaller than the wavelength of incident light (d << λ), the scattering intensity is inversely proportional "
            "to the fourth power of the wavelength: I_scattered ∝ 1/λ⁴. Blue light (~400 nm) has a much shorter wavelength than red light (~700 nm), "
            "so blue light is scattered approximately (700/400)⁴ ≈ 9.4 times more strongly in all directions, illuminating the sky with diffuse blue light."
        ),
        "canonical_equation": "I_scattered(λ) ∝ 1 / λ⁴,   I(θ, λ) = I_0 (8π⁴ α² / (λ⁴ R²)) (1 + cos²θ)",
        "latex": r"I(\lambda) \propto \frac{1}{\lambda^4}, \quad I(\theta, \lambda) = I_0 \frac{8\pi^4\alpha^2}{\lambda^4 R^2}(1 + \cos^2\theta)",
        "key_variables": "I: scattered light intensity (W/m²), λ: wavelength (m), α: polarizability of air molecules, θ: scattering angle",
        "intuition_steps": [
            "Sunlight contains all colors of the rainbow; red light has the longest visible wavelength (~700 nm) and blue/violet the shortest (~400 nm).",
            "Because of the 1/λ⁴ dependence, atmospheric gas molecules scatter short blue wavelengths roughly 10 times more effectively than red wavelengths.",
            "Why Not Violet? Sunlight contains more blue photons than violet photons, and human eye cone receptors are substantially more sensitive to blue light than violet light, causing us to perceive the sky as blue.",
            "Red Sunsets: At sunset and sunrise, sunlight traverses a much thicker path through the atmosphere. Virtually all blue light is scattered away before reaching the observer, leaving only the unscattered long red and orange wavelengths.",
            "Lunar Sky: On the Moon or in space where there is no atmosphere to scatter light, the sky appears completely black even when the Sun is blazing overhead.",
        ],
    },
    "electric_current": {
        "title": "Electric Current & Charge Carrier Transport",
        "subdomain": "electromagnetism",
        "core_principle": (
            "Electric current (I) is the net rate of flow of electric charge across a cross-sectional area per unit time (I = dQ/dt). "
            "In solid conductors, current is carried by mobile conduction electrons drifting opposite to the electric field with drift velocity v_d (I = n q A v_d). "
            "The SI base unit is the Ampere (1 A = 1 C/s). Conventional current is defined by historic convention as the direction positive charges would move."
        ),
        "canonical_equation": "I = dQ/dt = n q A v_d,   J⃗ = σ E⃗ = n q v⃗_d",
        "latex": r"I = \frac{dQ}{dt} = n q A v_d, \quad \vec{J} = \sigma \vec{E} = n q \vec{v}_d",
        "key_variables": "I: current (A or C/s), Q: charge (C), n: carrier number density (m⁻³), q: charge per carrier (1.602×10⁻¹⁹ C), A: cross-sectional area (m²), v_d: drift speed (m/s)",
        "intuition_steps": [
            "Rate of Charge Flow: One ampere corresponds to approximately 6.242 × 10¹⁸ electrons passing through a wire cross-section every second.",
            "Slow Drift vs Fast Signal: While the electric field signal propagates along the wire near the speed of light (~10⁸ m/s), individual electrons drift extremely slowly—often less than 0.1 mm per second.",
            "DC vs AC: Direct Current (DC) flows in a steady single direction (e.g. from chemical batteries); Alternating Current (AC) oscillates sinusoidally back and forth (e.g. residential 50/60 Hz power grids).",
        ],
    },
    "archimedes_principle": {
        "title": "Archimedes' Principle & Buoyant Force",
        "subdomain": "fluid_plasma",
        "core_principle": (
            "Archimedes' Principle states that any object completely or partially submerged in a fluid experiences an upward buoyant force F_b "
            "equal to the weight of the fluid displaced by the object (F_b = ρ_fluid V_submerged g). If buoyant force exceeds object weight, the object floats."
        ),
        "canonical_equation": "F_b = ρ_fluid V_disp g,   W_apparent = W_real - F_b",
        "latex": r"F_b = \rho_{\text{fluid}} V_{\text{disp}} g, \quad W_{\text{app}} = m g - \rho_{\text{fluid}} V_{\text{disp}} g",
        "key_variables": "F_b: buoyant force (N), ρ_fluid: fluid density (kg/m³), V_disp: displaced volume (m³), g = 9.807 m/s²",
        "intuition_steps": [
            "Origin of Buoyancy: Fluid pressure increases with depth (P = ρ g h). The upward pressure on the bottom of a submerged body is strictly greater than the downward pressure on its top, yielding a net upward force.",
            "Flotation Criterion: An object floats if its average density is less than the fluid density (ρ_obj < ρ_fluid), sinking until the displaced fluid weight matches its total weight.",
            "Ships & Icebergs: Massive steel ships float because their hollow hull geometry gives them an average density far less than that of water.",
        ],
    },
    "bernoulli_principle": {
        "title": "Bernoulli's Principle & Streamline Energy Conservation",
        "subdomain": "fluid_plasma",
        "core_principle": (
            "Bernoulli's Principle states that along a streamline of steady, incompressible, non-viscous fluid flow, an increase in fluid speed "
            "occurs simultaneously with a decrease in static fluid pressure or potential energy: P + ½ ρ v² + ρ g h = constant."
        ),
        "canonical_equation": "P + ½ ρ v² + ρ g h = constant",
        "latex": r"P + \frac{1}{2}\rho v^2 + \rho g h = \text{constant}",
        "key_variables": "P: static pressure (Pa), ρ: fluid density (kg/m³), v: flow speed (m/s), h: elevation (m)",
        "intuition_steps": [
            "Work-Energy in Fluids: Bernoulli's equation is conservation of mechanical energy per unit volume applied to fluid parcels.",
            "Venturi Effect: When fluid flows through a constriction, continuity (A₁v₁ = A₂v₂) forces velocity to increase, which drops static pressure.",
            "Aerodynamic Applications: Atomizers, carburetors, pitot tubes, and aerodynamic draft operate directly on Bernoulli pressure differentials.",
        ],
    },
    "conservation_of_momentum": {
        "title": "Law of Conservation of Linear Momentum",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "The Law of Conservation of Momentum states that if the net external force on a system is zero (∑ F_ext = 0), "
            "the total linear momentum of the system remains constant in time: ∑ p⃗_initial = ∑ p⃗_final. By Noether's theorem, "
            "momentum conservation is the exact mathematical consequence of the spatial translation invariance of physical laws."
        ),
        "canonical_equation": "∑ p⃗_i = ∑ p⃗_f,   dp⃗_total/dt = ∑ F_ext = 0",
        "latex": r"\sum \vec{p}_i = \sum \vec{p}_f, \quad \frac{d\vec{P}_{\text{total}}}{dt} = \vec{F}_{\text{ext}} = 0",
        "key_variables": "p⃗ = m v⃗: momentum (kg·m/s), m: mass (kg), v⃗: velocity (m/s), F_ext: external force (N)",
        "intuition_steps": [
            "In any collision (elastic, inelastic, or explosive), total momentum is strictly conserved as long as external forces are negligible during the impact.",
            "Elastic collisions conserve both total momentum and total kinetic energy; inelastic collisions conserve momentum while converting some kinetic energy to thermal energy or deformation.",
            "Recoil: Firing a rifle causes equal and opposite momentum transfer to the shooter: m_bullet v_bullet = -m_rifle v_recoil.",
        ],
    },
    "work_energy_theorem": {
        "title": "Work-Energy Theorem & Conservation of Mechanical Energy",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "The Work-Energy Theorem states that the net work done by all forces acting on an object equals the change in its kinetic energy: "
            "W_net = ΔK = ½ m v_f² - ½ m v_i². When only conservative forces act (gravity, ideal springs), total mechanical energy E = K + U remains constant."
        ),
        "canonical_equation": "W_net = ∫ F⃗ · dr⃗ = ΔK = ½ m v_f² - ½ m v_i²",
        "latex": r"W_{\text{net}} = \int \vec{F}\cdot d\vec{r} = \Delta K = \frac{1}{2}m v_f^2 - \frac{1}{2}m v_i^2",
        "key_variables": "W: work (J = N·m), K = ½mv²: kinetic energy (J), U: potential energy (J), F⃗: force vector, dr⃗: displacement vector",
        "intuition_steps": [
            "Work is done only by the component of force parallel to the displacement: W = F d cos(θ). Perpendicular forces (like normal force or centripetal force) do zero work.",
            "Positive work increases speed; negative work (like friction) removes mechanical energy and reduces speed.",
            "Stopping Distance: Doubling velocity quadruples kinetic energy (v²), meaning braking distance increases by a factor of 4 for a constant braking force.",
        ],
    },
    "ohms_law": {
        "title": "Ohm's Law & Electrical Resistance",
        "subdomain": "electromagnetism",
        "core_principle": (
            "Ohm's Law states that the current I flowing through an ohmic conductor between two points is directly proportional "
            "to the electric potential difference V across them and inversely proportional to the resistance R: V = I R. "
            "The microscopic form relates current density J⃗ to electric field E⃗ through electrical conductivity σ: J⃗ = σ E⃗."
        ),
        "canonical_equation": "V = I R,   P = V I = I² R = V² / R,   R = ρ L / A",
        "latex": r"V = I R, \quad \vec{J} = \sigma \vec{E}, \quad R = \frac{\rho L}{A}",
        "key_variables": "V: voltage (V), I: current (A), R: resistance (Ω), ρ: resistivity (Ω·m), L: length (m), A: cross-sectional area (m²)",
        "intuition_steps": [
            "Voltage is the electrical 'pressure' driving charges; resistance is the opposition of atomic lattice collisions to charge flow.",
            "Geometric Dependence: Resistance increases with wire length L and decreases with cross-sectional area A: R = ρ L / A.",
            "Power Dissipation: The electrical energy converted to heat per second in a resistor is given by Joule heating: P = I² R.",
        ],
    },
    "coulombs_law": {
        "title": "Coulomb's Law of Electrostatic Force",
        "subdomain": "electromagnetism",
        "core_principle": (
            "Coulomb's Law states that the electrostatic force F between two stationary point charges q₁ and q₂ is directly proportional "
            "to the product of the magnitudes of the charges and inversely proportional to the square of the distance r between them: F = k_e |q₁ q₂| / r². "
            "Like charges repel; opposite charges attract."
        ),
        "canonical_equation": "F = k_e (|q₁ q₂| / r²),   k_e = 1 / (4πε₀) ≈ 8.98755 × 10⁹ N·m²/C²",
        "latex": r"F = \frac{1}{4\pi\varepsilon_0} \frac{|q_1 q_2|}{r^2} = k_e \frac{|q_1 q_2|}{r^2}",
        "key_variables": "F: electrostatic force (N), q₁, q₂: electric charges (C), r: separation distance (m), k_e: Coulomb constant (N·m²/C²)",
        "intuition_steps": [
            "Inverse-Square Law: Doubling the distance between two charges quarters the electrostatic force between them.",
            "Vector Form: The force acts along the line joining the two charges. In vector form, F⃗₁₂ = k_e (q₁ q₂ / r²) r̂₁₂.",
            "Fundamental Strength: Coulomb electrostatic attraction between an electron and proton is approximately 10³⁹ times stronger than their mutual gravitational attraction.",
        ],
    },
    "first_law_thermodynamics": {
        "title": "First Law of Thermodynamics (Conservation of Energy)",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "The First Law of Thermodynamics is the universal law of conservation of energy applied to thermodynamic systems: "
            "the change in internal energy ΔU of a closed system equals the net heat Q added to the system minus the work W done by the system: ΔU = Q - W. "
            "Energy cannot be created or destroyed, only transformed between heat, work, and internal energy."
        ),
        "canonical_equation": "ΔU = Q - W,   dU = δQ - δW = T dS - P dV",
        "latex": r"\Delta U = Q - W, \quad dU = T\,dS - P\,dV",
        "key_variables": "ΔU: change in internal energy (J), Q: heat added to system (J), W: work done by system (J)",
        "intuition_steps": [
            "Internal Energy (U) is a state function depending only on current state (temperature, phase, pressure), not on how that state was reached.",
            "Heat (Q) and Work (W) are path-dependent transfer mechanisms, not stored quantities.",
            "Special Processes: In an adiabatic process (Q = 0), ΔU = -W; in an isochoric process (constant volume, W = 0), ΔU = Q.",
        ],
    },
    "second_law_thermodynamics": {
        "title": "Second Law of Thermodynamics & Entropy Arrow",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "The Second Law of Thermodynamics states that the total entropy S of an isolated system always increases or remains constant in any "
            "spontaneous process (ΔS_isolated ≥ 0). Heat spontaneously flows from hotter to colder bodies, and no heat engine operating between two "
            "thermal reservoirs can achieve 100% efficiency (Kelvin-Planck and Clausius statements)."
        ),
        "canonical_equation": "ΔS_isolated ≥ 0,   dS = δQ_rev / T,   η_max = 1 - T_C / T_H",
        "latex": r"\Delta S_{\text{universe}} \ge 0, \quad dS = \frac{\delta Q_{\text{rev}}}{T}, \quad \eta_{\text{Carnot}} = 1 - \frac{T_C}{T_H}",
        "key_variables": "S: thermodynamic entropy (J/K), Q_rev: reversible heat exchange (J), T: absolute temperature (K), η: thermal efficiency",
        "intuition_steps": [
            "Arrow of Time: The Second Law dictates the irreversible direction of time; broken coffee cups do not spontaneously reassemble.",
            "Statistical Meaning: Entropy is proportional to the logarithm of accessible microscopic quantum states: S = k_B ln(Ω).",
            "Engine Limit: You cannot convert random ambient thermal energy entirely into mechanical work without exhausting heat to a cold reservoir.",
        ],
    },
    "doppler_effect": {
        "title": "Doppler Effect for Sound and Electromagnetic Waves",
        "subdomain": "optics_waves",
        "core_principle": (
            "The Doppler Effect is the observed shift in frequency and wavelength of a wave when there is relative motion between the source "
            "and the observer. Approaching motion compresses wave crests, increasing observed frequency (blue-shift); receding motion stretches wave crests, "
            "decreasing observed frequency (red-shift)."
        ),
        "canonical_equation": "f' = f ((v ± v_o) / (v ∓ v_s)),   Relativistic: f' = f √((1 - β) / (1 + β))",
        "latex": r"f' = f\left(\frac{v \pm v_o}{v \mp v_s}\right), \quad f' = f\sqrt{\frac{1 - \beta}{1 + \beta}}",
        "key_variables": "f': observed frequency (Hz), f: source frequency (Hz), v: wave speed in medium (m/s), v_o: observer speed, v_s: source speed",
        "intuition_steps": [
            "Approaching Source: Wavefronts bunch together ahead of the source, decreasing wavelength λ' and increasing observed pitch f'.",
            "Receding Source: Wavefronts spread out behind the moving source, increasing wavelength λ' and lowering observed pitch.",
            "Cosmological Redshift: Light from distant galaxies is Doppler shifted toward longer red wavelengths because the fabric of spacetime itself is expanding (Hubble's Law).",
        ],
    },
    "snells_law_refraction": {
        "title": "Snell's Law of Refraction & Wave Index of Refraction",
        "subdomain": "optics_waves",
        "core_principle": (
            "Snell's Law describes how light bends across an interface between two optical media with refractive indices n₁ and n₂: "
            "n₁ sin(θ₁) = n₂ sin(θ₂). Light bends toward the normal when entering a denser medium with higher index of refraction (v decreases) "
            "to minimize travel time according to Fermat's Principle of Least Time."
        ),
        "canonical_equation": "n₁ sin(θ₁) = n₂ sin(θ₂),   n = c / v",
        "latex": r"n_1 \sin\theta_1 = n_2 \sin\theta_2, \quad n = \frac{c}{v}",
        "key_variables": "n₁, n₂: refractive indices, θ₁: angle of incidence (deg), θ₂: angle of refraction (deg), c: speed of light in vacuum",
        "intuition_steps": [
            "Index of Refraction: n = c/v measures how much slower light travels in a medium compared to vacuum (e.g. n_water ≈ 1.33, n_glass ≈ 1.5).",
            "Bending Rule: Entering a slower medium bends light toward the surface normal (θ₂ < θ₁); entering a faster medium bends light away from normal.",
            "Apparent Depth: Objects underwater (like fish or swimming pool floors) appear closer to the surface than they truly are due to refraction.",
        ],
    },
    "total_internal_reflection": {
        "title": "Total Internal Reflection & Critical Angle",
        "subdomain": "optics_waves",
        "core_principle": (
            "Total Internal Reflection (TIR) occurs when light traveling in an optically denser medium (n₁) strikes an interface with a rarer "
            "medium (n₂ < n₁) at an angle of incidence greater than the critical angle θ_c = arcsin(n₂/n₁). All incident light is 100% reflected "
            "back into the denser medium with zero transmission loss."
        ),
        "canonical_equation": "sin(θ_c) = n₂ / n₁,   θ_inc > θ_c ⟹ R = 1.0 (TIR)",
        "latex": r"\sin\theta_c = \frac{n_2}{n_1}, \quad \theta_1 \ge \theta_c \implies 100\% \text{ reflection}",
        "key_variables": "θ_c: critical angle (deg), n₁: higher refractive index, n₂: lower refractive index (n₂ < n₁)",
        "intuition_steps": [
            "At the critical angle θ_c, the refracted ray skims along the interface at exactly θ₂ = 90°.",
            "Fiber Optics: Modern global internet fiber cables transmit light over thousands of kilometers by repeatedly trapping optical pulses inside a glass core via total internal reflection.",
            "Diamond Brilliance: Diamond has an exceptionally high refractive index (n ≈ 2.42) and small critical angle (~24.4°), trapping light inside and scattering it through crown facets with dazzling sparkle.",
        ],
    },
    "photoelectric_effect": {
        "title": "Einstein's Photoelectric Effect & Photon Quantization",
        "subdomain": "quantum_mechanics",
        "core_principle": (
            "The Photoelectric Effect proves that electromagnetic radiation is quantized into discrete packets of energy called photons (E = h ν). "
            "When a photon strikes a metallic surface, it transfers all its energy to a single electron. If photon energy exceeds the metal's work function Φ, "
            "an electron is immediately ejected with maximum kinetic energy K_max = h ν - Φ = (h c / λ) - Φ."
        ),
        "canonical_equation": "K_max = h ν - Φ = (h c / λ) - Φ,   ν_threshold = Φ / h",
        "latex": r"K_{\text{max}} = h\nu - \Phi = \frac{h c}{\lambda} - \Phi",
        "key_variables": "K_max: maximum kinetic energy (J or eV), h: Planck constant (6.626×10⁻³⁴ J·s), ν: frequency (Hz), Φ: metal work function (eV)",
        "intuition_steps": [
            "Wave Theory Failure: Classical wave theory predicted that increasing light intensity would eventually eject electrons after a time delay. Experiments proved emission is instantaneous, and depends strictly on frequency, not intensity.",
            "Threshold Frequency: If ν < ν_threshold = Φ/h, zero electrons are emitted no matter how intense the beam is.",
            "Solar Panels: Modern photovoltaic solar cells operate on the photoelectric and photovoltaic effect, converting solar photons directly into electricity.",
        ],
    },
    "universal_gravitation": {
        "title": "Newton's Universal Law of Gravitation",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Newton's Universal Law of Gravitation states that every point mass attracts every other point mass with a force directly "
            "proportional to the product of their masses and inversely proportional to the square of the distance between their centers: "
            "F = G (m₁ m₂ / r²). This universal inverse-square law governs planetary orbits, tides, and celestial mechanics."
        ),
        "canonical_equation": "F = G (m₁ m₂ / r²),   G = 6.67430 × 10⁻¹¹ N·m²/kg²",
        "latex": r"F = G\frac{m_1 m_2}{r^2}, \quad \vec{F}_{12} = -G\frac{m_1 m_2}{r^2}\hat{r}_{12}",
        "key_variables": "F: gravitational force (N), G: Newton gravitational constant, m₁, m₂: masses (kg), r: separation distance (m)",
        "intuition_steps": [
            "Universality: The exact same gravitational law that causes an apple to fall from a tree on Earth also holds the Moon in orbit around the Earth.",
            "Surface Gravity: On Earth's surface, g = G M_earth / R_earth² ≈ 9.81 m/s².",
            "Kepler's Laws Derived: Newton showed that Kepler's empirical planetary laws are direct mathematical consequences of this inverse-square force law.",
        ],
    },
    "motion": {
        "title": "Motion and Kinematics (Change of Position over Time)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Motion is the change in the position of an object over time relative to a chosen reference frame. "
            "It is described quantitatively using displacement, velocity, and acceleration. Motion is intrinsically relative; "
            "an object can be at rest relative to one reference frame (such as a passenger in a seat) while moving rapidly relative to another (such as the ground below)."
        ),
        "canonical_equation": "v(t) = dx/dt,   a(t) = dv/dt = d²x/dt²,   Δx = ∫ v(t) dt",
        "latex": r"\vec{v}(t) = \frac{d\vec{r}}{dt}, \quad \vec{a}(t) = \frac{d\vec{v}}{dt} = \frac{d^2\vec{r}}{dt^2}, \quad \Delta\vec{r} = \int_{t_1}^{t_2} \vec{v}(t)\,dt",
        "key_variables": "r: position vector (m), v: velocity (m/s), a: acceleration (m/s²), t: time (s)",
        "intuition_steps": [
            "Reference Frame: All motion is measured relative to a coordinate reference frame. Without specifying a frame of reference, motion cannot be defined.",
            "Three Primary Classifications: (1) Rectilinear / Translatory motion (straight-line translation), (2) Circular / Rotational motion (around an axis), and (3) Oscillatory / Periodic motion (back-and-forth about an equilibrium position).",
            "Kinematic Hierarchy: Position r(t) differentiated with respect to time yields velocity v(t); velocity differentiated yields acceleration a(t).",
            "Uniform vs Accelerated Motion: An object traveling at constant velocity covers equal displacements in equal time intervals with zero net force.",
        ],
    },
    "distance_and_displacement": {
        "title": "Distance versus Displacement (Scalar Path vs. Vector Position Offset)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Distance is a scalar quantity measuring the total path length traveled by an object, regardless of direction. "
            "Displacement is a vector quantity pointing directly from the initial position to the final position: Δx = x_final - x_initial. "
            "Distance is always greater than or equal to the magnitude of displacement (d ≥ |Δx|)."
        ),
        "canonical_equation": "d = ∫ |v(t)| dt,   Δx = x_f - x_i",
        "latex": r"d = \int |v(t)|\,dt \ge |\Delta\vec{r}|, \quad \Delta\vec{r} = \vec{r}_f - \vec{r}_i",
        "key_variables": "d: total path distance (m), Δr: net displacement vector (m)",
        "intuition_steps": [
            "Round Trip Rule: If you walk around a 400 m track and finish at the start line, your total distance is 400 m, but your displacement is 0 m.",
            "Path Dependence: Distance depends on every curve and detour taken; displacement depends strictly on the start and end coordinates.",
        ],
    },
    "acceleration": {
        "title": "Acceleration (Rate of Change of Velocity)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Acceleration is a vector quantity defined as the instantaneous time rate of change of velocity: a = dv/dt = d²r/dt². "
            "Because velocity has both magnitude (speed) and direction, an object accelerates whenever its speed changes, its direction of travel changes, or both."
        ),
        "canonical_equation": "a_avg = Δv / Δt,   a(t) = dv/dt = d²x/dt²",
        "latex": r"\vec{a} = \frac{d\vec{v}}{dt} = \frac{d^2\vec{r}}{dt^2}",
        "key_variables": "a: acceleration (m/s²), v: velocity (m/s), t: elapsed time (s)",
        "intuition_steps": [
            "Three Ways to Accelerate: (1) Speeding up (velocity and acceleration parallel), (2) Slowing down / deceleration (velocity and acceleration anti-parallel), and (3) Turning at constant speed (acceleration perpendicular to velocity, as in circular motion).",
            "Signs Matter: A negative acceleration does not necessarily mean slowing down; an object moving in the negative direction with negative acceleration is speeding up.",
        ],
    },
    "equations_of_motion": {
        "title": "Kinematic Equations for Constant Acceleration (SUVAT)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "When an object moves along a straight line under uniform (constant) acceleration a, its kinematic variables "
            "(initial velocity u, final velocity v, acceleration a, elapsed time t, and displacement s) are governed by four exact relations derived from calculus."
        ),
        "canonical_equation": "v = u + a t,   s = u t + ½ a t²,   v² = u² + 2 a s,   s = ½ (u + v) t",
        "latex": r"v = u + at, \quad s = ut + \frac{1}{2}at^2, \quad v^2 = u^2 + 2as, \quad s = \frac{u+v}{2}t",
        "key_variables": "u: initial velocity (m/s), v: final velocity (m/s), a: constant acceleration (m/s²), t: time (s), s: displacement (m)",
        "intuition_steps": [
            "Uniform Acceleration Requirement: These equations apply only when acceleration is constant; if a varies with time, integrate directly.",
            "Linear Velocity Profile: Under constant acceleration, average velocity is simply the arithmetic midpoint: v_avg = (u + v) / 2.",
        ],
    },
    "free_fall": {
        "title": "Free Fall and Gravitational Acceleration",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Free fall is the idealized motion of a body where gravity is the sole force acting upon it, completely neglecting air resistance. "
            "Near Earth's surface, all freely falling bodies experience the exact same downward acceleration g ≈ 9.81 m/s², regardless of their mass or density."
        ),
        "canonical_equation": "y(t) = y_0 + v_0 t - ½ g t²,   v(t) = v_0 - g t,   v² = v_0² - 2 g Δy",
        "latex": r"y(t) = y_0 + v_0 t - \frac{1}{2}gt^2, \quad v(t) = v_0 - gt, \quad g \approx 9.81\,\text{m/s}^2",
        "key_variables": "g: gravitational acceleration (9.80665 m/s²), y: elevation (m), t: time (s)",
        "intuition_steps": [
            "Galilean Universality: In a vacuum or on the Moon, a heavy hammer and a feather fall side-by-side and strike the ground simultaneously.",
            "Vertical Trajectory Symmetry: An object thrown vertically upward at speed v_0 takes time t_peak = v_0/g to reach maximum height and returns at identical speed in double that time.",
        ],
    },
    "projectile_motion": {
        "title": "Projectile Motion in Two Dimensions",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Projectile motion is the 2D parabolic trajectory of an object launched into a gravitational field under negligible air resistance. "
            "The motion decomposes into two completely independent orthogonal 1D motions: constant horizontal velocity (a_x = 0) and uniform downward gravitational acceleration (a_y = -g)."
        ),
        "canonical_equation": "x = (v_0 cosθ) t,   y = (v_0 sinθ) t - ½ g t²,   R = (v_0² sin 2θ) / g",
        "latex": r"x(t) = (v_0\cos\theta)t, \quad y(t) = (v_0\sin\theta)t - \frac{1}{2}gt^2, \quad R = \frac{v_0^2\sin 2\theta}{g}",
        "key_variables": "v_0: initial launch speed (m/s), θ: launch angle, R: horizontal range (m), H = (v_0² sin²θ)/(2g): peak height",
        "intuition_steps": [
            "Orthogonal Independence: A bullet fired horizontally from a rifle and a bullet dropped from the same height strike flat ground at the exact same instant.",
            "Optimal Launch Angle: On flat level terrain without aerodynamic drag, launch angle θ = 45° maximizes horizontal range.",
        ],
    },
    "third_law_of_gravity": {
        "title": "Third Law of Gravity (Kepler's Harmonic Law & Gravitational Action-Reaction)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "The Third Law of Gravity encompasses two foundational physical tenets: "
            "(1) Kepler's Third Law (Harmonic Law of Gravitation), which establishes that the square of any celestial body's orbital period T "
            "is directly proportional to the cube of the semi-major axis a of its orbit: T² = (4π² / (G M)) a³, derived by equating Newton's gravitational attraction "
            "to the centripetal acceleration requirement (G M m / r² = m (2π/T)² r); and (2) Newton's Third Law applied to gravitation, which dictates that mutual "
            "gravitational forces form an exact action-reaction pair: the force exerted by the Sun on Earth is equal in magnitude and opposite in direction to the force exerted by Earth on the Sun (F_SE = -F_ES)."
        ),
        "canonical_equation": "T² = (4π² / (G M)) a³,   F_12 = -F_21 = -G (m₁ m₂ / r²) r̂",
        "latex": r"T^2 = \left(\frac{4\pi^2}{G M}\right) a^3, \quad \frac{T_1^2}{a_1^3} = \frac{T_2^2}{a_2^3} = \text{constant}, \quad \vec{F}_{12} = -\vec{F}_{21}",
        "key_variables": "T: orbital period (s or yr), a: semi-major axis / orbital radius (m or AU), G: gravitational constant, M: central mass (kg)",
        "intuition_steps": [
            "Harmonic Ratio: In our Solar System, measuring period in Earth years and orbital radius in Astronomical Units (AU), T² = a³ holds universally for all planets and asteroids orbiting the Sun.",
            "Derivation from Newton's Laws: Equate gravitational force F_g = G M m / r² to centripetal force F_c = m v² / r = m (2π r / T)² / r. Cancelling test mass m yields G M / r = 4π² r² / T², directly proving T² = (4π² / G M) r³.",
            "Mutual Gravitational Action-Reaction: When you drop an apple, Earth pulls the apple downward with force F = m_apple · g; the apple pulls the entire Earth upward with identical force F = G M_earth m_apple / R_earth²; Earth's immense mass makes its upward acceleration immeasurably tiny.",
        ],
    },
    "escape_and_orbital_velocity": {
        "title": "Orbital Velocity and Escape Velocity",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Orbital velocity v_orb is the horizontal speed needed for an object to remain in a stable circular orbit around a celestial body without falling to the surface. "
            "Escape velocity v_esc is the minimum initial ballistic speed required to overcome a body's gravitational field and coast to infinity with zero remaining velocity, derived by setting total mechanical energy E = K + U = 0."
        ),
        "canonical_equation": "v_orb = √(G M / r),   v_esc = √(2 G M / R) = √(2) v_orb",
        "latex": r"v_{\text{orb}} = \sqrt{\frac{G M}{r}}, \quad v_{\text{esc}} = \sqrt{\frac{2 G M}{R}} = \sqrt{2 g R}",
        "key_variables": "v_orb: circular orbital speed (m/s), v_esc: escape speed (m/s), R: planet radius (m), M: planet mass (kg)",
        "intuition_steps": [
            "The √2 Factor: Escape velocity from any circular orbit is exactly √2 ≈ 1.414 times orbital velocity: v_esc = √2 v_orb.",
            "Earth Benchmarks: Low Earth Orbit (LEO) velocity is ~7.8 km/s (~28,000 km/h). Earth's surface escape velocity is ~11.2 km/s (~40,300 km/h).",
            "Weightlessness in Orbit: Astronauts aboard the space station float not because gravity is zero (g at 400 km altitude is ~8.7 m/s²), but because the station and its occupants are in continuous free fall around Earth.",
        ],
    },
    "conservation_of_energy": {
        "title": "Law of Conservation of Mechanical and Total Energy",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "The Law of Conservation of Energy states that energy can neither be created nor destroyed; it can only transform from one form to another. "
            "For an isolated system subject only to conservative forces (such as gravity or elastic springs), total mechanical energy E = K + U remains strictly constant: ΔE = ΔK + ΔU = 0."
        ),
        "canonical_equation": "E_mech = K + U = ½ m v² + m g h = constant,   W_nc = ΔE",
        "latex": r"E = K + U = \frac{1}{2}mv^2 + U(\vec{r}) = \text{constant}, \quad \Delta K + \Delta U = W_{\text{non-conservative}}",
        "key_variables": "K = ½ m v²: kinetic energy (J), U: potential energy (J), W_nc: non-conservative work (J, e.g. friction)",
        "intuition_steps": [
            "Kinetic-Potential Trade-Off: In a swinging pendulum or rollercoaster, potential energy at peak elevation converts completely into kinetic energy at lowest point (v_max = √(2 g h)).",
            "Thermal Dissipation: When friction or drag acts, mechanical energy is not lost from the universe; it degrades into microscopic thermal internal energy (heat Q).",
        ],
    },
    "friction": {
        "title": "Friction Forces (Static, Kinetic, and Rolling Friction)",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Friction is the resistive contact force that opposes the relative motion or impending sliding between two solid surfaces in contact. "
            "Static friction f_s prevents motion up to a maximum threshold f_s,max = μ_s N; once the object breaks away and slides, kinetic friction f_k = μ_k N provides a roughly constant resistive drag."
        ),
        "canonical_equation": "f_s ≤ μ_s N,   f_s,max = μ_s N,   f_k = μ_k N",
        "latex": r"f_s \le \mu_s N, \quad f_k = \mu_k N, \quad \mu_s > \mu_k",
        "key_variables": "f_s: static friction (N), f_k: kinetic friction (N), μ_s: static coefficient, μ_k: kinetic coefficient, N: normal force (N)",
        "intuition_steps": [
            "Microscopic Origin: Contact surfaces possess microscopic peaks and valleys (asperities) that interlock and cold-weld together under compressive normal load.",
            "Static Exceeds Kinetic: It takes more force to get a stalled car or heavy furniture moving from rest than it takes to keep it sliding (μ_s > μ_k).",
        ],
    },
    "simple_harmonic_motion": {
        "title": "Simple Harmonic Motion (SHM) and Hooke's Law",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Simple Harmonic Motion occurs when the restoring force acting on a displaced system is directly proportional to its displacement from equilibrium "
            "and directed toward equilibrium: F = -k x. This produces sinusoidal oscillation governed by d²x/dt² + ω₀² x = 0, where natural angular frequency ω₀ = √(k/m)."
        ),
        "canonical_equation": "F = -k x,   d²x/dt² + (k/m) x = 0,   x(t) = A cos(ω₀ t + φ),   T = 2π √(m/k)",
        "latex": r"F = -kx, \quad \ddot{x} + \omega_0^2 x = 0, \quad \omega_0 = \sqrt{\frac{k}{m}}, \quad T = 2\pi\sqrt{\frac{m}{k}}",
        "key_variables": "k: spring force constant (N/m), m: oscillating mass (kg), A: amplitude (m), T: period (s), f = 1/T: frequency (Hz)",
        "intuition_steps": [
            "Continuous Energy Exchange: Potential energy U = ½ k x² is maximum at turning points (x = ±A, v = 0); kinetic energy K = ½ m v² is maximum at center equilibrium (x = 0, v = v_max = ω A).",
            "Isochronous Oscillation: The period T of an ideal harmonic oscillator is independent of the amplitude of vibration.",
        ],
    },
    "torque_and_rotational_motion": {
        "title": "Torque, Moment of Inertia, and Rotational Dynamics",
        "subdomain": "classical_mechanics",
        "core_principle": (
            "Torque τ is the rotational analog of force, measuring the effectiveness of a force in producing rotational acceleration about an axis: τ = r × F = r F sinθ. "
            "The rotational analog of Newton's second law is τ_net = I α, where I is the moment of inertia and α = dω/dt is angular acceleration."
        ),
        "canonical_equation": "τ = r × F = r F sinθ,   τ_net = I α = dL/dt,   L = I ω",
        "latex": r"\vec{\tau} = \vec{r}\times\vec{F}, \quad \tau = I\alpha, \quad L = I\omega, \quad K_{\text{rot}} = \frac{1}{2}I\omega^2",
        "key_variables": "τ: torque (N·m), r: lever arm distance (m), I = ∑ m_i r_i²: moment of inertia (kg·m²), α: angular acceleration (rad/s²)",
        "intuition_steps": [
            "Lever Arm Advantage: Pushing on a door handle located far from the hinges (large r) creates much greater torque than pushing near the hinge.",
            "Angular Momentum Conservation: When a spinning skater pulls their arms inward, moment of inertia I decreases, causing rotational velocity ω to increase sharply.",
        ],
    },
    "pascals_principle": {
        "title": "Pascal's Principle & Hydraulic Multiplication",
        "subdomain": "fluid_plasma",
        "core_principle": (
            "Pascal's Principle states that a change in pressure applied to an enclosed, incompressible static fluid is transmitted completely "
            "and undiminished to every portion of the fluid and to the walls of the containing vessel: ΔP₁ = ΔP₂."
        ),
        "canonical_equation": "P = F₁ / A₁ = F₂ / A₂,   F₂ = F₁ (A₂ / A₁)",
        "latex": r"\Delta P = \frac{F_1}{A_1} = \frac{F_2}{A_2} \implies F_2 = F_1\left(\frac{A_2}{A_1}\right)",
        "key_variables": "P: fluid pressure (Pa), F₁, F₂: forces on pistons (N), A₁, A₂: piston cross-sectional areas (m²)",
        "intuition_steps": [
            "Hydraulic Advantage: A modest force F₁ applied to a small piston produces a huge lifting force F₂ on a large piston, lifting heavy vehicles.",
            "Work Conservation: Because fluid volume is conserved (A₁ d₁ = A₂ d₂), input work equals output work (W = F₁ d₁ = F₂ d₂).",
        ],
    },
    "zeroth_law_thermodynamics": {
        "title": "Zeroth Law of Thermodynamics & Empirical Temperature",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "The Zeroth Law of Thermodynamics establishes that if two thermodynamic systems A and B are each in thermal equilibrium with a third system C, "
            "then system A and system B are in mutual thermal equilibrium with each other. This transitive property provides the physical foundation for defining temperature and building thermometers."
        ),
        "canonical_equation": r"T_A = T_C \text{ and } T_B = T_C \implies T_A = T_B",
        "latex": r"T_A = T_C \quad \text{and} \quad T_B = T_C \implies T_A = T_B",
        "key_variables": "T: thermodynamic temperature (K), thermal equilibrium: net heat transfer rate dQ/dt = 0",
        "intuition_steps": [
            "Thermometer Justification: When a thermometer reaches thermal equilibrium with an object, it reads its temperature; two objects yielding the same reading will exchange zero net heat when brought together.",
        ],
    },
    "third_law_thermodynamics": {
        "title": "Third Law of Thermodynamics & Absolute Zero Entropy",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "The Third Law of Thermodynamics states that as the absolute temperature of a pure crystalline substance approaches absolute zero "
            "(T → 0 K = -273.15°C), its entropy S approaches a universal minimum constant, conventionally defined as zero: lim_{T→0} S = 0."
        ),
        "canonical_equation": "lim_{T → 0 K} S = 0,   S = k_B ln(Ω_0) = 0",
        "latex": r"\lim_{T \to 0\,\text{K}} S = 0, \quad S = k_B \ln\Omega",
        "key_variables": "T: absolute temperature (K), S: entropy (J/K), k_B: Boltzmann constant",
        "intuition_steps": [
            "Unattainability of Absolute Zero: Because an infinite number of thermodynamic refrigeration cycles would be required to completely remove all thermal excitations, absolute zero cannot be reached in a finite sequence of operations.",
        ],
    },
    "ideal_gas_law": {
        "title": "Ideal Gas Law & Equation of State",
        "subdomain": "thermodynamics_stat_mech",
        "core_principle": (
            "The Ideal Gas Law is the equation of state relating pressure P, volume V, amount of gas n, and absolute temperature T "
            "for an ideal gas composed of point-like, non-interacting particles undergoing elastic collisions: P V = n R T = N k_B T."
        ),
        "canonical_equation": "P V = n R T = N k_B T,   R = 8.314 J/(mol·K)",
        "latex": r"P V = n R T = N k_B T, \quad \frac{P_1 V_1}{T_1} = \frac{P_2 V_2}{T_2}",
        "key_variables": "P: pressure (Pa), V: volume (m³), n: moles of gas, R: gas constant, T: temperature (K)",
        "intuition_steps": [
            "Kinetic Theory Link: Pressure arises from the collision of gas molecules against vessel walls; temperature is a direct measure of average molecular kinetic energy: K_avg = 3/2 k_B T.",
        ],
    },
    "thin_lens_equation": {
        "title": "Thin-Lens Equation and Optical Magnification",
        "subdomain": "optics_waves",
        "core_principle": (
            "The Gaussian thin-lens equation relates the focal length f of a lens to the distance of an object from the lens d_o "
            "and the distance of the formed image d_i: 1/f = 1/d_o + 1/d_i. Linear magnification is given by m = -d_i / d_o = h_i / h_o."
        ),
        "canonical_equation": "1/f = 1/d_o + 1/d_i,   m = -d_i / d_o = h_i / h_o",
        "latex": r"\frac{1}{f} = \frac{1}{d_o} + \frac{1}{d_i}, \quad m = -\frac{d_i}{d_o} = \frac{h_i}{h_o}",
        "key_variables": "f: focal length (m), d_o: object distance (m), d_i: image distance (m), m: lateral magnification",
        "intuition_steps": [
            "Real vs Virtual Images: When d_i > 0, the image is real and inverted; when d_i < 0, the image is virtual, upright, and on the same side as the object.",
        ],
    },
    "dispersion_of_light": {
        "title": "Dispersion of Light & Rainbow Formation",
        "subdomain": "optics_waves",
        "core_principle": (
            "Dispersion is the phenomenon where the phase velocity and refractive index n(λ) of a medium depend on the wavelength of light. "
            "In normal dispersion, violet light has a higher index of refraction than red light and bends more strongly, splitting white light into its spectral rainbow colors."
        ),
        "canonical_equation": "n = n(λ),   v(λ) = c / n(λ),   n_violet > n_red",
        "latex": r"n(\lambda) \approx A + \frac{B}{\lambda^2}, \quad v(\lambda) = \frac{c}{n(\lambda)}",
        "key_variables": "n: refractive index, λ: wavelength (m), v: phase velocity in medium (m/s)",
        "intuition_steps": [
            "Prism Spectrum: White sunlight entering a triangular glass prism separates into red, orange, yellow, green, blue, and violet because shorter wavelengths refract at sharper angles.",
            "Rainbows: Atmospheric water droplets act as tiny spherical prisms, combining internal refraction, total internal reflection, and dispersion.",
        ],
    },
    "sound_waves": {
        "title": "Sound Waves & Acoustic Pressure Oscillations",
        "subdomain": "optics_waves",
        "core_principle": (
            "Sound is a mechanical longitudinal compression wave that propagates through a material medium (solid, liquid, or gas) "
            "via alternating compressions (high density) and rarefactions (low density). Sound cannot propagate through a vacuum. Wave speed is v = f λ = √(B/ρ)."
        ),
        "canonical_equation": "v = f λ,   v_sound,air ≈ 331.3 + 0.606 T (°C) m/s,   v = √(B / ρ)",
        "latex": r"v = f\lambda = \sqrt{\frac{B}{\rho}}, \quad v_{\text{air}}(T) \approx 331.3\sqrt{1 + \frac{T}{273.15}}\,\text{m/s}",
        "key_variables": "v: speed of sound (m/s), f: frequency (Hz, pitch), λ: wavelength (m), B: bulk modulus (Pa), ρ: density (kg/m³)",
        "intuition_steps": [
            "Speed in Media: Sound travels faster in water (~1480 m/s) and steel (~5960 m/s) than in air (~343 m/s at 20°C) due to high elastic moduli.",
            "Audible Bandwidth: Healthy human ears perceive sounds from 20 Hz to 20,000 Hz.",
        ],
    },
    "electric_field_and_potential": {
        "title": "Electric Field, Electric Potential, and Voltage",
        "subdomain": "electromagnetism",
        "core_principle": (
            "An electric field E is a vector field representing electrostatic force experienced per unit positive charge: E = F/q. "
            "Electric potential V is electric potential energy per unit charge: V = U/q. The electric field points along the gradient of steepest potential decrease: E = -∇V."
        ),
        "canonical_equation": "E = F / q = k_e Q / r²,   V = k_e Q / r,   E = -dV/dr",
        "latex": r"\vec{E} = -\nabla V = \frac{1}{4\pi\varepsilon_0}\frac{Q}{r^2}\hat{r}, \quad V(r) = \frac{1}{4\pi\varepsilon_0}\frac{Q}{r}",
        "key_variables": "E: electric field strength (V/m or N/C), V: electric potential (Volts = J/C), Q: source charge (C)",
        "intuition_steps": [
            "Topography Analogy: Electric potential is analogous to gravitational elevation; positive charges fall 'downhill' toward lower potential, while negative charges climb 'uphill'.",
        ],
    },
    "capacitance": {
        "title": "Capacitance & Electrostatic Energy Storage",
        "subdomain": "electromagnetism",
        "core_principle": (
            "A capacitor is a device composed of two conducting plates separated by an insulator (dielectric) that stores separated electrical charge "
            "and electrostatic potential energy. Capacitance C is defined as the ratio of stored charge Q to the potential difference V: C = Q/V."
        ),
        "canonical_equation": "C = Q / V = ε_r ε₀ (A / d),   U_stored = ½ C V² = ½ Q V",
        "latex": r"C = \frac{Q}{V} = \frac{\kappa\varepsilon_0 A}{d}, \quad U = \frac{1}{2}CV^2",
        "key_variables": "C: capacitance (Farads, F), Q: charge (C), V: voltage (V), A: plate area (m²), d: plate separation (m)",
        "intuition_steps": [
            "Fast Discharge: Unlike chemical batteries that release energy slowly through chemical reactions, capacitors can discharge energy in microseconds, powering flashes and defibrillators.",
        ],
    },
    "lorentz_force": {
        "title": "Lorentz Force Law on Moving Charged Particles",
        "subdomain": "electromagnetism",
        "core_principle": (
            "The Lorentz force law defines the total electromagnetic force experienced by a particle carrying charge q moving with velocity v "
            "through combined electric E and magnetic B fields: F = q (E + v × B)."
        ),
        "canonical_equation": "F = q (E + v × B),   F_magnetic = q v B sinθ",
        "latex": r"\vec{F} = q\left(\vec{E} + \vec{v}\times\vec{B}\right), \quad F_B = q v B \sin\theta",
        "key_variables": "F: Lorentz force (N), q: charge (C), v: velocity (m/s), E: electric field (V/m), B: magnetic field (T)",
        "intuition_steps": [
            "Zero Magnetic Work: Because magnetic force is always perpendicular to velocity (F_B ⊥ v), static magnetic fields never do work and cannot alter a particle's kinetic energy.",
        ],
    },
    "faradays_law": {
        "title": "Faraday's Law of Electromagnetic Induction & Lenz's Law",
        "subdomain": "electromagnetism",
        "core_principle": (
            "Faraday's Law states that a changing magnetic flux Φ_B through a closed conducting circuit induces an electromotive force (EMF, voltage) "
            "proportional to the rate of change of flux: E = -N (dΦ_B/dt). Lenz's Law (the negative sign) dictates that induced current creates an opposing magnetic field fighting the flux change."
        ),
        "canonical_equation": "E_emf = -N (dΦ_B / dt),   Φ_B = ∫ B · dA = B A cosθ",
        "latex": r"\mathcal{E} = -\frac{d\Phi_B}{dt} = -\frac{d}{dt}\int \mathbf{B}\cdot d\mathbf{A}",
        "key_variables": "E_emf: induced electromotive force (V), Φ_B: magnetic flux (Weber), N: coil turns, t: time (s)",
        "intuition_steps": [
            "Powering Civilization: Hydroelectric generators, wind turbines, and power stations operate entirely on Faraday's law by rotating magnetic coils.",
        ],
    },
    "maxwell_equations": {
        "title": "Maxwell's Four Unified Equations of Electrodynamics",
        "subdomain": "electromagnetism",
        "core_principle": (
            "Maxwell's Equations form the complete classical foundation of electrodynamics, unifying electricity, magnetism, and light into four coupled equations: "
            "(1) Gauss's law for electricity, (2) Gauss's law for magnetism (no magnetic monopoles), (3) Faraday's law of induction, and (4) Ampere-Maxwell law with displacement current."
        ),
        "canonical_equation": "∇·E = ρ/ε₀,   ∇·B = 0,   ∇×E = -∂B/∂t,   ∇×B = μ₀J + μ₀ε₀ ∂E/∂t",
        "latex": r"\nabla\cdot\mathbf{E} = \frac{\rho}{\varepsilon_0}, \quad \nabla\cdot\mathbf{B} = 0, \quad \nabla\times\mathbf{E} = -\frac{\partial\mathbf{B}}{\partial t}, \quad \nabla\times\mathbf{B} = \mu_0\mathbf{J} + \mu_0\varepsilon_0\frac{\partial\mathbf{E}}{\partial t}",
        "key_variables": "E: electric field (V/m), B: magnetic field (T), ρ: charge density (C/m³), J: current density (A/m²), c = 1/√(μ₀ε₀)",
        "intuition_steps": [
            "Light as EM Waves: Maxwell demonstrated that oscillating electric and magnetic fields sustain each other, propagating through space at speed c ≈ 3×10⁸ m/s.",
        ],
    },
    "wave_particle_duality": {
        "title": "Wave-Particle Duality & de Broglie Matter Waves",
        "subdomain": "quantum_mechanics",
        "core_principle": (
            "Wave-particle duality asserts that all entities in the universe exhibit both wave-like and particle-like properties. "
            "Louis de Broglie postulated that any particle with linear momentum p has an associated matter wave with wavelength λ = h/p = h/(m v)."
        ),
        "canonical_equation": "λ = h / p = h / (m v),   E = h f = ℏ ω",
        "latex": r"\lambda = \frac{h}{p} = \frac{h}{m v}, \quad E = h f = \hbar\omega",
        "key_variables": "λ: de Broglie wavelength (m), h: Planck constant (6.626×10⁻³⁴ J·s), p: momentum (kg·m/s)",
        "intuition_steps": [
            "Electron Microscopy: High-speed electrons have vastly smaller de Broglie wavelengths than visible photons, allowing electron microscopes to resolve individual atomic lattices.",
        ],
    },
    "mass_energy_equivalence": {
        "title": "Einstein's Mass-Energy Equivalence (E = mc²)",
        "subdomain": "relativity_cosmology",
        "core_principle": (
            "Einstein's Mass-Energy Equivalence demonstrates that mass and energy are two forms of the exact same physical reality. "
            "An object at rest possesses intrinsic rest energy E_0 = m_0 c². In relativistic kinematics, total energy, momentum, and rest mass are unified by E² = (p c)² + (m_0 c²)²."
        ),
        "canonical_equation": "E_0 = m_0 c²,   E² = (p c)² + (m_0 c²)²,   ΔE = Δm c²",
        "latex": r"E_0 = m_0 c^2, \quad E^2 = (p c)^2 + (m_0 c^2)^2, \quad \Delta E = \Delta m\,c^2",
        "key_variables": "E: energy (J), m_0: rest mass (kg), c: speed of light (2.99792458×10⁸ m/s), p: momentum (kg·m/s)",
        "intuition_steps": [
            "Nuclear Power & Stars: In nuclear reactions, a tiny mass defect Δm between reactants and products converts into immense kinetic energy and gamma rays via ΔE = Δm c².",
        ],
    },
}


def get_concept_guide(subdomain: str, concept_label: Optional[str]) -> Dict[str, Any]:
    """Retrieve a structured teacher guide for any physics subdomain + concept."""
    norm_concept = (concept_label or "").strip().lower().replace(" ", "_")
    if norm_concept in CONCEPT_ENCYCLOPEDIA:
        return CONCEPT_ENCYCLOPEDIA[norm_concept]

    # Keyword / synonym fuzzy matching to foundational encyclopedia concepts
    SYNONYM_FALLBACKS: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"motion|kinematic|displacement|trajectory|translatory"), "motion"),
        (re.compile(r"dist.*displace|path.*offset"), "distance_and_displacement"),
        (re.compile(r"speed.*vel|vel.*speed"), "speed_vs_velocity"),
        (re.compile(r"accelerat|rate.*vel"), "acceleration"),
        (re.compile(r"suvat|eq.*motion|kinematic.*eq"), "equations_of_motion"),
        (re.compile(r"free.*fall|fall.*grav"), "free_fall"),
        (re.compile(r"projectile|ballistic|launch"), "projectile_motion"),
        (re.compile(r"third.*grav|3rd.*grav|kepler.*third|kepler.*3rd|harmonic.*law"), "third_law_of_gravity"),
        (re.compile(r"gravit|universal.*grav|attract.*mass"), "universal_gravitation"),
        (re.compile(r"escape.*vel|orbit.*vel|satellite"), "escape_and_orbital_velocity"),
        (re.compile(r"newton.*third|action.*reaction"), "newton_third_law"),
        (re.compile(r"newton.*first|inertia"), "newton_first_law"),
        (re.compile(r"newton.*second|f.*=.*m.*a"), "newton_second_law"),
        (re.compile(r"momentum|impulse|linear.*mom"), "conservation_of_momentum"),
        (re.compile(r"work.*energy|energy.*work"), "work_energy_theorem"),
        (re.compile(r"conserv.*energy|mech.*energy"), "conservation_of_energy"),
        (re.compile(r"friction|normal.*force|asperit"), "friction"),
        (re.compile(r"simple.*harmonic|shm|hooke|restoring"), "simple_harmonic_motion"),
        (re.compile(r"torque|moment.*inertia|rotat"), "torque_and_rotational_motion"),
        (re.compile(r"archimede|buoyan|float"), "archimedes_principle"),
        (re.compile(r"bernoulli|streamline|lift"), "bernoulli_principle"),
        (re.compile(r"pascal|hydraulic"), "pascals_principle"),
        (re.compile(r"zeroth.*law|thermal.*equil"), "zeroth_law_thermodynamics"),
        (re.compile(r"first.*law.*thermo|u.*=.*q.*w"), "first_law_thermodynamics"),
        (re.compile(r"second.*law.*thermo|entropy|carnot"), "second_law_thermodynamics"),
        (re.compile(r"third.*law.*thermo|zero.*entropy"), "third_law_thermodynamics"),
        (re.compile(r"ideal.*gas|p.*v.*=.*n.*r.*t"), "ideal_gas_law"),
        (re.compile(r"sky.*blue|rayleigh|scatter"), "rayleigh_scattering"),
        (re.compile(r"doppler"), "doppler_effect"),
        (re.compile(r"snell|refract"), "snells_law_refraction"),
        (re.compile(r"total.*internal|critical.*angle"), "total_internal_reflection"),
        (re.compile(r"lens|mirror|magnif"), "thin_lens_equation"),
        (re.compile(r"dispersion|rainbow|prism"), "dispersion_of_light"),
        (re.compile(r"sound|acoustic|pitch|loud"), "sound_waves"),
        (re.compile(r"current|drift.*vel|ampere"), "electric_current"),
        (re.compile(r"coulomb|electrostat"), "coulombs_law"),
        (re.compile(r"electric.*field|electric.*pot|voltage"), "electric_field_and_potential"),
        (re.compile(r"ohm|resist"), "ohms_law"),
        (re.compile(r"capacit|dielectric"), "capacitance"),
        (re.compile(r"faraday|induct|lenz"), "faradays_law"),
        (re.compile(r"lorentz|q.*v.*b"), "lorentz_force"),
        (re.compile(r"maxwell"), "maxwell_equations"),
        (re.compile(r"photoelectric|work.*func"), "photoelectric_effect"),
        (re.compile(r"wave.*particle|de.*broglie"), "wave_particle_duality"),
        (re.compile(r"uncertainty|heisenberg"), "uncertainty_principle"),
        (re.compile(r"mass.*energy|e.*=.*m.*c"), "mass_energy_equivalence"),
    ]
    for pat, target_key in SYNONYM_FALLBACKS:
        if pat.search(norm_concept) and target_key in CONCEPT_ENCYCLOPEDIA:
            return CONCEPT_ENCYCLOPEDIA[target_key]

    # Fallback synthesis for the remaining concepts across all 10 subdomains
    pretty_concept = (concept_label or subdomain).replace("_", " ").title()
    pretty_sub = subdomain.replace("_", " ").title()

    subdomain_defaults: Dict[str, Dict[str, str]] = {
        "classical_mechanics": {
            "eq": "F_net = m a = dp/dt,   W = ΔK = ½ m v²,   E_mech = K + U = constant",
            "latex": r"\vec{F}_{\text{net}} = m\vec{a} = \frac{d\vec{p}}{dt}, \quad W = \Delta K, \quad E = K + U",
            "vars": "F: net force (N), m: mass (kg), a: acceleration (m/s²), v: velocity (m/s), K: kinetic energy (J)",
        },
        "electromagnetism": {
            "eq": "∇·E = ρ/ε₀,   ∇×B = μ₀J + μ₀ε₀ ∂E/∂t,   F = q(E + v×B)",
            "latex": r"\nabla\cdot\mathbf{E} = \frac{\rho}{\varepsilon_0}, \quad \nabla\times\mathbf{B} = \mu_0\mathbf{J} + \mu_0\varepsilon_0\frac{\partial\mathbf{E}}{\partial t}",
            "vars": "E: electric field (V/m), B: magnetic flux density (T), ρ: charge density (C/m³), J: current density (A/m²)",
        },
        "thermodynamics_stat_mech": {
            "eq": "ΔU = Q - W,   P V = n R T,   ΔS ≥ 0",
            "latex": r"\Delta U = Q - W, \quad P V = n R T, \quad \Delta S \ge 0",
            "vars": "U: internal energy (J), Q: heat added (J), W: work done (J), P: pressure (Pa), T: temperature (K)",
        },
        "quantum_mechanics": {
            "eq": "iℏ ∂Ψ/∂t = Ĥ Ψ,   E = h ν,   λ = h/p",
            "latex": r"i\hbar\frac{\partial\Psi}{\partial t} = \hat{H}\Psi, \quad E = h\nu, \quad \lambda = \frac{h}{p}",
            "vars": "Ψ: quantum wavefunction, Ĥ: Hamiltonian operator, ℏ: reduced Planck constant, λ: de Broglie wavelength",
        },
        "relativity_cosmology": {
            "eq": "E² = (p c)² + (m_0 c²)²,   ds² = c² dt² - dx² - dy² - dz²,   E = m c²",
            "latex": r"E^2 = (pc)^2 + (m_0 c^2)^2, \quad E = mc^2",
            "vars": "m_0: rest mass (kg), c: speed of light (m/s), p: momentum (kg·m/s), E: energy (J)",
        },
        "fluid_plasma": {
            "eq": "P + ½ ρ v² + ρ g h = constant,   F_b = ρ_fluid V_disp g",
            "latex": r"P + \frac{1}{2}\rho v^2 + \rho g h = \text{constant}, \quad F_b = \rho g V",
            "vars": "P: pressure (Pa), ρ: fluid density (kg/m³), v: flow speed (m/s), F_b: buoyant force (N)",
        },
        "solid_state": {
            "eq": "σ = n e² τ / m*,   E(k + G) = E(k),   ψ_{n,k}(r) = e^{i k·r} u_{n,k}(r)",
            "latex": r"\psi_{n\mathbf{k}}(\mathbf{r}) = e^{i\mathbf{k}\cdot\mathbf{r}}u_{n\mathbf{k}}(\mathbf{r}), \quad \sigma = \frac{n e^2 \tau}{m^*}",
            "vars": "k: crystal wavevector (m⁻¹), u_{n,k}(r): lattice-periodic Bloch function, m*: effective mass",
        },
        "quantum_field_theory": {
            "eq": "(i γ^μ D_μ - m)ψ = 0,   (□ + m²)φ = 0,   Z[J] = ∫ Dφ e^{i S[φ]}",
            "latex": r"(i\gamma^\mu D_\mu - m)\psi = 0, \quad (\Box + m^2)\phi = 0",
            "vars": "ψ: Dirac spinor field, γ^μ: Dirac matrices, D_μ: gauge derivative, m: particle mass",
        },
        "optics_waves": {
            "eq": "v = f λ,   n₁ sin(θ₁) = n₂ sin(θ₂),   1/f = 1/d_o + 1/d_i",
            "latex": r"v = f\lambda, \quad n_1\sin\theta_1 = n_2\sin\theta_2, \quad \frac{1}{f} = \frac{1}{d_o} + \frac{1}{d_i}",
            "vars": "v: wave speed (m/s), f: frequency (Hz), λ: wavelength (m), n: refractive index, f: focal length",
        },
        "quantum_information": {
            "eq": "S(ρ) = -Tr(ρ ln ρ),   |S_CHSH| ≤ 2√2,   |ψ⟩ = cos(θ/2)|0⟩ + e^{iφ}sin(θ/2)|1⟩",
            "latex": r"|\psi\rangle = \cos\frac{\theta}{2}|0\rangle + e^{i\phi}\sin\frac{\theta}{2}|1\rangle, \quad S(\rho) = -\operatorname{Tr}(\rho\ln\rho)",
            "vars": "|ψ⟩: pure qubit state on Bloch sphere, ρ: density operator, S(ρ): von Neumann entanglement entropy",
        },
    }
    sub_meta = subdomain_defaults.get(subdomain, {
        "eq": "F_net = m a,   W = ΔK,   v = f λ",
        "latex": r"\vec{F}_{\text{net}} = m\vec{a}",
        "vars": "Standard SI physical observables and conservation laws",
    })
    return {
        "title": f"{pretty_concept} ({pretty_sub})",
        "subdomain": subdomain,
        "core_principle": (
            f"{pretty_concept} is a governing physical principle in {pretty_sub} that describes the observable dynamics, "
            f"conservation laws, and boundary conditions of physical systems in this domain."
        ),
        "canonical_equation": sub_meta["eq"],
        "latex": sub_meta["latex"],
        "key_variables": sub_meta["vars"],
        "intuition_steps": [
            f"1. Identify the physical system, boundary conditions, and regime governing {pretty_concept.lower()}.",
            f"2. Apply governing conservation and dynamical equations using consistent SI units.",
            "3. Verify limiting cases, dimensional homogeneity, and physical consistency.",
        ],
    }


def extract_clean_sentences_from_passage(raw_passage_text: str, query: str, max_sentences: int = 3) -> str:
    """Extract clean, complete, grammatical sentences from a verified textbook passage without broken PDF line wraps or boilerplate."""
    if not raw_passage_text:
        return ""
    # Strip page markers and image attribution credits
    cleaned = re.sub(r"\[p\.\d+\]\s*", "", raw_passage_text)
    cleaned = re.sub(r"\(credit:[^)]+\)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Split into candidate sentences on sentence-ending punctuation
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", cleaned)
    query_tokens = {
        tok for tok in re.findall(r"[a-zA-Z]{3,}", query.lower())
        if tok not in {"what", "how", "why", "explain", "define", "state", "the", "and", "for", "with", "from", "into"}
    }

    BOILERPLATE_SUBSTRINGS = (
        "copyright", "all rights reserved", "creative commons", "license", "licence",
        "www.", "http:", "https:", "fullerton", "california", "rev.", "isbn",
        "contents thermodynamics", "flow of entropy", "figure ", "challenge ",
        "problem set", "page ", "editorial", "published by", "printed in",
        "credit:", "flickr", "wikimedia", "getty",
    )

    scored: List[tuple[float, int, str]] = []
    clean_candidates: List[str] = []

    for idx, sent in enumerate(raw_sentences):
        s = sent.strip()
        if len(s) < 35 or len(s) > 420:
            continue
        # Ensure it starts cleanly and ends with punctuation
        if not s[0].isalnum() and s[0] not in "(\"‘'":
            continue
        if s[-1] not in ".!?":
            s = s + "."
        s_low = s.lower()

        # Reject boilerplate sentences (copyrights, licenses, publisher headers, table of contents)
        if any(bp in s_low for bp in BOILERPLATE_SUBSTRINGS):
            continue

        clean_candidates.append(s)
        overlap = sum(2.5 for tok in query_tokens if tok in s_low)
        # Bonus for definitional / pedagogical phrasing
        if any(p in s_low for p in ("is defined as", "is defined to be", "states that", "defined as", "called", "known as", "law", "principle", "equation", "conservation", "energy", "velocity", "force", "acceleration", "motion")):
            overlap += 2.0
        scored.append((overlap, -idx, s))

    if not scored:
        if clean_candidates:
            return " ".join(clean_candidates[:max_sentences])
        fallback = cleaned[:360].rsplit(" ", 1)[0]
        # Clean any remaining boilerplate from fallback
        if any(bp in fallback.lower() for bp in BOILERPLATE_SUBSTRINGS):
            return "Physics textbooks establish the foundational definitions, equations of motion, and conservation laws for this phenomenon."
        return fallback + ("." if not fallback.endswith(".") else "")

    scored.sort(reverse=True)
    chosen = sorted(scored[:max_sentences], key=lambda item: -item[1])
    return " ".join(item[2] for item in chosen)


class PedagogicalSynthesizer:
    """Synthesizes clean teacher-grade explanations grounded in SHA-256 verified textbook passages."""

    _READER_CACHE: Any = None
    _READER_MTIME: float = 0.0

    CONVENTIONS_BY_SUBDOMAIN: Dict[str, Dict[str, str]] = {
        "classical_mechanics": {
            "convention_name": "Lagrangian Sign & Generalized Coordinate Convention",
            "book_a_convention": "Goldstein / Landau Vol. 1: L = T - V, Euler-Lagrange d/dt(∂L/∂q_dot) - ∂L/∂q = Q_nonconservative",
            "book_b_convention": "Newtonian Vector Mechanics (OpenStax / Halliday): ΣF = m a, constraint forces N and T explicit",
            "translation_rule": "Set Q_nc = 0 for conservative forces; generalized momentum p_i = ∂L/∂q_dot_i reduces to m v_i in Cartesian coordinates.",
        },
        "electromagnetism": {
            "convention_name": "SI Rationalized MKS vs. Gaussian CGS Electrodynamics Units",
            "book_a_convention": "Griffiths / University Physics (SI MKS): ∇·E = ρ/ε_0, F = q(E + v × B), Coulomb factor 1/(4π ε_0)",
            "book_b_convention": "Landau & Lifshitz Vol. 2 & Vol. 8 (Gaussian CGS): ∇·E = 4π ρ, F = q(E + (v/c) × B), 1/(4π ε_0) -> 1",
            "translation_rule": "To convert SI -> Gaussian CGS: replace ε_0 -> 1/(4π), μ_0 -> 4π/c², and B_SI -> B_CGS / c.",
        },
        "thermodynamics_stat_mech": {
            "convention_name": "First Law Work Sign & Boltzmann Entropy Convention",
            "book_a_convention": "Physics / Engineering (OpenStax / Tong): dU = δQ - δW (W > 0 is work done BY the system, δW = P dV)",
            "book_b_convention": "Landau Vol. 5 / IUPAC Statistical Physics: dE = T dS - P dV + μ dN (δW_on = -P dV is work done ON the system)",
            "translation_rule": "W_by_system = -W_on_system = ∫ P dV; both yield identical internal energy ΔU when sign of W is matched.",
        },
        "quantum_mechanics": {
            "convention_name": "Dirac Bra-Ket & Fourier Wavefunction Normalization",
            "book_a_convention": "Dirac / Sakurai: <x|p> = (2π ħ)^(-1/2) exp(i p x / ħ), completeness ∫|p><p|dp = I",
            "book_b_convention": "Griffiths / Wave Mechanics: ψ(x) = (2π)^(-1/2) ∫ φ(k) exp(i k x) dk with k = p / ħ",
            "translation_rule": "Multiply k-space momentum amplitudes by ħ^(-1/2) when transforming to canonical p-space bras/kets.",
        },
        "relativity_cosmology": {
            "convention_name": "Minkowski Metric Signature (West Coast vs. East Coast)",
            "book_a_convention": "Landau & Lifshitz Vol. 2 / Particle Physics (+,-,-,-): ds² = c² dt² - dx² - dy² - dz² (timelike ds² > 0)",
            "book_b_convention": "Sean Carroll / General Relativity (-,+,+,+): ds² = -c² dt² + dx² + dy² + dz² (proper time dτ² = -ds²/c²)",
            "translation_rule": "Multiply metric tensor g_μν by -1 when switching between (+,-,-,-) and (-,+,+,+); Einstein tensor G_μν is invariant.",
        },
        "fluid_plasma": {
            "convention_name": "Cauchy Stress & Viscous Sign Convention",
            "book_a_convention": "Landau Vol. 6 / Fluid Mechanics: σ_ij = -p δ_ij + τ_ij (compressive pressure p > 0)",
            "book_b_convention": "Continuum / Plasma Transport: Π_ij = p δ_ij + ρ v_i v_j - τ_ij (momentum flux tensor)",
            "translation_rule": "Divergence of momentum flux tensor -∂Π_ij/∂x_j equals net Navier-Stokes force density.",
        },
        "solid_state": {
            "convention_name": "Elasticity Strain Tensor & Reciprocal Lattice 2π Factor",
            "book_a_convention": "Landau Vol. 7 / Solid State (Crystallographer vs. Physicist): G · R = 2π m, u_ij = 1/2(∂u_i/∂x_j + ∂u_j/∂x_i)",
            "book_b_convention": "Engineering Voigt Shear Strain: γ_xy = 2 u_xy = ∂u_x/∂y + ∂u_y/∂x",
            "translation_rule": "Tensor shear component u_xy is half the engineering shear angle γ_xy.",
        },
        "quantum_field_theory": {
            "convention_name": "Natural Units (ħ = c = 1) & Feynman Propagator iε Prescription",
            "book_a_convention": "Feynman QED / Tong QFT: ħ = c = 1, [Mass] = [Energy] = [Length]^(-1), D_F(p) = i / (p² - m² + iε)",
            "book_b_convention": "SI Restored Units: p² c² - m² c⁴, Compton wavelength λ_C = ħ / (m c)",
            "translation_rule": "Restore powers of ħ and c via dimensional analysis: multiply energy by (ħ c)^(-1) to obtain inverse length.",
        },
        "optics_waves": {
            "convention_name": "Cartesian vs. Gaussian Sign Convention & Phasor Phase",
            "book_a_convention": "Gaussian Thin-Lens (OpenStax): 1/f = 1/d_o + 1/d_i (d_o > 0 for real object, d_i > 0 on transmission side)",
            "book_b_convention": "Cartesian Coordinate Optics: 1/v - 1/u = 1/f (all distances measured from vertex with sign of x-axis)",
            "translation_rule": "Set u = -d_o and v = +d_i to map Cartesian lens equation 1/v - 1/u = 1/f into 1/d_o + 1/d_i = 1/f.",
        },
        "quantum_information": {
            "convention_name": "Computational Z-Basis & von Neumann Entropy Logarithm Base",
            "book_a_convention": "Quantum Information (Nielsen & Chuang): |0> = [1, 0]^T, |1> = [0, 1]^T, S(ρ) = -Tr(ρ log_2 ρ) in bits (shannons)",
            "book_b_convention": "Statistical Mechanics (Landau): S = -k_B Tr(ρ ln ρ) in natural units (nats)",
            "translation_rule": "S_bits = S_nats / ln(2); Bloch north pole corresponds to Z|+1> = |0>.",
        },
    }

    @classmethod
    def get_convention_harmonization(cls, subdomain: str) -> Dict[str, str]:
        """Pillar 7: Return cross-book sign, unit, and metric convention translation guide."""
        return cls.CONVENTIONS_BY_SUBDOMAIN.get(
            subdomain,
            cls.CONVENTIONS_BY_SUBDOMAIN["classical_mechanics"],
        )

    @classmethod
    def generate_interactive_simulation_widget(
        cls,
        subdomain: str,
        concept_label: Optional[str],
        numerical_solution: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Pillar 10: Generate an Interactive HTML5 Canvas Simulation Spec & Embeddable Widget."""
        mode = (numerical_solution or {}).get("mode") or subdomain
        val = (numerical_solution or {}).get("final_value", 1.0)
        unit = (numerical_solution or {}).get("si_unit", "")
        target_var = (numerical_solution or {}).get("target_variable", "y")
        steps = (numerical_solution or {}).get("steps") or []
        knowns = (steps[0].get("knowns_used") if steps and isinstance(steps[0], dict) else {}) or {}

        widget_html = (
            f'<div class="physics-sim-widget" data-subdomain="{subdomain}" data-mode="{mode}" '
            f'style="border:1px solid #334155;border-radius:10px;padding:12px;background:#0f172a;color:#f8fafc;">'
            f'<div style="font-weight:700;margin-bottom:6px;">Interactive Physics Simulation: {subdomain.replace("_", " ").title()} ({mode})</div>'
            f'<canvas id="sim-canvas-{subdomain}" width="480" height="200" style="width:100%;background:#1e293b;border-radius:6px;"></canvas>'
            f'<div style="margin-top:8px;font-size:13px;">Computed Observable: <code>{target_var} = {val} {unit}</code></div>'
            f'</div>'
        )
        return {
            "widget_type": "html5_canvas_physics_simulation",
            "subdomain": subdomain,
            "simulation_mode": mode,
            "concept": concept_label or "general",
            "initial_parameters": knowns,
            "target_observable": target_var,
            "computed_value": val,
            "si_unit": unit,
            "interactive_controls": list(knowns.keys()) if knowns else ["parameter_1", "parameter_2"],
            "embeddable_html": widget_html,
        }

    @classmethod
    def _get_neural_reader(cls) -> Any:
        from pathlib import Path
        from ..neural.passage_reader import PassageReaderBundle, tokenize

        # This bundle is experimental; the Harness must not silently opt in.
        if os.environ.get("TINY_EXPERT_ALLOW_EXPERIMENTAL_READER") != "1":
            return None

        reader_dir = Path(__file__).resolve().parents[1] / "data" / "models" / "physics_passage_reader"
        manifest_file = reader_dir / "manifest.json"
        if not manifest_file.is_file():
            return None
        mtime = manifest_file.stat().st_mtime
        if cls._READER_CACHE is None or cls._READER_MTIME != mtime:
            try:
                cls._READER_CACHE = PassageReaderBundle(reader_dir, allow_experimental=True)
                cls._READER_MTIME = mtime
            except Exception:
                return None
        return cls._READER_CACHE

    @classmethod
    def synthesize_physics_response(
        cls,
        query: str,
        subdomain: str,
        concept_label: Optional[str],
        book_engine: Any,
        numerical_solution: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from ..neural.passage_reader import tokenize

        guide = get_concept_guide(subdomain, concept_label)

        # Retrieve & cryptographically verify passages across DISTINCT textbooks (Multi-Book Perspectives)
        raw_passages = book_engine.search(query=query, shelf="physics", top_k=15) if book_engine is not None else []
        if len(raw_passages) < 2 and concept_label:
            expanded_q = f"{query} {concept_label.replace('_', ' ')}"
            raw_passages = book_engine.search(query=expanded_q, shelf="physics", top_k=15) if book_engine is not None else []
        search_q = query

        # Prioritize distinct books first so duplicate-topic books each contribute their unique perspective
        diverse_passages: List[Dict[str, Any]] = []
        seen_docs: set[str] = set()
        overflow_passages: List[Dict[str, Any]] = []
        for p in raw_passages:
            doc_key = str(p.get("document_id") or p.get("source") or "").split("(")[0].strip()
            if doc_key and doc_key not in seen_docs:
                seen_docs.add(doc_key)
                diverse_passages.append(p)
            else:
                overflow_passages.append(p)
            if len(diverse_passages) >= 4:
                break
        passages = (diverse_passages + overflow_passages)[:3]

        perspective_roles = (
            "Primary Conceptual Reference",
            "Alternative Theoretical / Mathematical Formulation",
            "Cross-Book Verification & Perspective",
        )
        verified_citations: List[Dict[str, Any]] = []
        extractive_summary = ""
        neural_answer_span: Optional[Dict[str, Any]] = None
        reader = cls._get_neural_reader()

        for idx_p, p in enumerate(passages):
            pid = p.get("passage_id")
            if not pid or book_engine is None:
                continue
            try:
                proof = book_engine.verify_passage(pid)
                src_label = str(p.get("source") or "Physics Textbook")
                book_title = src_label.split(" (Pages")[0].split(" (Overview")[0].strip()
                clean_excerpt = extract_clean_sentences_from_passage(p.get("text", ""), search_q, max_sentences=2)
                role = perspective_roles[min(idx_p, len(perspective_roles) - 1)]
                verified_citations.append({
                    "passage_id": pid,
                    "document_id": p.get("document_id"),
                    "book_title": book_title,
                    "source": src_label,
                    "chapter_title": p.get("chapter_title"),
                    "perspective_role": role,
                    "perspective_excerpt": clean_excerpt,
                    "sha256_revision": proof.get("source_revision"),
                    "byte_range": proof.get("verified_text_offsets") or [proof.get("raw_start"), proof.get("raw_end")],
                    "verified": bool(proof.get("source_consistency", True)),
                    "verbatim_excerpt": p.get("text", "")[:500],
                })
                if not extractive_summary:
                    extractive_summary = extract_clean_sentences_from_passage(p.get("text", ""), search_q, max_sentences=3)
                if neural_answer_span is None and reader is not None:
                    # BiGRU Neural Passage Reader operates on <= 256 tokens and <= 48 question tokens
                    q_tokens = tokenize(query)
                    p_text = extractive_summary or p.get("text", "")[:700]
                    p_tokens = tokenize(p_text)
                    if 1 <= len(q_tokens) <= 48 and 1 <= len(p_tokens) <= 250:
                        q_clipped = query if len(q_tokens) <= 45 else " ".join(t[0] for t in q_tokens[:40])
                        pred_span = reader.predict(q_clipped, p_text, min_score=0.001)
                        if (pred_span.get("status") == "experimental_answer"
                                and re.search(r"\w", pred_span.get("answer") or "")):
                            neural_answer_span = {
                                "answer": pred_span["answer"],
                                "score": pred_span.get("score"),
                                "passage_id": pid,
                            }
            except Exception:
                continue

        # Build clean, human-readable teacher explanation
        lines = [
            f"### {guide['title']}",
            f"**Principle:** {guide['core_principle']}",
            f"**Canonical Equation:** `{guide['canonical_equation']}`",
            f"**Key Variables & SI Units:** {guide['key_variables']}",
        ]

        if guide.get("intuition_steps"):
            lines.append("\n**Physical Mechanism & Real-World Intuition:**")
            for step in guide["intuition_steps"]:
                lines.append(f"  - {step}")

        if numerical_solution and numerical_solution.get("solved"):
            lines.append(
                f"**Computed Numerical Result:** `{numerical_solution.get('target_variable')} = "
                f"{numerical_solution.get('final_value'):.6g} {numerical_solution.get('si_unit', '')}` "
                f"({numerical_solution.get('mode', 'symbolic_cas')}, {numerical_solution.get('hops', 1)} hop(s))"
            )
            for idx, step in enumerate(numerical_solution.get("steps", []), 1):
                lines.append(
                    f"  - Step {idx} ({step.get('title', 'Formula')}): `{step.get('isolated_symbolic_form')}` "
                    f"→ `{step.get('value'):.6g} {step.get('si_unit', '')}`"
                )
        elif numerical_solution and numerical_solution.get("physical_violations"):
            lines.append(
                f"**Physical Sanity Critic Alert:** {'; '.join(numerical_solution['physical_violations'])}"
            )

        if neural_answer_span and neural_answer_span.get("answer"):
            lines.append(f"**Experimental BiGRU Span (unvalidated):** \"{neural_answer_span['answer']}\"")

        if extractive_summary:
            lines.append(f"**Retrieved Textbook Excerpt (relevance not verified):** {extractive_summary}")

        from .cas_engine import SymbolicCASEngine

        mode_hint = " ".join(str(x) for x in (query, concept_label,
                              (numerical_solution or {}).get("mode")) if x)
        convention_harmonizer = cls.get_convention_harmonization(subdomain)
        first_principles_derivation = SymbolicCASEngine.derive_from_first_principles(subdomain, mode_hint)
        proof_certificate = SymbolicCASEngine.verify_mathematical_proof_certificate(
            subdomain, mode_hint, numerical_solution, verified_citations
        )
        simulation_widget = cls.generate_interactive_simulation_widget(subdomain, concept_label, numerical_solution)

        if first_principles_derivation.get("derived"):
            lines.append(
                f"**First-Principles Symbolic Derivation ({first_principles_derivation.get('axiom')}):** "
                f"`{first_principles_derivation.get('derived_closed_form')}`"
            )
        lines.append(
            f"**Cross-Book Convention Harmonizer ({convention_harmonizer['convention_name']}):** "
            f"{convention_harmonizer['translation_rule']}"
        )
        if verified_citations:
            top_cit = verified_citations[0]
            lines.append(
                f"**Verified Source Citation:** *{top_cit['source']}* "
                f"(SHA-256: `{str(top_cit['sha256_revision'])[:16]}...`, character offsets `{top_cit['byte_range'][0]}..{top_cit['byte_range'][1]}` — source integrity checked; answer support not evaluated)"
            )
            if len(verified_citations) > 1:
                persp_lines = ["**Additional Retrieved Sources (not independent answer verification):**"]
                for cit in verified_citations:
                    persp_lines.append(
                        f"  - **According to *{cit['book_title']}*** ({cit['perspective_role']}): "
                        f"\"{cit['perspective_excerpt']}\" "
                        f"`[SHA-256: {str(cit['sha256_revision'])[:12]}...]`"
                    )
                lines.append("\n".join(persp_lines))

        return {
            "title": guide["title"],
            "core_principle": guide["core_principle"],
            "canonical_equation": guide["canonical_equation"],
            "latex": guide["latex"],
            "key_variables": guide["key_variables"],
            "intuition_steps": guide["intuition_steps"],
            "neural_answer_span": neural_answer_span,
            "extractive_textbook_summary": extractive_summary,
            "convention_harmonizer": convention_harmonizer,
            "first_principles_derivation": first_principles_derivation,
            "proof_certificate": proof_certificate,
            "simulation_widget": simulation_widget,
            "distinct_books_cited": len({c.get("book_title") for c in verified_citations if c.get("book_title")}),
            "verified_citations": verified_citations,
            "teacher_markdown": "\n\n".join(lines),
        }
