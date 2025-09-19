from dataclasses import dataclass
from math import pow

@dataclass
class State:
    I_star: float  # integration ceiling
    K: float       # stress load (kappa load)
    W: float       # work/energy
    gamma: float   # learning pressure
    eps: float     # entropy/fragmentation
    Ic: float = 1.0

def terrynce_value(s: State) -> float:
    k_term = max(0.0, s.I_star - s.K)
    work   = pow(max(0.0, s.W), s.gamma)
    return k_term * work * (1.0 - min(1.0, max(0.0, s.eps)))

def phi_star(s: State, a_k=0.6, a_e=0.7, delta=0.0) -> float:
    denom = 1.0 + a_k*max(0.0, s.K) + a_e*max(0.0, s.eps)
    return s.Ic / max(1e-9, denom) + delta
