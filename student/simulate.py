import json, random
from curve.curve import State, terrynce_value, phi_star

def simulate_lane(law, style, history_path):
    forgiveness = style["forgiveness"]   # 0.02..0.30
    smoothing   = style["smoothing"]     # 0.05..0.40
    vkd         = style["vkd_discount"]  # 0.20..0.90

    # -> state mapping (transparent knobs → curve state)
    s = State(
        I_star = 1.0 + 0.2*forgiveness,          # more forgiveness → higher ceiling
        K      = 0.3 + 0.5*(1.0-smoothing),      # less smoothing → more stress load
        W      = 0.7 + 0.1*(1.0 - vkd),          # less short-chasing → better work potential
        gamma  = 1.0 + 0.2*smoothing,            # steadier learning pressure
        eps    = 0.10 + 0.15*forgiveness,        # sloppiness lifts entropy
        Ic     = 1.0
    )

    V   = terrynce_value(s)
    PHI = phi_star(s)

    # Canon invariants
    Ic     = 0.30 + 0.6*forgiveness + 0.25*(1.0 - smoothing) + 0.15*vkd + 0.05*random.random()
    kappa  = 0.40 + 0.40*(1.0 - smoothing) + 0.25*forgiveness + 0.20*vkd + 0.05*random.random()

    budget_ok = (Ic <= law["budget"]["k"] * law["budget"]["AMB"])
    bend_ok   = (kappa < law["bend"]["kappa_c"])

    # Emergence metrics (interpretable proxies)
    false_green = max(0.0, 0.01 + 0.25*(forgiveness-0.10) + 0.10*(0.30 - smoothing) + 0.02*random.random())
    false_green = min(false_green, 0.20)

    flap_index  = max(0.0, 0.05 + 0.30*(0.40 - smoothing) + 0.05*(vkd) + 0.02*random.random())
    flap_index  = min(flap_index, 0.40)

    rec = 2 + 4*smoothing - 3*forgiveness + 1.5*(0.5 - vkd) + random.random()
    recovery_halflife = max(1, int(round(rec)))

    exception_rate = max(0.0, 0.01 + 0.10*(forgiveness - 0.10) + 0.02*random.random())
    exception_rate = min(exception_rate, 0.20)

    recognition = 1.0 - abs(forgiveness - 0.14)/0.20 - abs(smoothing - 0.22)/0.25
    recognition = max(0.0, min(1.0, recognition))

    alignment = max(0.0, 1.0 - 2.2*false_green - 4.0*exception_rate)
    alignment = min(alignment, 1.0)

    w = law["weights"]
    objective_J = (
        w["w_recognition"]*recognition +
        w["w_alignment"]*alignment -
        w["lambda_flap"]*flap_index -
        w["lambda_exception"]*exception_rate
    )

    return {
        "law": {
            "budget_ok": budget_ok, "bend_ok": bend_ok,
            "Ic": round(Ic,3), "AMB": law["budget"]["AMB"], "k": law["budget"]["k"],
            "kappa": round(kappa,3), "kappa_c": law["bend"]["kappa_c"]
        },
        "emergence": {
            "V": round(V,4), "phi_star": round(PHI,4),
            "recognition": round(recognition,3), "alignment": round(alignment,3),
            "false_green": round(false_green,3), "flap_index": round(flap_index,3),
            "recovery_halflife": recovery_halflife, "exception_rate": round(exception_rate,3),
            "objective_J": round(objective_J,3)
        }
    }
