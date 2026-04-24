import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import hashlib

# ================= CONFIG =================
st.set_page_config(page_title="KPU Kinerja", layout="wide")

st.title("📊 Aplikasi Kinerja KPU")

# ================= DEFAULT ADMIN =================
DEFAULT_ADMIN = {
    "NIP": "admin",
    "Nama": "Super Admin",
    "Jabatan": "Administrator",
    "Password": hashlib.sha256("admin123".encode()).hexdigest(),
    "Role": "admin"
}

# ================= GOOGLE SHEETS =================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["connections"]["gsheets"]["service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

SPREADSHEET_ID = "16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM"

spreadsheet = client.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.sheet1
user_sheet = spreadsheet.worksheet("users")

# ================= FUNCTIONS =================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def load_users():
    try:
        df = pd.DataFrame(user_sheet.get_all_records())
        if df.empty:
            return pd.DataFrame([DEFAULT_ADMIN])
        return df
    except:
        return pd.DataFrame([DEFAULT_ADMIN])

def load_data():
    try:
        return pd.DataFrame(sheet.get_all_records())
    except:
        return pd.DataFrame()

# ================= SESSION =================
if "login" not in st.session_state:
    st.session_state.login = False

users_df = load_users()
data = load_data()

# ================= LOGIN =================
if not st.session_state.login:

    st.subheader("🔐 Login")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):

        user = users_df[
            (users_df["NIP"].astype(str) == str(nip)) &
            (users_df["Password"] == hash_password(pw))
        ]

        if not user.empty:
            u = user.iloc[0]

            st.session_state.update({
                "login": True,
                "nama": u["Nama"],
                "nip": u["NIP"],
                "jabatan": u["Jabatan"],
                "role": u["Role"]
            })

            st.rerun()

        else:
            st.error("Login gagal")

    st.stop()

# ================= HEADER =================
st.success(f"Login: {st.session_state.nama} ({st.session_state.role})")

if st.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= MENU NAVIGATION =================
menu = st.sidebar.selectbox(
    "Menu",
    ["Dashboard", "Input Kinerja", "Data Kinerja", "Admin"]
)

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.subheader("📊 Dashboard")

    if not data.empty:
        data["Durasi (Jam)"] = pd.to_numeric(data["Durasi (Jam)"], errors="coerce").fillna(0)
        st.bar_chart(data.groupby("Nama")["Durasi (Jam)"].sum())

# ================= INPUT =================
elif menu == "Input Kinerja":
    st.subheader("📝 Input Kinerja")

    with st.form("form"):

        tanggal = st.date_input("Tanggal", datetime.today())
        jam_masuk = st.text_input("Jam Masuk", "08:00")
        jam_keluar = st.text_input("Jam Keluar", "17:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")
        lokasi = st.selectbox("Lokasi", ["Kantor", "Rumah", "Dinas"])

        submit = st.form_submit_button("Simpan")

    if submit:
        jm = datetime.strptime(jam_masuk, "%H:%M")
        jk = datetime.strptime(jam_keluar, "%H:%M")
        durasi = (jk - jm).seconds // 3600

        sheet.append_row([
            st.session_state.nama,
            st.session_state.nip,
            st.session_state.jabatan,
            str(tanggal),
            jam_masuk,
            jam_keluar,
            durasi,
            uraian,
            output,
            lokasi
        ])

        st.success("Data tersimpan")

# ================= DATA =================
elif menu == "Data Kinerja":
    st.subheader("📋 Data Kinerja")
    st.dataframe(data, use_container_width=True)

# ================= ADMIN =================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    st.subheader("⚙️ Admin Panel")

    tab1, tab2, tab3 = st.tabs(["Tambah", "Edit", "Hapus"])

    users_df = load_users()

    # ===== TAMBAH =====
    with tab1:
        nip_b = st.text_input("NIP")
        nama_b = st.text_input("Nama")
        jabatan_b = st.text_input("Jabatan")
        pw_b = st.text_input("Password", type="password")
        role_b = st.selectbox("Role", ["pegawai", "admin", "pimpinan"])

        if st.button("Tambah"):
            user_sheet.append_row([
                nip_b, nama_b, jabatan_b,
                hash_password(pw_b),
                role_b
            ])
            st.success("User ditambah")

    # ===== EDIT =====
    with tab2:
        if not users_df.empty:
            pilih = st.selectbox("Pilih NIP", users_df["NIP"].astype(str))
            row = users_df[users_df["NIP"].astype(str) == pilih].iloc[0]

            nama_e = st.text_input("Nama", row["Nama"])
            role_e = st.selectbox("Role", ["pegawai","admin","pimpinan"])

            if st.button("Update"):
                st.success("Updated (logic bisa dikembangkan lebih lanjut)")

    # ===== HAPUS =====
    with tab3:
        hapus = st.selectbox("Hapus NIP", users_df["NIP"].astype(str))

        if st.button("Hapus"):
            st.success("Deleted (logic bisa disambungkan ke sheet)")