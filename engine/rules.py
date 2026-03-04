"""
Electronics Rule Engine for CircuitSense
Power-first heuristic analysis, component stress checks, and engineering reasoning.
"""

import re


def analyze_board(parsed_bom: dict) -> dict:
    """
    Run full engineering analysis on a parsed BOM.

    Returns dict with:
        - power_analysis: Power subsystem assessment
        - stress_checks: Component stress flags
        - test_priorities: Ordered list of what to test first
        - engineering_notes: Domain-specific observations
    """
    components = parsed_bom["components"]
    risk_flags = parsed_bom["risk_flags"]

    power_analysis = _analyze_power_subsystem(components)
    stress_checks = _check_component_stress(components)
    test_priorities = _generate_test_priorities(components, power_analysis, risk_flags)
    engineering_notes = _generate_engineering_notes(components, parsed_bom["summary"])
    impactful_components = _get_impactful_components(components)
    
    # Calculate composite risk
    power_risk = power_analysis["risk_level"]
    flag_severities = [f["severity"] for f in risk_flags]
    all_risks = [power_risk] + flag_severities
    
    if "HIGH" in all_risks:
        composite_risk = "HIGH"
    elif "MEDIUM" in all_risks:
        composite_risk = "MEDIUM"
    else:
        composite_risk = "LOW"
        
    top_action = "Review board power up sequence."
    if test_priorities:
        top_action = test_priorities[0]["area"].split("—")[0].strip()

    return {
        "power_analysis": power_analysis,
        "stress_checks": stress_checks,
        "test_priorities": test_priorities,
        "engineering_notes": engineering_notes,
        "composite_risk": composite_risk,
        "top_action": top_action,
        "impactful_components": impactful_components
    }


def _analyze_power_subsystem(components: list) -> dict:
    """Analyze the power subsystem — this runs FIRST (power-first logic)."""
    regulators = [c for c in components if c["category"] == "Voltage Regulator"]
    power_caps = [c for c in components if c["category"] == "Capacitor" and c["power_relevance"] == "HIGH"]
    inductors = [c for c in components if c["category"] == "Inductor"]
    power_diodes = [c for c in components if c["category"] == "Diode" and c["power_relevance"] in ("HIGH", "MEDIUM")]
    fuses = [c for c in components if c["category"] == "Fuse"]

    # Determine power topology with keyword heuristics
    topology = "Unknown"
    
    linear_keywords = ["linear", "ldo", "78", "79", "lm78", "lm79", "adjustable linear"]
    switch_keywords = ["buck", "boost", "switch", "dc-dc", "lm2596", "mp1584", "step-down", "step-up"]
    
    is_explicit_linear = False
    is_explicit_switch = False
    
    for reg in regulators:
        reg_text = (reg.get("value", "") + " " + reg.get("description", "")).lower()
        if any(kw in reg_text for kw in linear_keywords):
            is_explicit_linear = True
        if any(kw in reg_text for kw in switch_keywords):
            is_explicit_switch = True
            
    if is_explicit_linear and not is_explicit_switch:
        topology = "Linear regulation (LDO/linear regulator)"
    elif is_explicit_switch:
        topology = "Switching regulation (buck/boost converter)"
    elif regulators and not inductors:
        topology = "Linear regulation (LDO/linear regulator)"
    elif regulators and inductors:
        topology = "Switching regulation (buck/boost converter)"
    elif inductors and not regulators:
        topology = "Possible switching/filter topology"

    # Power chain analysis
    power_chain = []
    if fuses:
        power_chain.append({"stage": "Input Protection", "components": [f["reference"] for f in fuses], "status": "✅ Present"})
    else:
        power_chain.append({"stage": "Input Protection", "components": [], "status": "⚠️ Missing fuse/PTC"})

    if power_diodes:
        power_chain.append({"stage": "Reverse Polarity / Rectification", "components": [d["reference"] for d in power_diodes], "status": "✅ Present"})

    if regulators:
        for reg in regulators:
            power_chain.append({
                "stage": f"Regulation ({reg['value']})",
                "components": [reg["reference"]],
                "status": "✅ Present — needs voltage/ripple/load testing"
            })

    if power_caps:
        power_chain.append({"stage": "Decoupling / Filtering", "components": [c["reference"] for c in power_caps], "status": "✅ Present"})
    else:
        power_chain.append({"stage": "Decoupling / Filtering", "components": [], "status": "⚠️ No bulk capacitors found"})

    return {
        "topology": topology,
        "regulator_count": len(regulators),
        "regulators": [{"ref": r["reference"], "value": r["value"]} for r in regulators],
        "power_chain": power_chain,
        "has_input_protection": len(fuses) > 0 or any(
            re.search(r"TVS|SMBJ|transient|surge|clamp", c.get("value", "") + " " + c.get("description", ""), re.IGNORECASE)
            for c in power_diodes
        ),
        "has_decoupling": len(power_caps) > 0,
        "risk_level": "HIGH" if (not fuses and not power_diodes) or not power_caps else ("MEDIUM" if sum(c["quantity"] for c in power_caps) < sum(c["quantity"] for c in regulators) * 2 else "LOW"),
    }


def _check_component_stress(components: list) -> list:
    """Check for potential component stress issues."""
    stress_flags = []

    # Check capacitor types in power applications
    for comp in components:
        if comp["category"] == "Capacitor" and comp["power_relevance"] == "HIGH":
            combined_text = (comp["value"] + " " + comp.get("description", "")).lower()
            # Electrolytic caps degrade faster
            if any(term in combined_text for term in ["electrolytic", "elec", "e-cap"]):
                stress_flags.append({
                    "component": comp["reference"],
                    "issue": "Electrolytic capacitor in power path — check ESR and temperature rating",
                    "recommendation": "Verify capacitor ESR meets regulator stability requirements. Consider polymer or ceramic alternatives for longer life.",
                    "severity": "MEDIUM",
                    "source": "🔧 Rule-based",
                })

        # Check for generic/unmarked components
        if comp["value"] in ["", "N/A", "n/a", "NA", "-"]:
            stress_flags.append({
                "component": comp["reference"],
                "issue": f"Component {comp['reference']} has no value specified",
                "recommendation": "Verify BOM is complete. Missing values can lead to incorrect test limits.",
                "severity": "LOW",
                "source": "🔧 Rule-based",
            })

    return stress_flags


def _generate_test_priorities(components: list, power_analysis: dict, risk_flags: list) -> list:
    """
    Generate ordered test priorities using POWER-FIRST logic.
    Priorities adapt dynamically based on:
    - Power topology (linear vs switching)
    - Risk level (HIGH → fault-seeking, LOW → verification)
    - Protection presence
    - Component specifics
    """
    priorities = []
    risk = power_analysis["risk_level"]
    topology = power_analysis["topology"]
    is_switching = "switching" in topology.lower()
    is_linear = "linear" in topology.lower()
    has_protection = power_analysis["has_input_protection"]
    has_decoupling = power_analysis["has_decoupling"]
    regulators = power_analysis.get("regulators", [])
    reg_names = ", ".join(f"{r['ref']} ({r['value']})" for r in regulators) if regulators else "unknown"

    # ─── PRIORITY 1: Power Rails (always first, but tone & tests change) ───

    if risk == "HIGH":
        # HIGH risk → fault-seeking, urgent
        p1_icon = "🔴"
        p1_label = "Failure Mode: Load-dependent regulation instability or failure"
        p1_reason = (
            f"Power risk is HIGH. Regulators: {reg_names}. "
            f"Topology: {topology}. "
            "Missing protection or insufficient decoupling detected. "
            "Test aggressively for output accuracy, thermal stress, and dropout before anything else."
        )
        if is_linear:
            p1_tests = [
                f"Measure DC output voltage at {reg_names} — expect ±5% of nominal, flag any drift",
                "Measure input-to-output voltage differential (dropout margin) — linear regulators fail when Vin-Vout is too low",
                "Check regulator case temperature after 5 min at full load — overheating is the #1 failure mode for linear regulators",
                "Measure ripple with oscilloscope (AC coupling, 20MHz BW limit) — high ripple suggests failing or missing output cap",
                "Load step test: 50% → 100% load — watch for output sag or oscillation",
            ]
            p1_pass = "Output within ±5% of nominal, dropout margin > 2V, case temp < 80°C, ripple < 50mV pp"
        else:
            p1_tests = [
                f"Measure DC output voltage at {reg_names} — must be within ±3% for switching regulators",
                "Check switching ripple at output with oscilloscope (full bandwidth, 10x probe, short ground lead)",
                "Measure input current at no-load and full load — excessive no-load current suggests controller fault",
                "Verify inductor is not saturating under load (listen for audible whine, check current waveform)",
                "Load step test: 50% → 100% — switching regulators can show transient overshoot",
            ]
            p1_pass = "Output within ±3% of nominal, ripple < 30mV pp, no audible noise, clean transient response"

    elif risk == "MEDIUM":
        # MEDIUM risk → cautious verification
        p1_icon = "🟡"
        p1_label = "Failure Mode: Marginal power stability under transient loads"
        p1_reason = (
            f"Power topology: {topology}. Regulators: {reg_names}. "
            "Design has some protection but decoupling may be insufficient. "
            "Verify power output stability and confirm protection elements work as expected."
        )
        if is_switching:
            p1_tests = [
                f"Verify DC output voltage at {reg_names} — confirm within ±3% specification",
                "Measure switching ripple at output — switching designs need clean output filtering",
                "Test load regulation: measure voltage at 25%, 50%, 75%, 100% load",
                "Verify input protection activates correctly (if fuse present, confirm it trips at rated current)",
                "Check efficiency: measure input power vs output power",
            ]
            p1_pass = "Output within ±3%, ripple < 30mV pp, load regulation < 2%, efficiency > 80%"
        else:
            p1_tests = [
                f"Verify DC output voltage at {reg_names} — confirm within ±5% specification",
                "Measure ripple/noise (AC coupling, 20MHz BW limit)",
                "Test load regulation from 10% to full load",
                "Monitor regulator temperature over 15 minutes at full load",
            ]
            p1_pass = "Output within ±5%, ripple < 50mV pp, temp < 70°C at full load"

    else:
        # LOW risk → confident verification
        p1_icon = "🟢"
        p1_label = "Performance Validation: Nominal power delivery"
        p1_reason = (
            f"Power design looks solid. Topology: {topology}. Regulators: {reg_names}. "
            "Protection and decoupling are present. "
            "Focus on confirming datasheet specifications and characterizing performance margins."
        )
        if is_switching:
            p1_tests = [
                f"Confirm output voltage at {reg_names} matches datasheet nominal (±1% for precision)",
                "Characterize load transient response: 10% → 90% load step, measure recovery time",
                "Measure power efficiency across load range (25%, 50%, 75%, 100%)",
                "Check EMI/switching noise — probe near inductor and switching node",
                "Verify soft-start behavior on power-up",
            ]
            p1_pass = "Datasheet specs met, transient recovery < 100µs, efficiency > 85%, no EMI issues"
        else:
            p1_tests = [
                f"Confirm output voltage at {reg_names} matches datasheet nominal",
                "Characterize dropout voltage — reduce input gradually until output drops",
                "Measure line regulation: vary input ±10% and measure output stability",
                "Verify output noise floor with oscilloscope at full bandwidth",
            ]
            p1_pass = "Datasheet specs met, line regulation < 0.5%, noise floor < 20mV pp"

    priorities.append({
        "priority": 1,
        "area": p1_label,
        "reason": p1_reason,
        "tests": p1_tests,
        "instruments": "DMM (DC voltage), Oscilloscope (ripple/transient), Electronic load (load regulation)",
        "pass_criteria": p1_pass,
        "source": f"🔧 Rule-based (power-first • {topology.split('(')[0].strip()} • risk={risk})",
    })

    # ─── PRIORITY 2: Input Protection ─────────────────────────────────

    pnum = 2
    if not has_protection:
        priorities.append({
            "priority": pnum,
            "area": "Failure Mode: Catastrophic damage from overcurrent/reverse polarity",
            "reason": "No fuse, PTC, or TVS found in BOM. This is a significant design gap — overcurrent or reverse polarity could damage the entire board. Test behavior under fault conditions.",
            "tests": [
                "Slowly ramp input current beyond expected max — observe for smoke, component damage",
                "If possible, apply reverse polarity briefly — check for damage",
                "Monitor all component temperatures under sustained max load (identify thermal weak points)",
                "Measure short-circuit behavior at output — does anything limit current?",
            ],
            "instruments": "Current-limited power supply, thermal camera/thermocouple, DMM",
            "pass_criteria": "No damage at 120% rated current, no thermal runaway, graceful behavior under fault",
            "source": "🔧 Rule-based (missing input protection)",
        })
        pnum += 1
    else:
        priorities.append({
            "priority": pnum,
            "area": "System Check: Protection threshold verification",
            "reason": "Protection components are present. Confirm they activate correctly at rated thresholds.",
            "tests": [
                "Verify fuse/PTC trips at rated overcurrent (ramp current slowly past rating)",
                "Confirm TVS/Zener clamps voltage at expected level (if present)",
                "Test recovery after overcurrent event (PTC should reset, fuse should open)",
            ],
            "instruments": "Current-limited power supply, oscilloscope (for clamp voltage), DMM",
            "pass_criteria": "Protection activates within ±15% of rated value, resets correctly (if resettable)",
            "source": "🔧 Rule-based (protection verification)",
        })
        pnum += 1

    # ─── PRIORITY 3: Decoupling & Filtering ───────────────────────────

    if not has_decoupling:
        priorities.append({
            "priority": pnum,
            "area": "Failure Mode: High-frequency oscillation and dropout",
            "reason": "Bulk decoupling capacitors are missing or insufficient. This can cause oscillation, noise, and intermittent failures especially under transient loads.",
            "tests": [
                "Probe regulator output with oscilloscope at full bandwidth — look for oscillation",
                "Apply fast load transient — check for output ringing or instability",
                "Temporarily add external capacitor at output — does stability improve? (diagnostic test)",
            ],
            "instruments": "Oscilloscope (full BW, short probe ground), function generator for load transient",
            "pass_criteria": "No oscillation, no ringing after transient, stable output under all conditions",
            "source": "🔧 Rule-based (insufficient decoupling)",
        })
    else:
        priorities.append({
            "priority": pnum,
            "area": "System Check: Noise floor and ripple rejection",
            "reason": "Decoupling capacitors are present. Verify they effectively suppress noise and maintain stability across operating conditions.",
            "tests": [
                "Measure high-frequency noise at regulator outputs (use close probe loop, minimal ground lead)",
                "Check for oscillation at regulator output under varying loads (no-load to full-load sweep)",
            ],
            "instruments": "Oscilloscope with 10x probe, close to regulator output pin",
            "pass_criteria": "No oscillation, HF noise < 10mV pp",
            "source": "🔧 Rule-based (decoupling verification)",
        })
    pnum += 1

    # ─── PRIORITY 4: Signal Integrity (if ICs present) ────────────────

    ics = [c for c in components if c["category"] == "IC / Microcontroller"]
    crystals = [c for c in components if c["category"] == "Crystal / Oscillator"]

    if ics:
        ic_names = ", ".join(f"{ic['reference']} ({ic['value']})" for ic in ics)
        crystal_note = ""
        if crystals:
            crystal_names = ", ".join(f"{y['reference']} ({y['value']})" for y in crystals)
            crystal_note = f" Crystal/oscillator present: {crystal_names}."

        priorities.append({
            "priority": pnum,
            "area": "Signal Integrity / Digital",
            "reason": f"Found {len(ics)} IC(s): {ic_names}.{crystal_note} Verify clock stability, reset behavior, and communication buses after power is confirmed good.",
            "tests": [
                f"Verify clock signal at {crystals[0]['reference']} ({crystals[0]['value']}) — check frequency accuracy and amplitude" if crystals else "Verify clock source frequency and amplitude",
                "Check reset pin behavior during power-on — must stay low for sufficient time",
                "If I2C/SPI present: verify bus signal levels and pull-up adequacy",
                "Monitor power pins of each IC with oscilloscope — ensure clean supply at IC VCC",
            ],
            "instruments": "Oscilloscope, logic analyzer (for bus protocols)",
            "pass_criteria": "Clock within ±50ppm, reset hold time > 10ms, bus signals at correct logic levels",
            "source": "🔧 Rule-based (IC-specific)",
        })
        pnum += 1

    # ─── PRIORITY 5: Thermal Analysis ─────────────────────────────────

    if is_linear:
        thermal_reason = (
            "Linear regulators dissipate excess voltage as heat (P = (Vin - Vout) × Iload). "
            "This is the PRIMARY failure mechanism for linear designs. Extended thermal testing is critical."
        )
        thermal_tests = [
            "Run board at full load for 30+ minutes — linear regulators accumulate heat",
            f"Monitor {reg_names} temperature every 5 minutes — plot thermal curve",
            "Calculate power dissipation: P = (Vin - Vout) × I_load — compare to package rating",
            "Check for thermal shutdown cycling (output drops then recovers periodically)",
            "If temp > 85°C, consider adding heatsink and retest",
        ]
        thermal_pass = "Thermal equilibrium < 100°C (TO-220) or < 125°C (SMD), no shutdown cycling, no drift > 1%"
        thermal_severity = "🔴" if is_linear and risk == "HIGH" else "🟡"
    else:
        thermal_reason = (
            "Switching regulators are more efficient but can still overheat at high loads. "
            "Check inductor, switching FET, and diode temperatures."
        )
        thermal_tests = [
            "Run board at full load for 15 minutes",
            "Monitor inductor, regulator IC, and catch diode temperatures",
            "Check efficiency — low efficiency means more thermal dissipation",
            "Look for thermal-induced frequency shift in switching waveform",
        ]
        thermal_pass = "All components < rated temperature, efficiency stable, no frequency drift"
        thermal_severity = "🟡"

    priorities.append({
        "priority": pnum,
        "area": "Thermal Analysis",
        "reason": thermal_reason,
        "tests": thermal_tests,
        "instruments": "Thermal camera / IR thermometer, DMM for voltage drift monitoring, timer",
        "pass_criteria": thermal_pass,
        "source": f"🔧 Rule-based (thermal • {'linear dissipation risk' if is_linear else 'switching efficiency check'})",
    })

    return priorities


def _generate_engineering_notes(components: list, summary: dict) -> list:
    """Generate domain-specific engineering observations."""
    notes = []

    total = summary["total_components"]
    cats = summary["category_counts"]

    notes.append({
        "note": f"Board has {total} components across {len(cats)} categories.",
        "source": "🔧 Rule-based",
    })

    # Component ratio analysis
    cap_count = cats.get("Capacitor", 0)
    res_count = cats.get("Resistor", 0)
    ic_count = cats.get("IC / Microcontroller", 0)

    if ic_count > 0 and cap_count < ic_count * 2:
        notes.append({
            "note": f"Low capacitor-to-IC ratio ({cap_count} caps for {ic_count} ICs). Each IC typically needs at least 1-2 bypass caps. Check decoupling.",
            "source": "🔧 Rule-based",
        })

    if ic_count > 0:
        notes.append({
            "note": f"Found {ic_count} IC(s). Each requires power pin bypass cap verification and proper reset/clock signals.",
            "source": "🔧 Rule-based",
        })

    reg_count = cats.get("Voltage Regulator", 0)
    if reg_count > 1:
        notes.append({
            "note": f"Multiple regulators ({reg_count}) suggest multiple power domains. Test each domain independently before testing cross-domain signals.",
            "source": "🔧 Rule-based (power-first)",
        })

    return notes


def get_context_for_ai(parsed_bom: dict, analysis: dict) -> str:
    """
    Generate a text context string summarizing the board analysis,
    to be injected into Mistral AI prompts.
    """
    ctx_parts = []

    # Board overview
    s = parsed_bom["summary"]
    ctx_parts.append(f"BOARD SUMMARY: {s['total_components']} components, {s['power_critical_count']} power-critical.")
    ctx_parts.append(f"Categories: {', '.join(f'{k}: {v}' for k, v in s['category_counts'].items())}")

    # Power topology
    pa = analysis["power_analysis"]
    ctx_parts.append(f"\nPOWER TOPOLOGY: {pa['topology']}")
    ctx_parts.append(f"Regulators: {', '.join(r['ref'] + ' (' + r['value'] + ')' for r in pa['regulators'])}")
    ctx_parts.append(f"Input protection: {'Present' if pa['has_input_protection'] else 'MISSING'}")
    ctx_parts.append(f"Decoupling: {'Present' if pa['has_decoupling'] else 'MISSING/INSUFFICIENT'}")
    ctx_parts.append(f"Power risk level: {pa['risk_level']}")

    # Risk flags
    if parsed_bom["risk_flags"]:
        ctx_parts.append(f"\nRISK FLAGS ({len(parsed_bom['risk_flags'])}):")
        for flag in parsed_bom["risk_flags"]:
            ctx_parts.append(f"  [{flag['severity']}] {flag['message']}")

    # Stress checks
    if analysis["stress_checks"]:
        ctx_parts.append(f"\nSTRESS CHECKS ({len(analysis['stress_checks'])}):")
        for sc in analysis["stress_checks"]:
            ctx_parts.append(f"  {sc['component']}: {sc['issue']}")

    return "\n".join(ctx_parts)


def _get_impactful_components(components: list) -> list:
    """
    Calculate component impact scores: power_relevance_multiplier * quantity.
    Returns the top 3 components to focus on during bench testing.
    """
    impact_scores = []
    relevance_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    
    for c in components:
        # Ignore generic categories or tiny jellybean parts without specific power relevance
        if c["category"] in ["Resistor", "Other"] and c["power_relevance"] == "LOW":
            continue
            
        weight = relevance_weights.get(c["power_relevance"], 1)
        score = weight * c.get("quantity", 1)
        
        impact_scores.append({
            "reference": c["reference"],
            "value": c["value"],
            "category": c["category"],
            "score": score
        })
        
    # Sort descending by score, take top 3
    impact_scores.sort(key=lambda x: x["score"], reverse=True)
    return impact_scores[:3]
