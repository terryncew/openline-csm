import json, os, time, hashlib, random
from pathlib import Path
from student.simulate import simulate_lane

ROOT = Path(__file__).resolve().parents[1]
LAW = json.loads((ROOT/"canon/law.json").read_text())

LANE = "lane1"
STYLE_PATH = ROOT/f"adapters/{LANE}/style.json"
LAST_SIM_PATH = ROOT/f"adapters/{LANE}/last_sim.json"

DOCS = ROOT/"docs"
RECEIPTS = DOCS/"receipts"
RECEIPTS.mkdir(parents=True, exist_ok=True)

def now_utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def digest(obj): return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

def read_style():
    if STYLE_PATH.exists():
        return json.loads(STYLE_PATH.read_text())
    return { "forgiveness":0.10, "smoothing":0.20, "reflex_order":["rollback","rules_first","retune"], "vkd_discount":0.50 }

def read_last_sim():
    if LAST_SIM_PATH.exists():
        return json.loads(LAST_SIM_PATH.read_text())
    return None

def propose_style(old):
    n = old.copy()
    for k,step,lo,hi in [
        ("forgiveness", 0.02, 0.02, 0.30),
        ("smoothing",   0.05, 0.05, 0.40),
        ("vkd_discount",0.05, 0.20, 0.90),
    ]:
        n[k] = round(min(hi, max(lo, old[k] + random.choice([-step, step]))), 2)
    if random.random() < 0.20:
        ro = n["reflex_order"][:]
        ro[-1], ro[-2] = ro[-2], ro[-1]
        n["reflex_order"] = ro
    return n

def judge(sim, last_sim):
    reasons, verdict = [], "accepted"
    if not sim["law"]["budget_ok"]:
        verdict="rejected"; reasons.append("budget fail")
    if not sim["law"]["bend_ok"]:
        verdict="rejected"; reasons.append("bend fail")
    bm = LAW["benchmark"]
    if sim["emergence"]["false_green"] > bm["max_false_green"]:
        verdict="rejected"; reasons.append("false_green high")
    if sim["emergence"]["flap_index"] > bm["max_flap_index"]:
        verdict="rejected"; reasons.append("flap high")
    if sim["emergence"]["recovery_halflife"] > bm["target_recovery_halflife"]:
        verdict="rejected"; reasons.append("slow recovery")
    if sim["emergence"]["exception_rate"] > LAW["exception"]["target_rate"]:
        verdict="rejected"; reasons.append("exception rate high")
    if verdict=="accepted" and last_sim:
        not_worse = (sim["emergence"]["false_green"] <= last_sim["emergence"]["false_green"]+1e-6
                     and sim["emergence"]["flap_index"] <= last_sim["emergence"]["flap_index"]+1e-6)
        better    = sim["emergence"]["objective_J"] >= last_sim["emergence"]["objective_J"]-1e-6
        if not (not_worse or better):
            verdict="rejected"; reasons.append("no improvement")
    return verdict, reasons

def write_receipt(title, status, point, because, but, so, extras=None, path=None):
    obj = {
        "title": title, "status": status, "point": point,
        "because": because, "but": but, "so": so,
        "metrics": {}, "policy": {"use":"demo","share":"yes","train":"yes"},
        "stamp": {"issued_at": now_utc(), "digest_sha256": ""}
    }
    if extras: obj.update(extras)
    obj["stamp"]["digest_sha256"] = digest(obj)
    out = path or (RECEIPTS/"tuning.json")
    out.write_text(json.dumps(obj, indent=2))
    (ROOT/"docs/receipt.latest.json").write_text(json.dumps(obj, indent=2))

def main():
    style_old = read_style()
    last_sim  = read_last_sim()
    style_new = propose_style(style_old)

    sim = simulate_lane(LAW, style_new, ROOT/f"data/{LANE}/history.jsonl")
    verdict, reasons = judge(sim, last_sim)

    if verdict=="accepted":
        STYLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STYLE_PATH.write_text(json.dumps(style_new, indent=2))
        LAST_SIM_PATH.write_text(json.dumps(sim, indent=2))

    because = [
        f"lane: {LANE}",
        f"style_old: {json.dumps(style_old)}",
        f"style_new: {json.dumps(style_new)}",
        f"law: budget k={LAW['budget']['k']}, AMB={LAW['budget']['AMB']}, bend kappa_c={LAW['bend']['kappa_c']}",
        f"sim: {json.dumps(sim)}"
    ]
    write_receipt(
        title="Tuning Receipt",
        status="OK" if verdict=="accepted" else "ERROR",
        point="Shadow → judge by Canon → (maybe) adopt style",
        because=because,
        but="; ".join(reasons),
        so="adopted" if verdict=="accepted" else "rejected",
        extras={"metrics":{"law":sim["law"], "emergence":sim["emergence"]},"verdict":verdict}
    )
    (RECEIPTS/"canon.json").write_text((ROOT/"canon/law.json").read_text())

if __name__ == "__main__":
    main()
