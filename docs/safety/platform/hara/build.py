#!/usr/bin/env python3
"""Build the HARA workbook from hara.json and the item definition.

hara.json holds the analyst's judgments: the SC / NSC / NA classification and
hazard of every function x malfunction pair, safe states, the operating
envelope, and rating rules that override the generator's S / E / C heuristics
for specific hazards (each with its rationale). This script expands those rules
into the generator's per-row overrides, runs the HARA generator, and recalculates
the ASIL formulas.

Usage:
    python build.py <hara-builder scripts directory>
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ITEM_DEFINITION = os.path.join(HERE, "..", "item-definition", "item-definition.json")
OUTPUT = os.path.join(HERE, "LD-HARA-001_hara.xlsx")


def clean_copy(scripts_dir):
    """Copy the generator scripts to a temp dir, dropping trailing NUL padding
    that some installed copies carry (Python refuses to run source with NULs)."""
    work = tempfile.mkdtemp(prefix="hara_gen_")
    shutil.copytree(scripts_dir, work, dirs_exist_ok=True)
    for name in ("generate_hara.py", "recalc.py"):
        path = os.path.join(work, name)
        with open(path, "rb") as f:
            data = f.read()
        with open(path, "wb") as f:
            f.write(data.rstrip(b"\x00"))
    return work


def load_generator(scripts_dir):
    spec = importlib.util.spec_from_file_location("generate_hara", os.path.join(scripts_dir, "generate_hara.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sentence(text):
    """'Unintended lateral motion: ...' -> 'unintended lateral motion: ...' for 'Prevent <hazard>'."""
    return text[0].lower() + text[1:]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    scripts = clean_copy(sys.argv[1])
    gen = load_generator(scripts)
    with open(os.path.join(HERE, "hara.json"), encoding="utf-8") as f:
        src = json.load(f)
    with open(ITEM_DEFINITION, encoding="utf-8") as f:
        item_def = json.load(f)

    env = src["environments"]
    locations = [loc for loc in gen.DEFAULT_LOCATIONS if loc["code"] not in env["drop_locations"]]
    weather = [wx for wx in gen.DEFAULT_WEATHER if wx["code"] not in env["drop_weather"]]

    functions = []
    for fn in item_def["functions"]:
        functions.append({
            "id": fn["id"], "name": fn["name"], "description": fn["description"],
            "kinetic_authority": src["functions_kinetic_authority"][fn["id"]],
            "safe_state": src["safe_states"].get(fn["id"], ""),
        })

    ratings = []
    for pair in src["function_malfunction_ratings"]:
        row = dict(pair)
        hazard_id = row.pop("hazard")
        row["hazard_description"] = sentence(src["hazards"][hazard_id]) if hazard_id else ""
        if hazard_id:
            row["rationale"] = f"[{hazard_id}] {row['rationale']}"
            row["safe_state"] = src["safe_states"].get(pair["function_id"], "")
        ratings.append(row)

    overrides = {}
    for rule in src["rating_rules"]:
        for pair in src["function_malfunction_ratings"]:
            if pair["classification"] != "SC" or pair["hazard"] not in rule["hazards"]:
                continue
            for loc in locations:
                for wx in weather:
                    key = (pair["function_id"], pair["malfunction_id"], loc["code"], wx["code"])
                    ovr = overrides.setdefault(key, {
                        "function_id": key[0], "malfunction_id": key[1],
                        "location_code": key[2], "weather_code": key[3]})
                    value = rule["by_location"][loc["code"]] if "by_location" in rule else rule["value"]
                    ovr[rule["field"]] = value
                    ovr[rule["field"] + "_rationale"] = rule["rationale"]

    gen_input = {
        "item": src["item"],
        "scope_description": item_def["scope_description"],
        "boundary_diagram_notes": item_def["boundary"]["notes"],
        "assumptions": [{"id": a["id"], "category": a["category"], "assumption": a["assumption"]}
                        for a in item_def["assumptions"]] + [
            {"id": "A09", "category": "Scope", "assumption": env["rationale"]},
            {"id": "A10", "category": "Method", "assumption": "Hazards are rated without crediting the item's own safety mechanisms (the panda supervision, F05), as ISO 26262-3 requires. External measures in the vehicle (EPS self-limiting, stock emergency braking) are platform assumptions and are not credited either."}],
        "interfaces": [{"id": i["id"], "interface": i["interface"], "direction": i["direction"], "description": i["data"]}
                       for i in item_def["external_interfaces"]],
        "functions": functions,
        "environments": {"locations": locations, "weather": weather},
        "function_malfunction_ratings": ratings,
        "rating_overrides": list(overrides.values()),
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(gen_input, tmp)
    subprocess.run([sys.executable, os.path.join(scripts, "generate_hara.py"), tmp.name, OUTPUT], check=True)
    subprocess.run([sys.executable, os.path.join(scripts, "recalc.py"), OUTPUT], check=True)
    os.unlink(tmp.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
