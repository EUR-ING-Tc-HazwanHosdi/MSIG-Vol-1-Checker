import streamlit as st

# ===============================
# MSIG ENGINE v8 CONFIG CORE
# ===============================

st.set_page_config(page_title="MSIG Compliance Engine v8", layout="wide")

# ===============================
# SCORING ENGINE
# ===============================

def risk_engine(score):
    if score >= 85:
        return "LOW", "🟢"
    elif score >= 70:
        return "MEDIUM", "🟡"
    elif score >= 50:
        return "HIGH", "🟠"
    else:
        return "CRITICAL", "🔴"


def clamp_score(score):
    return max(0, min(100, score))


# ===============================
# VOL 1 - PLANNING CHECKS
# ===============================

def vol1_check(data):
    score = 100
    issues = []
    warnings = []
    rec = []

    pe = data["pe"]
    land = data["land"]

    # RULE 1: PE check
    if pe > 1000:
        score -= 25
        issues.append("High Population Equivalent (>1000)")

    elif pe < 50:
        warnings.append("Very low PE - verify classification")

    # RULE 2: Land adequacy
    if land < pe * 0.5:
        score -= 20
        issues.append("Insufficient land area for development density")

    # RULE 3: basic planning sanity
    if land <= 0:
        score = 0
        issues.append("Missing land area")

    return clamp_score(score), issues, warnings, rec


# ===============================
# VOL 3 - SEWER & PUMP CHECKS
# ===============================

def vol3_check(data):
    score = 100
    issues = []
    warnings = []
    rec = []

    pe = data["pe"]
    flow = data["flow"]
    dia = data["diameter"]
    slope = data["slope"]

    # FLOW consistency
    if flow <= 0:
        score -= 40
        issues.append("Invalid flow calculation")

    # PIPE DIAMETER CHECK
    if dia < 150:
        score -= 25
        issues.append("Pipe diameter too small (<150mm)")

    # SLOPE CHECK
    if slope < 0.005:
        score -= 20
        warnings.append("Slope may be too low for self-cleansing velocity")

    # PE vs flow sanity
    expected_flow = pe * 0.21  # simplified rule
    if abs(flow - expected_flow) / max(expected_flow, 1) > 0.5:
        score -= 15
        warnings.append("Flow vs PE inconsistency detected")

    return clamp_score(score), issues, warnings, rec


# ===============================
# VOL 4 - STP CHECKS
# ===============================

def vol4_check(data):
    score = 100
    issues = []
    warnings = []
    rec = []

    pe = data["pe"]
    stp = data["stp_capacity"]

    if stp <= 0:
        score -= 50
        issues.append("Missing STP capacity")

    if stp < pe:
        score -= 30
        issues.append("STP undersized for PE demand")

    if stp > pe * 2:
        warnings.append("STP may be overdesigned")

    return clamp_score(score), issues, warnings, rec


# ===============================
# UI HEADER
# ===============================

st.title("🛡️ MSIG Compliance Engine v8 (Rule-Based)")

tab1, tab2, tab3 = st.tabs([
    "📘 Vol 1 Planning",
    "📗 Vol 3 Sewer & Pump",
    "📕 Vol 4 STP"
])

# ===============================
# VOL 1 UI
# ===============================

with tab1:
    st.subheader("Vol 1 - Planning Submission Check")

    pe = st.number_input("Population Equivalent (PE)", 0, 100000, 100)
    land = st.number_input("Land Area (m²)", 0.0, 100000.0, 500.0)

    if st.button("Run Vol 1 Check"):
        score, issues, warnings, rec = vol1_check({
            "pe": pe,
            "land": land
        })

        risk, icon = risk_engine(score)

        st.metric("Score", f"{score}/100")
        st.metric("Risk Level", f"{icon} {risk}")

        st.write("### Issues")
        st.write(issues if issues else "None")

        st.write("### Warnings")
        st.write(warnings if warnings else "None")

        st.write("### Recommendations")
        st.write(rec if rec else ["Ensure zoning compliance", "Verify layout efficiency"])


# ===============================
# VOL 3 UI
# ===============================

with tab2:
    st.subheader("Vol 3 - Sewer & Pump Station Check")

    pe = st.number_input("PE", 0, 100000, 200)
    flow = st.number_input("Flow (m³/day)", 0.0, 100000.0, 50.0)
    diameter = st.number_input("Pipe Diameter (mm)", 0, 2000, 150)
    slope = st.number_input("Slope", 0.0, 1.0, 0.01)

    if st.button("Run Vol 3 Check"):
        score, issues, warnings, rec = vol3_check({
            "pe": pe,
            "flow": flow,
            "diameter": diameter,
            "slope": slope
        })

        risk, icon = risk_engine(score)

        st.metric("Score", f"{score}/100")
        st.metric("Risk Level", f"{icon} {risk}")

        st.write("### Issues")
        st.write(issues if issues else "None")

        st.write("### Warnings")
        st.write(warnings if warnings else "None")

        st.write("### Recommendations")
        st.write(rec if rec else [
            "Verify hydraulic gradient",
            "Check manhole spacing",
            "Confirm pipe self-cleansing velocity"
        ])


# ===============================
# VOL 4 UI
# ===============================

with tab3:
    st.subheader("Vol 4 - Sewage Treatment Plant (STP) Check")

    pe = st.number_input("PE", 0, 100000, 300)
    stp = st.number_input("STP Capacity (PE equivalent)", 0, 100000, 0)

    if st.button("Run Vol 4 Check"):
        score, issues, warnings, rec = vol4_check({
            "pe": pe,
            "stp_capacity": stp
        })

        risk, icon = risk_engine(score)

        st.metric("Score", f"{score}/100")
        st.metric("Risk Level", f"{icon} {risk}")

        st.write("### Issues")
        st.write(issues if issues else "None")

        st.write("### Warnings")
        st.write(warnings if warnings else "None")

        st.write("### Recommendations")
        st.write(rec if rec else [
            "Check STP process selection (SBR / Extended Aeration)",
            "Verify effluent compliance",
            "Check hydraulic retention time"
        ])


# ===============================
# FOOTER
# ===============================

st.markdown("---")
st.caption("MSIG Engine v8 | Rule-Based Compliance System | Engineering Decision Support Tool")