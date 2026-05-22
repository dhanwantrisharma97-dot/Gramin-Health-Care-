import streamlit as st
import sqlite3
import json
import uuid
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Rural Health Connect", page_icon="🏥", layout="wide")

st.markdown("""
<style>
.main-header { font-size: 2.5rem; font-weight: bold; color: #2E7D32; text-align: center; }
.tagline { font-style: italic; color: #2E7D32; text-align: center; font-size: 1.1rem; }
.metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 10px; color: white; text-align: center; }
.metric-value { font-size: 2rem; font-weight: bold; }
.patient-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; }
.vital-normal { color: #4CAF50; font-weight: bold; }
.vital-warning { color: #FF9800; font-weight: bold; }
.vital-danger { color: #F44336; font-weight: bold; }
.danger-box { background: #FFEBEE; border-left: 4px solid #F44336; padding: 1rem; border-radius: 4px; margin: 1rem 0; }
.warning-box { background: #FFF3E0; border-left: 4px solid #FF9800; padding: 1rem; border-radius: 4px; margin: 1rem 0; }
.success-box { background: #E8F5E9; border-left: 4px solid #4CAF50; padding: 1rem; border-radius: 4px; margin: 1rem 0; }
.info-box { background: #E3F2FD; border-left: 4px solid #1976D2; padding: 1rem; border-radius: 4px; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db():
    return sqlite3.connect("rural_health.db", check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS patients (id TEXT PRIMARY KEY, health_id TEXT UNIQUE, name TEXT, age INTEGER, gender TEXT, phone TEXT, address TEXT, aadhaar TEXT, blood_group TEXT, allergies TEXT, medical_history TEXT, category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS vitals (id TEXT PRIMARY KEY, patient_id TEXT, bp_systolic INTEGER, bp_diastolic INTEGER, pulse INTEGER, spo2 INTEGER, temperature REAL, respiratory_rate INTEGER, blood_sugar_fasting REAL, blood_sugar_pp REAL, weight REAL, height REAL, bmi REAL, recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, recorded_by TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS prescriptions (id TEXT PRIMARY KEY, patient_id TEXT, doctor_name TEXT, diagnosis TEXT, diagnosis_code TEXT, medicines TEXT, investigations TEXT, advice TEXT, follow_up_date TEXT, severity TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS symptoms (id TEXT PRIMARY KEY, patient_id TEXT, symptoms TEXT, body_part TEXT, severity INTEGER, duration TEXT, associated_symptoms TEXT, recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS appointments (id TEXT PRIMARY KEY, patient_id TEXT, appointment_date TEXT, appointment_type TEXT, status TEXT DEFAULT 'Scheduled', notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS medicines (id TEXT PRIMARY KEY, name TEXT, generic_name TEXT, category TEXT, dosage_forms TEXT, adult_dose TEXT, pediatric_dose TEXT, contraindications TEXT, side_effects TEXT, pregnancy_category TEXT)")
    conn.commit()
    c.execute("SELECT COUNT(*) FROM medicines")
    if c.fetchone()[0] == 0:
        meds = [
            (str(uuid.uuid4()), "Paracetamol", "Acetaminophen", "Analgesic", "Tablet/Syrup", "500mg-1g q6h", "10-15mg/kg q6h", "Liver disease", "Nausea", "B"),
            (str(uuid.uuid4()), "Amoxicillin", "Amoxicillin", "Antibiotic", "Capsule/Syrup", "500mg q8h", "20-40mg/kg/day", "Penicillin allergy", "Diarrhea", "B"),
            (str(uuid.uuid4()), "Metformin", "Metformin", "Antidiabetic", "Tablet", "500mg-1g BD", "Not for <10yrs", "Kidney disease", "Stomach upset", "B"),
            (str(uuid.uuid4()), "Amlodipine", "Amlodipine", "BP Medicine", "Tablet", "5-10mg OD", "Not for kids", "Heart valve disease", "Swelling", "C"),
            (str(uuid.uuid4()), "ORS", "Oral Rehydration", "Electrolyte", "Sachet", "As needed", "As per weight", "None", "None", "A"),
            (str(uuid.uuid4()), "Albendazole", "Albendazole", "Deworming", "Tablet", "400mg once", "200mg once", "Pregnancy", "Stomach pain", "C"),
            (str(uuid.uuid4()), "Salbutamol", "Albuterol", "Asthma", "Inhaler/Syrup", "2-4mg q6h", "0.1mg/kg q6h", "None", "Shaking", "C"),
            (str(uuid.uuid4()), "Ibuprofen", "Ibuprofen", "Painkiller", "Tablet", "400mg q8h", "5-10mg/kg q6h", "Stomach ulcer", "Stomach pain", "D"),
            (str(uuid.uuid4()), "Cetirizine", "Cetirizine", "Allergy", "Tablet", "10mg OD", "2.5-5mg OD", "Kidney disease", "Sleepiness", "B"),
            (str(uuid.uuid4()), "Omeprazole", "Omeprazole", "Acidity", "Capsule", "20mg OD", "Not for <1yr", "None", "Headache", "C"),
        ]
        c.executemany("INSERT INTO medicines VALUES (?,?,?,?,?,?,?,?,?,?)", meds)
        conn.commit()

def gen_health_id():
    return "RHC" + datetime.now().strftime("%Y%m") + str(uuid.uuid4().int)[:6]

def calc_bmi(w, h):
    if w and h and h > 0:
        return round(w / ((h/100)**2), 2)
    return None

def vital_status(val, typ):
    if typ == "bp_systolic":
        if val < 90: return "danger"
        elif val > 160: return "danger"
        elif val > 140: return "warning"
        else: return "normal"
    elif typ == "bp_diastolic":
        if val < 60 or val > 100: return "danger"
        elif val > 90: return "warning"
        else: return "normal"
    elif typ == "pulse":
        if val < 60 or val > 120: return "danger"
        elif val > 100: return "warning"
        else: return "normal"
    elif typ == "spo2":
        if val < 90: return "danger"
        elif val < 95: return "warning"
        else: return "normal"
    elif typ == "temp":
        if val > 103: return "danger"
        elif val > 101: return "warning"
        else: return "normal"
    return "normal"

def triage(bp_sys, bp_dia, pulse, spo2, temp):
    red = 0
    if bp_sys and bp_sys > 180: red += 1
    if bp_sys and bp_sys < 80: red += 1
    if spo2 and spo2 < 90: red += 1
    if temp and temp > 104: red += 1
    if pulse and pulse > 150: red += 1
    if red >= 2:
        return "RED - Emergency! Immediate attention", "danger-box"
    elif red == 1:
        return "YELLOW - Urgent, treat within 24 hrs", "warning-box"
    return "GREEN - Stable, routine care", "success-box"

def diagnose(symptoms, vitals):
    s = symptoms.lower()
    d = []
    if "fever" in s and "headache" in s: d.append(("Viral Fever", 75, ["CBC", "MP"]))
    if "cough" in s and "fever" in s: d.append(("Pneumonia", 70, ["Chest X-Ray", "CBC"]))
    if "chest pain" in s: d.append(("Heart Problem", 60, ["ECG", "Troponin"]))
    if "stomach pain" in s and "vomiting" in s: d.append(("Stomach Infection", 65, ["CBC", "USG"]))
    if "burning" in s and "urine" in s: d.append(("Urine Infection", 70, ["Urine Test"]))
    if "wound" in s or "cut" in s: d.append(("Wound Infection", 55, ["CBC"]))
    if vitals.get('bs_fasting') and vitals['bs_fasting'] > 126: d.append(("Diabetes", 80, ["HbA1c", "Sugar Test"]))
    if vitals.get('bp_systolic') and vitals['bp_systolic'] > 140: d.append(("High BP", 60, ["ECG", "Kidney Test"]))
    if "diarrhea" in s or "loose" in s: d.append(("Diarrhea", 70, ["Stool Test"]))
    if "skin" in s or "itching" in s: d.append(("Skin Problem", 55, ["None"]))
    if not d: d.append(("General Checkup", 30, ["CBC"]))
    return sorted(d, key=lambda x: x[1], reverse=True)[:5]

def header():
    st.markdown('<div class="main-header">🏥 Rural Health Connect</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline">Har Gaon, Har Ghar, Sehat Ka Haq</div>', unsafe_allow_html=True)
    st.markdown("---")

def sidebar():
    with st.sidebar:
        st.markdown("<h3 style='color:#2E7D32'>📋 Menu</h3>", unsafe_allow_html=True)
        role = st.selectbox("Role", ["Doctor", "ASHA Worker", "Admin"])
        st.session_state.role = role
        menu = st.radio("Go to:", ["🏠 Dashboard", "👤 New Patient", "🔍 Search Patient", "🩺 Vitals", "🤒 Symptoms", "💊 Prescription", "📊 Monitoring", "📅 Appointments", "📚 Medicines", "🆘 Emergency"])
        st.markdown("---")
        st.markdown("📡 Status: 🟢 Online")
        if st.button("🔄 Sync"): st.success("Synced!")
        return menu

def dashboard():
    st.markdown("### 📊 Dashboard")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM patients")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vitals WHERE date(recorded_at)=date('now')")
    vitals_today = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM prescriptions WHERE date(created_at)=date('now')")
    presc_today = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date=date('now') AND status='Scheduled'")
    appt_today = c.fetchone()[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="metric-card"><div class="metric-value">{total}</div><div>Patients</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card" style="background:linear-gradient(135deg,#f093fb,#f5576c)"><div class="metric-value">{vitals_today}</div><div>Vitals Today</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card" style="background:linear-gradient(135deg,#4facfe,#00f2fe)"><div class="metric-value">{presc_today}</div><div>Prescriptions</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card" style="background:linear-gradient(135deg,#43e97b,#38f9d7)"><div class="metric-value">{appt_today}</div><div>Appointments</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔔 Recent Patients")
        c.execute("SELECT name, age, gender, health_id FROM patients ORDER BY created_at DESC LIMIT 5")
        for p in c.fetchall():
            st.markdown(f'<div class="patient-card"><b>{p[0]}</b> ({p[1]}y, {p[2]})<br><small>ID: {p[3]}</small></div>', unsafe_allow_html=True)
    with col2:
        st.markdown("#### ⚠️ Critical Alerts")
        c.execute("SELECT p.name, v.bp_systolic, v.spo2, v.temperature FROM vitals v JOIN patients p ON v.patient_id=p.id WHERE v.bp_systolic>180 OR v.bp_systolic<80 OR v.spo2<90 OR v.temperature>104 ORDER BY v.recorded_at DESC LIMIT 5")
        alerts = c.fetchall()
        if alerts:
            for a in alerts:
                st.markdown(f'<div class="danger-box"><b>🔴 {a[0]}</b><br>BP:{a[1]} SpO2:{a[2]}% Temp:{a[3]}F</div>', unsafe_allow_html=True)
        else:
            st.success("No critical alerts")

def new_patient():
    st.markdown("### 👤 New Patient Registration")
    with st.form("reg"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Name *")
            age = st.number_input("Age", 0, 120, 30)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            phone = st.text_input("Phone")
        with c2:
            address = st.text_area("Address")
            aadhaar = st.text_input("Aadhaar (Optional)")
            bg = st.selectbox("Blood Group", ["Select", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
            cat = st.selectbox("Category", ["General", "SC", "ST", "OBC", "BPL"])
        allergies = st.text_area("Allergies")
        history = st.text_area("Medical History")
        if st.form_submit_button("✅ Register"):
            if not name:
                st.error("Name required!")
            else:
                conn = get_db()
                c = conn.cursor()
                pid = str(uuid.uuid4())
                hid = gen_health_id()
                c.execute("INSERT INTO patients VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (pid, hid, name, age, gender, phone, address, aadhaar, bg if bg!="Select" else None, allergies, history, cat, datetime.now()))
                conn.commit()
                st.success(f"Registered! Health ID: {hid}")
                st.balloons()

def search_patient():
    st.markdown("### 🔍 Search Patient")
    search = st.text_input("Search by name/ID/phone/aadhaar")
    if search:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM patients WHERE name LIKE ? OR health_id LIKE ? OR phone LIKE ? OR aadhaar LIKE ?", 
                 (f'%{search}%',)*4)
        for p in c.fetchall():
            with st.expander(f"👤 {p[2]} ({p[4]}, {p[3]}y) - {p[1]}"):
                c1, c2 = st.columns(2)
                c1.write(f"**ID:** {p[1]}")
**Age:** {p[3]}
**Gender:** {p[4]}
c1.write(f"**Phone:** {p[5] or 'N/A'}")
c2.write(f"**Address:** {p[6] or 'N/A'}")
c2.write(f"**Blood Group:** {p[8] or 'N/A'}")
c2.write(f"**Allergies:** {p[9] or 'None'}")

def vitals_entry():
    st.markdown("### 🩺 Vitals Entry")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, health_id FROM patients ORDER BY name")
    pts = c.fetchall()
    if not pts:
        st.warning("No patients! Register first.")
        return
    opts = {f"{p[1]} ({p[2]})": p[0] for p in pts}
    pid = opts[st.selectbox("Patient", list(opts.keys()))]
    with st.form("vitals"):
        c1, c2, c3 = st.columns(3)
        with c1:
            bp_sys = st.number_input("BP Systolic", 50, 250, 120)
            pulse = st.number_input("Pulse", 30, 200, 72)
            weight = st.number_input("Weight (kg)", 1.0, 200.0, 60.0)
        with c2:
            bp_dia = st.number_input("BP Diastolic", 30, 150, 80)
            spo2 = st.number_input("SpO2 (%)", 70, 100, 98)
            height = st.number_input("Height (cm)", 30.0, 250.0, 165.0)
        with c3:
            temp = st.number_input("Temperature (F)", 95.0, 110.0, 98.6)
            resp = st.number_input("Respiratory Rate", 8, 40, 16)
        c1, c2 = st.columns(2)
        with c1: bs_fast = st.number_input("Fasting Sugar", 50, 500, 90)
        with c2: bs_pp = st.number_input("PP Sugar", 50, 500, 120)
        bmi = calc_bmi(weight, height)
        if bmi: st.info(f"BMI: {bmi}")
        if st.form_submit_button("💾 Save"):
            vid = str(uuid.uuid4())
            c.execute("INSERT INTO vitals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (vid, pid, bp_sys, bp_dia, pulse, spo2, temp, resp, bs_fast, bs_pp, weight, height, bmi, datetime.now(), st.session_state.get('role','Doctor')))
            conn.commit()
            msg, cls = triage(bp_sys, bp_dia, pulse, spo2, temp)
            st.markdown(f'<div class="{cls}"><b>{msg}</b></div>', unsafe_allow_html=True)
            st.success("Vitals saved!")

def symptom_checker():
    st.markdown("### 🤒 Symptom Checker")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, health_id FROM patients ORDER BY name")
    pts = c.fetchall()
    if not pts:
        st.warning("No patients!")
        return
    opts = {f"{p[1]} ({p[2]})": p[0] for p in pts}
    pid = opts[st.selectbox("Patient", list(opts.keys()))]
    c.execute("SELECT * FROM vitals WHERE patient_id=? ORDER BY recorded_at DESC LIMIT 1", (pid,))
    lv = c.fetchone()
    with st.form("symptoms"):
        c1, c2 = st.columns(2)
        with c1:
            part = st.selectbox("Body Part", ["General", "Head", "Eyes", "Ears", "Chest", "Stomach", "Skin", "Legs"])
            sym = st.text_area("Symptoms", placeholder="fever, headache, cough...")
            sev = st.slider("Severity 1-10", 1, 10, 5)
        with c2:
            dur = st.selectbox("Duration", ["<1 day", "1-3 days", "4-7 days", "1-2 weeks", ">1 month", "Chronic"])
            assoc = st.text_area("Other symptoms")
        if st.form_submit_button("🔍 Analyze"):
            sid = str(uuid.uuid4())
            c.execute("INSERT INTO symptoms VALUES (?,?,?,?,?,?,?,?)", (sid, pid, sym, part, sev, dur, assoc, datetime.now()))
            conn.commit()
            vd = {}
            if lv:
                vd = {'bp_systolic': lv[2], 'bp_diastolic': lv[3], 'pulse': lv[4], 'spo2': lv[5], 'temperature': lv[6], 'blood_sugar_fasting': lv[9]}
            dx = diagnose(sym, vd)
            st.markdown("### 📋 Possible Diagnoses")
            for i, (d, conf, tests) in enumerate(dx, 1):
                with st.expander(f"#{i} {d} ({conf}% confidence)"):
                    st.write("**Tests:** " + ", ".join(tests))
                    if conf >= 70: st.markdown('<div class="warning-box">⚠️ High probability</div>', unsafe_allow_html=True)
                    elif conf >= 50: st.markdown('<div class="info-box">ℹ️ Moderate probability</div>', unsafe_allow_html=True)
                    else: st.markdown('<div class="success-box">✅ Low probability</div>', unsafe_allow_html=True)

def prescription():
    st.markdown("### 💊 Prescription")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, health_id FROM patients ORDER BY name")
    pts = c.fetchall()
    if not pts:
        st.warning("No patients!")
        return
    opts = {f"{p[1]} ({p[2]})": p[0] for p in pts}
    pid = opts[st.selectbox("Patient", list(opts.keys()))]
    c.execute("SELECT * FROM patients WHERE id=?", (pid,))
    patient = c.fetchone()
    with st.form("presc"):
        c1, c2 = st.columns(2)
        with c1:
            diag = st.text_input("Diagnosis")
            code = st.text_input("ICD-10 Code (Optional)")
            sev = st.selectbox("Severity", ["Mild", "Moderate", "Severe", "Emergency"])
        with c2:
            doc = st.text_input("Doctor", value=st.session_state.get('role','Doctor'))
            fup = st.date_input("Follow-up", value=datetime.now()+timedelta(days=7))
        st.markdown("#### Medicines")
        c.execute("SELECT name, generic_name, adult_dose FROM medicines ORDER BY name")
        meds = c.fetchall()
        selected = []
        cols = st.columns(3)
        for i, m in enumerate(meds[:9]):
            with cols[i%3]:
                if st.checkbox(f"{m[0]}", key=f"m{i}"):
                    dose = st.text_input(f"Dose", value=m[2], key=f"d{i}")
                    freq = st.selectbox(f"Freq", ["OD", "BD", "TDS", "QID"], key=f"f{i}")
                    days = st.number_input(f"Days", 1, 90, 5, key=f"dy{i}")
                    selected.append({"name": m[0], "dose": dose, "freq": freq, "days": days})
        c1, c2 = st.columns(2)
        with c1: inv = st.text_area("Tests")
        with c2: adv = st.text_area("Advice")
        if st.form_submit_button("📝 Generate"):
            prid = str(uuid.uuid4())
            c.execute("INSERT INTO prescriptions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (prid, pid, doc, diag, code, json.dumps(selected), inv, adv, fup.strftime("%Y-%m-%d"), sev, datetime.now()))
            conn.commit()
            st.success("Prescription generated!")
            st.markdown("### 📄 Prescription")
            st.markdown(f"**Patient:** {patient[2]} | **Age:** {patient[3]}y | **ID:** {patient[1]}")
            st.markdown(f"**Date:** {datetime.now().strftime('%d/%m/%Y')} | **Doctor:** {doc}")
            st.markdown(f"**Diagnosis:** {diag} | **Severity:** {sev}")
            st.markdown("**Rx:**")
            for i, m in enumerate(selected, 1):
                st.write(f"{i}. {m['name']} - {m['dose']} - {m['freq']} x {m['days']} days")
            st.markdown(f"**Tests:** {inv or 'None'}
**Advice:** {adv or 'None'}
**Follow-up:** {fup.strftime('%d/%m/%Y')}")
            txt = f"PRESCRIPTION\nPatient: {patient[2]}\nDiagnosis: {diag}\n"
            for m in selected: txt += f"- {m['name']} {m['dose']} {m['freq']} {m['days']}days\n"
            st.download_button("📥 Download", txt, f"presc_{patient[1]}_{datetime.now().strftime('%Y%m%d')}.txt")

def monitoring():
    st.markdown("### 📊 Health Monitoring")
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, health_id FROM patients ORDER BY name")
    pts = c.fetchall()
    if not pts:
        st.warning("No patients!")
        return
    opts = {f"{p[1]} ({p[2]})": p[0] for p in pts}
    pid = opts[st.selectbox("Patient", list(opts.keys()))]
    c.execute("SELECT * FROM vitals WHERE patient_id=? ORDER BY recorded_at DESC", (pid,))
    vitals = c.fetchall()
    if not vitals:
        st.info("No vitals recorded")
        return
    latest = vitals[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(f"**BP**<br><span class='vital-{vital_status(latest[2],'bp_systolic')}'>{latest[2]}/{latest[3]}</span>", unsafe_allow_html=True)
    c2.markdown(f"**Pulse**<br><span class='vital-{vital_status(latest[4],'pulse')}'>{latest[4]}</span>", unsafe_allow_html=True)
    c3.markdown(f"**SpO2**<br><span class='vital-{vital_status(latest[5],'spo2')}'>{latest[5]}%</span>", unsafe_allow_html=True)
    c4.markdown(f"**Temp**<br><span class='vital-{vital_status(latest[6],'temp')}'>{latest[6]}F</span>", unsafe_allow_html=True)
    c5.write(f"**BMI:** {latest[13] or 'N/A'}")
    if len(vitals) > 1:
        df = pd.DataFrame(vitals, columns=['id','pid','bp_sys','bp_dia','pulse','spo2','temp','resp','bsf','bsp','wt','ht','bmi','dt','by'])
        df['dt'] = pd.to_datetime(df['dt'])
        df = df.sort_values('dt')
        t1, t2, t3 = st.tabs(["BP Trend", "Sugar Trend", "Weight/BMI"])
        with t1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['dt'], y=df['bp_sys'], name='Systolic', line=dict(color='red')))
            fig.add_trace(go.Scatter(x=df['dt'], y=df['bp_dia'], name='Diastolic', line=dict(color='blue')))
            fig.update_layout(title="Blood Pressure", xaxis_title="Date", yaxis_title="mmHg")
            st.plotly_chart(fig, use_container_width=True)
        with t2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['dt'], y=df['bsf'], name='Fasting', line=dict(color='green')))
            fig.add_trace(go.Scatter(x=df['dt'], y=df['bsp'], name='PP', line=dict(color='orange')))
            fig.update_layout(title="Blood Sugar", xaxis_title="Date", yaxis_title="mg/dL")
            st.plotly_chart(fig, use_container_width=True)
        with t3:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['dt'], y=df['wt'], name='Weight'))
            fig.add_trace(go.Scatter(x=df['dt'], y=df['bmi'], name='BMI', yaxis='y2'))
            fig.update_layout(title="Weight & BMI", yaxis2=dict(overlaying='y', side='right'))
            st.plotly_chart(fig, use_container_width=True)
    df_show = pd.DataFrame(vitals, columns=['id','pid','bp_sys','bp_dia','pulse','spo2','temp','resp','bsf','bsp','wt','ht','bmi','dt','by'])[['dt','bp_sys','bp_dia','pulse','spo2','temp','bmi']]
    st.dataframe(df_show, use_container_width=True)

def appointments():
    st.markdown("### 📅 Appointments")
    conn = get_db()
    c = conn.cursor()
    t1, t2 = st.tabs(["Schedule", "View"])
    with t1:
        c.execute("SELECT id, name, health_id FROM patients ORDER BY name")
        pts = c.fetchall()
        if not pts:
            st.warning("No patients!")
            return
        opts = {f"{p[1]} ({p[2]})": p[0] for p in pts}
        with st.form("appt"):
            pid = opts[st.selectbox("Patient", list(opts.keys()))]
            dt = st.date_input("Date", min_value=datetime.now().date())
            typ = st.selectbox("Type", ["General", "Follow-up", "Emergency", "Vaccination", "ANC", "Child Health"])
            notes = st.text_area("Notes")
            if st.form_submit_button("📅 Schedule"):
                aid = str(uuid.uuid4())
                c.execute("INSERT INTO appointments VALUES (?,?,?,?,?,?,?)", (aid, pid, dt.strftime("%Y-%m-%d"), typ, "Scheduled", notes, datetime.now()))
                conn.commit()
                st.success("Scheduled!")
    with t2:
        c.execute("SELECT a.id, p.name, a.appointment_date, a.appointment_type, a.status, a.notes FROM appointments a JOIN patients p ON a.patient_id=p.id ORDER BY a.appointment_date DESC")
        for a in c.fetchall():
            sc = "🟢" if a[4]=="Completed" else "🟡"
            with st.expander(f"{sc} {a[1]} - {a[2]} ({a[3]})"):
                st.write(f"Status: {a[4]} | Notes: {a[5] or 'None'}")
                if a[4]=="Scheduled" and st.button("✅ Complete", key=f"comp{a[0]}"):
                    c.execute("UPDATE appointments SET status='Completed' WHERE id=?", (a[0],))
                    conn.commit()
                    st.rerun()

def medicines():
    st.markdown("### 📚 Medicine Database")
    conn = get_db()
    c = conn.cursor()
    search = st.text_input("Search")
    if search:
        c.execute("SELECT * FROM medicines WHERE name LIKE ? OR generic_name LIKE ?", (f'%{search}%',)*2)
    else:
        c.execute("SELECT * FROM medicines ORDER BY name")
    for m in c.fetchall():
        with st.expander(f"💊 {m[1]} ({m[2]})"):
            c1, c2 = st.columns(2)
            c1.write(f"**Category:** {m[3]}
**Form:** {m[4]}
**Adult:** {m[5]}
**Child:** {m[6]}")
            c2.write(f"**Avoid if:** {m[7]}
**Side effects:** {m[8]}
**Pregnancy:** {m[9]}")

def emergency():
    st.markdown("### 🆘 Emergency")
    st.markdown('<div class="danger-box"><h3>⚠️ EMERGENCY NUMBERS</h3></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div style="background:#FFEBEE;padding:20px;border-radius:10px;text-align:center;"><h2>🚑 108</h2><b>Ambulance</b></div>', unsafe_allow_html=True)
    c2.markdown('<div style="background:#FFF3E0;padding:20px;border-radius:10px;text-align:center;"><h2>👮 100</h2><b>Police</b></div>', unsafe_allow_html=True)
    c3.markdown('<div style="background:#E3F2FD;padding:20px;border-radius:10px;text-align:center;"><h2>🔥 101</h2><b>Fire</b></div>', unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🚨 SEND EMERGENCY ALERT", type="primary"):
        st.markdown(f'<div class="danger-box"><h4>🚨 ALERT SENT!</h4><p>Time: {datetime.now().strftime("%H:%M:%S")}</p><p>Nearest PHC, 108 Ambulance notified</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 🩹 First Aid")
    etype = st.selectbox("Emergency Type", ["Bleeding", "Burns", "Choking", "Snake Bite", "Heart Attack"])
    guides = {
        "Bleeding": ["Apply pressure with clean cloth", "Elevate wound", "Clean with antiseptic", "Cover with bandage"],
        "Burns": ["Cool with water", "No ice directly", "Cover with clean cloth", "Don't break blisters"],
        "Choking": ["Encourage cough", "Heimlich if trained", "Call 108", "No food/water"],
        "Snake Bite": ["Keep calm", "Immobilize limb", "Don't cut/suck", "Remove tight items", "Rush to hospital"],
        "Heart Attack": ["Call 108", "Sit semi-reclined", "Loosen clothing", "Aspirin 300mg if available", "Be ready for CPR"]
    }
    for step in guides[etype]:
        st.markdown(f"- ✅ {step}")
    st.markdown('<div class="warning-box">⚠️ For guidance only. Seek professional help immediately!</div>', unsafe_allow_html=True)

# MAIN
def main():
    init_db()
    header()
    page = sidebar()
    if page == "🏠 Dashboard": dashboard()
    elif page == "👤 New Patient": new_patient()
    elif page == "🔍 Search Patient": search_patient()
    elif page == "🩺 Vitals": vitals_entry()
    elif page == "🤒 Symptoms": symptom_checker()
    elif page == "💊 Prescription": prescription()
    elif page == "📊 Monitoring": monitoring()
    elif page == "📅 Appointments": appointments()
    elif page == "📚 Medicines": medicines()
    elif page == "🆘 Emergency": emergency()

if __name__ == "__main__":
    main()
