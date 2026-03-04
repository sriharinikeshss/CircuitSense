"""
BOM CSV Parser for CircuitSense
Parses Bill of Materials CSV files into structured component data.
"""

import pandas as pd
import re


# Component category classification rules
CATEGORY_RULES = {
    "Voltage Regulator": [
        r"LM78\d+", r"LM317", r"AMS1117", r"LDO", r"regulator",
        r"LM1117", r"7805", r"7812", r"7833", r"TPS\d+", r"MCP\d+",
        r"AP\d+", r"XC\d+", r"RT\d+", r"MP\d+"
    ],
    "Capacitor": [
        r"^C\d+", r"capacitor", r"cap", r"\d+[unpf]F", r"\d+uF",
        r"\d+nF", r"\d+pF"
    ],
    "Resistor": [
        r"^R\d+", r"resistor", r"\bres\b", r"\d+[kKmM]?\s*ohm",
        r"\d+[kKmM]?Ω"
    ],
    "Crystal / Oscillator": [
        r"crystal", r"oscillator", r"^Y\d+", r"MHz", r"xtal"
    ],
    "Inductor": [
        r"^L\d+", r"inductor", r"choke", r"\d+[unm]H\b"
    ],
    "Diode": [
        r"^D\d+", r"diode", r"1N\d+", r"schottky", r"zener",
        r"LED", r"SS\d+", r"BAT\d+", r"TVS", r"SMBJ\d+", r"transient"
    ],
    "Transistor": [
        r"^Q\d+", r"MOSFET", r"BJT", r"2N\d+", r"IRF\d+",
        r"BSS\d+", r"BC\d+", r"2SC\d+"
    ],
    "IC / Microcontroller": [
        r"ATmega", r"STM32", r"PIC\d+", r"ESP\d+", r"MCU",
        r"^U\d+", r"\bIC\b", r"555", r"op.?amp", r"NE555"
    ],
    "Connector": [
        r"^J\d+", r"connector", r"header", r"USB", r"barrel",
        r"terminal", r"pin"
    ],

    "Fuse": [
        r"^F\d+", r"fuse", r"PTC", r"polyfuse"
    ],
    "Transformer": [
        r"^T\d+", r"transformer", r"xfmr"
    ]
}


def classify_component(ref_des: str, value: str, description: str = "") -> str:
    """Classify a component into a category based on reference designator, value, and description."""
    combined = f"{ref_des} {value} {description}"

    for category, patterns in CATEGORY_RULES.items():
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return category

    return "Other"


def estimate_power_relevance(category: str, value: str, description: str = "") -> str:
    """Estimate how relevant a component is to the power subsystem."""
    combined = (value + " " + description).lower()
    power_categories = {"Voltage Regulator", "Inductor", "Fuse", "Transformer"}
    if category in power_categories:
        return "HIGH"

    # Capacitors on power rails (typically larger values)
    if category == "Capacitor":
        value_lower = combined
        # Bulk caps (>=10uF) are usually power-related
        match = re.search(r'(\d+\.?\d*)\s*(uf|μf)', value_lower)
        if match:
            cap_val = float(match.group(1))
            if cap_val >= 10:
                return "HIGH"
            elif cap_val >= 1:
                return "MEDIUM"
        return "LOW"

    if category == "Diode":
        # Power diodes / Schottky are power-relevant
        if re.search(r"schottky|1N5\d+|SS\d+|power|TVS|SMBJ|transient", combined, re.IGNORECASE):
            return "HIGH"
        return "MEDIUM"

    if category == "Resistor":
        # High-power resistors
        if re.search(r"(\d+)\s*W", combined) or re.search(r"shunt|sense|current", combined, re.IGNORECASE):
            return "HIGH"
        return "LOW"

    return "LOW"


def parse_bom(file_or_path) -> dict:
    """
    Parse a BOM CSV file into structured component data.

    Args:
        file_or_path: Either a file path string or a file-like object (e.g., from Streamlit upload)

    Returns:
        dict with keys:
            - 'components': list of dicts with component details
            - 'summary': dict with category counts and stats
            - 'power_components': list of power-relevant components
            - 'risk_flags': list of identified risks
    """
    # Read CSV
    df = pd.read_csv(file_or_path)

    # Normalize column names (handle various BOM formats)
    col_map = {}
    for col in df.columns:
        col_lower = col.strip().lower()
        if col_lower in ["reference", "ref", "ref des", "reference designator", "designator"]:
            col_map[col] = "Reference"
        elif col_lower in ["value", "val"]:
            col_map[col] = "Value"
        elif col_lower in ["description", "desc", "part description"]:
            col_map[col] = "Description"
        elif col_lower in ["quantity", "qty", "count"]:
            col_map[col] = "Quantity"
        elif col_lower in ["package", "footprint", "pkg", "case"]:
            col_map[col] = "Package"
        elif col_lower in ["manufacturer", "mfr", "mfg"]:
            col_map[col] = "Manufacturer"
        elif col_lower in ["part number", "mpn", "mfr part", "manufacturer part"]:
            col_map[col] = "PartNumber"

    df = df.rename(columns=col_map)

    # Ensure required columns exist
    if "Reference" not in df.columns:
        # Try to use first column as reference
        df = df.rename(columns={df.columns[0]: "Reference"})
    if "Value" not in df.columns:
        if len(df.columns) > 1:
            df = df.rename(columns={df.columns[1]: "Value"})
        else:
            df["Value"] = ""

    # Fill missing columns
    for col in ["Description", "Quantity", "Package", "Manufacturer", "PartNumber"]:
        if col not in df.columns:
            df[col] = "" if col != "Quantity" else 1

    # Drop rows with empty reference
    df = df.dropna(subset=["Reference"])
    df["Value"] = df["Value"].fillna("").astype(str)
    df["Description"] = df["Description"].fillna("").astype(str)

    # Classify components
    components = []
    for _, row in df.iterrows():
        ref = str(row["Reference"]).strip()
        value = str(row["Value"]).strip()
        desc = str(row["Description"]).strip()

        category = classify_component(ref, value, desc)
        power_relevance = estimate_power_relevance(category, value, desc)

        # Safe quantity parsing
        try:
            qty = int(float(str(row.get("Quantity", 1)) or 1))
        except (ValueError, TypeError):
            qty = 1

        comp = {
            "reference": ref,
            "value": value,
            "description": desc,
            "quantity": qty,
            "package": str(row.get("Package", "")).strip(),
            "manufacturer": str(row.get("Manufacturer", "")).strip(),
            "part_number": str(row.get("PartNumber", "")).strip(),
            "category": category,
            "power_relevance": power_relevance,
        }
        components.append(comp)

    # Build summary using actual quantities
    category_counts = {}
    total_physical = 0
    power_critical_qty = 0
    
    for comp in components:
        cat = comp["category"]
        qty = comp["quantity"]
        category_counts[cat] = category_counts.get(cat, 0) + qty
        total_physical += qty
        if comp["power_relevance"] == "HIGH":
            power_critical_qty += qty

    power_components = [c for c in components if c["power_relevance"] == "HIGH"]
    medium_power = [c for c in components if c["power_relevance"] == "MEDIUM"]

    # Generate risk flags
    risk_flags = _generate_risk_flags(components, category_counts)

    return {
        "components": components,
        "summary": {
            "total_line_items": len(components),
            "total_components": total_physical,
            "category_counts": category_counts,
            "power_critical_count": power_critical_qty,
            "categories": list(category_counts.keys()),
        },
        "power_components": power_components,
        "medium_power_components": medium_power,
        "risk_flags": risk_flags,
    }


def _generate_risk_flags(components: list, category_counts: dict) -> list:
    """Generate risk flags based on BOM analysis."""
    flags = []

    # Check for voltage regulators without nearby decoupling caps
    regulators = [c for c in components if c["category"] == "Voltage Regulator"]
    bulk_caps = [c for c in components if c["category"] == "Capacitor" and c["power_relevance"] == "HIGH"]

    reg_qty = sum(r["quantity"] for r in regulators)
    cap_qty = sum(c["quantity"] for c in bulk_caps)

    if reg_qty > 0 and cap_qty < reg_qty:
        flags.append({
            "severity": "HIGH",
            "type": "DECOUPLING",
            "message": f"Found {reg_qty} voltage regulator(s) but only {cap_qty} bulk capacitor(s). Each regulator typically needs input and output capacitors.",
            "source": "🔧 Rule-based",
            "components": [r["reference"] for r in regulators],
        })

    # Check for missing fuse protection
    if regulators and "Fuse" not in category_counts:
        flags.append({
            "severity": "MEDIUM",
            "type": "PROTECTION",
            "message": "No fuse found in BOM. Power input should have overcurrent protection.",
            "source": "🔧 Rule-based",
            "components": [],
        })

    # Check for high component count without test points
    total_qty = sum(c["quantity"] for c in components)
    if total_qty > 20 and "Connector" not in category_counts:
        flags.append({
            "severity": "LOW",
            "type": "TESTABILITY",
            "message": "Board has many components but no connectors/test points listed. Consider adding test access points.",
            "source": "🔧 Rule-based",
            "components": [],
        })

    # Flag power components that need careful testing
    for reg in regulators:
        flags.append({
            "severity": "INFO",
            "type": "POWER_TEST",
            "message": f"Voltage regulator {reg['reference']} ({reg['value']}) — test output voltage, ripple, load regulation, and thermal performance.",
            "source": "🔧 Rule-based",
            "components": [reg["reference"]],
        })

    return flags
