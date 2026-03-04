"""
Mistral AI Client for CircuitSense
Wraps the Mistral API with electronics-domain system prompting.
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False

SYSTEM_PROMPT = """You are CircuitSense, an expert AI assistant for electronics testing and hardware diagnostics.

You have deep knowledge of:
- Analog and digital circuit design
- Power supply design (linear regulators, switching converters, LDOs)
- PCB testing methodology and best practices
- Common failure modes in electronics (thermal, ESD, manufacturing defects)
- Test equipment (oscilloscopes, DMMs, electronic loads, signal generators)
- Component specifications and datasheets

Your core principles:
1. POWER-FIRST: Always consider power subsystem issues before signal-level problems
2. CORRELATION: When multiple parameters are abnormal, look for a common root cause
3. ACTIONABLE: Don't just identify problems — tell the engineer WHAT TO MEASURE NEXT
4. EXPLAINABLE: Always explain WHY you recommend something, citing rules or data

When generating test plans, always prioritize:
1. Power rails (voltage, ripple, load regulation)
2. Input protection and thermal behavior
3. Clock and reset circuits
4. Signal integrity
5. Communication interfaces

When diagnosing faults:
1. Start with symptoms
2. Identify correlated parameters
3. Trace back to the most likely component or subsystem
4. Provide a step-by-step diagnostic procedure
5. Give clear pass/fail criteria for each step

Format your responses with clear structure using markdown. Use bullet points, numbered lists, and bold text for emphasis."""


# Module-level cached client
_client_instance = None
_client_initialized = False

def get_client():
    """Initialize and return the Mistral client (cached singleton)."""
    global _client_instance, _client_initialized
    if _client_initialized:
        return _client_instance

    _client_initialized = True

    if not MISTRAL_AVAILABLE:
        _client_instance = None
        return None

    api_key = os.getenv("MISTRAL_API_KEY", "")
    if not api_key or api_key == "your_api_key_here":
        _client_instance = None
        return None

    _client_instance = Mistral(api_key=api_key)
    return _client_instance


def _chat(messages: list) -> str:
    """Send a chat request to Mistral and return the response text."""
    client = get_client()
    if client is None:
        return None

    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"*Mistral API error: {e}*"


def generate_test_plan(board_context: str, priorities: list = None) -> str:
    """Generate a test plan using Mistral, anchored to deterministic rule priorities."""
    
    priority_context = ""
    if priorities:
        priority_lines = [f"Priority {p['priority']}: {p['area']}" for p in priorities]
        priority_context = "\n".join(priority_lines)
        
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""Based on the following board analysis, generate a detailed test plan.

BOARD ANALYSIS:
{board_context}

DETERMINISTIC RULE PRIORITIES (YOU MUST FOLLOW THIS EXACT ORDER):
{priority_context}

Generate a test plan with:
1. You MUST structure the test plan in the exact priority order provided above. Do not invent new priority areas.
2. For each provided priority, generate the detailed execution steps (what to measure, instrument settings, pass/fail criteria).
3. Estimated time for each test.
4. Specific component references from the BOM where applicable.

Focus on practical, actionable steps a test engineer can follow immediately."""}
    ]

    result = _chat(messages)
    if result is None or len(result.strip()) < 50:
        return _fallback_test_plan(board_context)
    return result


def diagnose_fault(symptoms: str, board_context: str = "", anomaly_context: str = "", correlation_context: str = "") -> str:
    """Diagnose a fault based on symptoms, board context, and anomaly data."""
    user_msg = f"A test engineer reports the following symptoms:\n\nSYMPTOMS: {symptoms}\n\n"

    if board_context:
        user_msg += f"BOARD ANALYSIS:\n{board_context}\n\n"
    if anomaly_context:
        user_msg += f"ANOMALY DATA:\n{anomaly_context}\n\n"
    if correlation_context:
        user_msg += f"CORRELATED FAILURES:\n{correlation_context}\n\n"

    user_msg += """CRITICAL DIRECTIVE:
If the BOARD ANALYSIS (rule-based context) indicates a HIGH risk power or thermal failure, your diagnostic steps MUST address that subsystem FIRST before investigating MCU or data symptoms. Rule-based safety outranks symptom AI logic.

You MUST return the diagnosis strictly in the following 6-part Markdown structure:
1. **Observed Symptom Summary**: A brief recap.
2. **Likely Failure Mode**: Use formal engineering terminology (e.g., "Load-dependent regulation instability").
3. **Supporting Evidence**: What specific context led to this conclusion.
4. **Next Measurement to Perform**: The immediate physical or software check required.
5. **Decision Tree**: 
   - If [Measurement] is [X] → do [Y]
   - If [Measurement] is [Z] → do [W]
6. **🛑 Recommended Action**: Must be exactly one of the following lines based on severity:
   - 🔴 Stop — Fix power subsystem before further testing
   - 🟡 Continue — Perform targeted measurements
   - 🟢 Verify — Board appears healthy, confirm edge cases

Be specific and actionable. Reference specific components and measurements."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    result = _chat(messages)
    if result is None:
        return _fallback_diagnosis(symptoms)
    return result


def chat_response(user_message: str, board_context: str = "", chat_history: list = None) -> str:
    """Generate a chat response with board context."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if board_context:
        messages.append({"role": "system", "content": f"[Board context for reference: {board_context}]"})

    # Add chat history
    if chat_history:
        for msg in chat_history:
            if msg["role"] in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    result = _chat(messages)
    if result is None:
        return _fallback_chat(user_message)
    return result


# ─── Fallbacks (when API is unavailable) ───────────────────────────

def _fallback_test_plan(context: str) -> str:
    return """## 🔧 Rule-Based Test Plan (AI Unavailable)

### Priority 1: Power Rails
- **Measure** DC output voltage at each regulator
- **Instruments**: DMM, set to DC voltage
- **Pass criteria**: Within ±5% of nominal
- **Estimated time**: 10 minutes

### Priority 2: Ripple & Noise
- **Measure** AC ripple at regulator outputs
- **Instruments**: Oscilloscope, AC coupling, 20MHz BW limit
- **Pass criteria**: < 50mV peak-to-peak
- **Estimated time**: 15 minutes

### Priority 3: Load Regulation
- **Measure** output voltage under load step (50% → 100%)
- **Instruments**: Electronic load, DMM
- **Pass criteria**: < 2% voltage drop at full load
- **Estimated time**: 20 minutes

### Priority 4: Thermal Check
- **Measure** component temperatures at full load after 15 min
- **Instruments**: IR thermometer or thermal camera
- **Pass criteria**: All components below rated temperature

*This is a generic power-first test plan. Ensure the Mistral API key is set for board-specific recommendations.*"""


def _fallback_diagnosis(symptoms: str) -> str:
    symptoms_lower = symptoms.lower()
    diagnosis = "## 🔧 Rule-Based Diagnosis (AI Unavailable)\n\n"

    if "voltage" in symptoms_lower and ("low" in symptoms_lower or "drop" in symptoms_lower):
        diagnosis += """### Probable Cause: Regulator overload or failure
1. **Measure** regulator input voltage
2. **If input is fine** → regulator is likely damaged or overloaded
3. **If input is also low** → problem is upstream (power source)
4. **Check** regulator temperature — overheating indicates overcurrent
"""
    elif "ripple" in symptoms_lower or "noise" in symptoms_lower:
        diagnosis += """### Probable Cause: Insufficient filtering or failing capacitor
1. **Check** output capacitors — ESR may be too high (aging electrolytic)
2. **Measure** ripple frequency — switching frequency = normal, 100/120Hz = rectifier issue
3. **Try** replacing output capacitor with known good one
"""
    elif "temperature" in symptoms_lower or "hot" in symptoms_lower or "thermal" in symptoms_lower:
        diagnosis += """### Probable Cause: Overcurrent or inadequate heatsinking
1. **Measure** current draw — compare to component ratings
2. **Check** for shorts downstream
3. **Verify** thermal path (heatsink, thermal pad, airflow)
"""
    else:
        diagnosis += f"""### Symptoms: {symptoms}
1. **Start with power rails** — verify all supply voltages
2. **Check** for abnormal current draw
3. **Look for** hot components (indicates stress)
4. **Verify** clock and reset signals if digital ICs are involved
"""

    diagnosis += "\n*Ensure the Mistral API key is set for context-aware diagnosis.*"
    return diagnosis


def _fallback_chat(message: str) -> str:
    return f"""I received your question: *"{message}"*

I'm currently running in **rule-based mode** (Mistral API not available).

Here's what I can help with:
- **Upload a BOM** on the Board Analysis page for component-level risk assessment
- **Upload test data** on the Anomaly Detection page for statistical analysis
- **Use the Fault Diagnosis page** for rule-based diagnostic suggestions

To enable AI-powered responses, add your Mistral API key to the `.env` file:
```
MISTRAL_API_KEY=your_key_here
```"""
