import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# ================= CONFIG =================
st.set_page_config(
    page_title="Aplikasi E-Kinerja KPU Kota Bengkulu",
    layout="wide"
)

# ================= HEADER =================
col1, col2 = st.columns([1, 5])

with col1:
    st.image("logo_kpu.png", width=80)

with col2:
    st.title("📊 Aplikasi E-Kinerja KPU Kota Bengkulu")
    st.caption("Transparan • Akuntabel • Profesional")

st.markdown("---")

# ================= GOOGLE SHEETS AUTH =================
SCOPE = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

CREDS_FILE = "credentials.json"

@st.cache_resource
def connect_gsheet():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open("E-Kinerja").worksheet("data")
    users = client.open("E-Kinerja").worksheet("users")
    return sheet, users

sheet, users_sheet = connect_gsheet()

# ================= LOAD USERS =================
def load_users():
    data = users_sheet.get_all_records()
    return pd.DataFrame(data)

users_df = load_users()

# ================= LOGIN =================
st.sidebar.header("🔐 Login")

username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

login_btn = st.sidebar.button("Login")

if "login" not in st.session_state:
    st.session_state.login = False

if login_btn:
    user = users_df[
        (users_df["username"] == username) &
        (users_df["password"] == password)
    ]

    if not user.empty:
        st.session_state.login = True
        st.session_state.user = user.iloc[0].to_dict()
        st.success("Login berhasil!")
    else:
        st.error("Username atau password salah")

# ================= IF NOT LOGIN =================
if not st.session_state.login:
    st.warning("Silakan login terlebih dahulu")
    st.stop()

user = st.session_state.user
role = user["role"]
nama = user["nama"]

st.sidebar.success(f"Login sebagai: {nama} ({role})")

# ================= LOAD DATA =================
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

# convert tanggal
if not df.empty:
    df["tanggal"] = pd.to_datetime(df["tanggal"])

# ================= FILTER USER =================
if role == "pegawai":
    df = df[df["nama"] == nama]

# ================= DASHBOARD =================
st.subheader(f"👋 Selamat datang, {nama}")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Kegiatan", len(df))
col2.metric("Selesai", len(df[df["status"] == "Selesai"]) if not df.empty else 0)
col3.metric("Proses", len(df[df["status"] == "Proses"]) if not df.empty else 0)
col4.metric("Bulan Data", datetime.now().strftime("%B %Y"))

st.markdown("---")

# ================= FILTER TANGGAL =================
st.subheader("📅 Filter Periode")

col1, col2 = st.columns(2)

start_date = col1.date_input("Tanggal Mulai")
end_date = col2.date_input("Tanggal Akhir")

if not df.empty:
    mask = (df["tanggal"].dt.date >= start_date) & (df["tanggal"].dt.date <= end_date)
    filtered = df.loc[mask]
else:
    filtered = df

# ================= TABEL DATA =================
st.subheader("📋 Data Kinerja")

st.dataframe(filtered, use_container_width=True)

# ================= DOWNLOAD EXCEL =================
def to_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Rekap")
    return output.getvalue()

st.download_button(
    "📥 Download Rekap Excel",
    data=to_excel(filtered),
    file_name=f"rekap_kinerja_{nama}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ================= ADMIN PANEL =================
if role == "admin":
    st.markdown("---")
    st.subheader("⚙️ Admin Panel")

    st.info("Menu admin aktif")

    st.dataframe(users_df)

# ================= FOOTER =================
st.markdown("---")
st.caption("© 2026 Aplikasi E-Kinerja KPU Kota Bengkulu")