import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# ================= CONFIG =================
st.set_page_config(page_title="Aplikasi E-Kinerja KPU Kota Bengkulu", layout="wide")

# ================= HEADER (IMAGE) =================
# Pastikan file logo/header ada di repo: header.png
st.image("header.png", use_container_width=True)

st.markdown("### 📊 Aplikasi E-Kinerja KPU Kota Bengkulu")

# ================= PERIODE DINAMIS (21 - 20) =================
def get_periode(tgl=None):
    if tgl is None:
        tgl = date.today()

    if tgl.day >= 21:
        start = date(tgl.year, tgl.month, 21)
        if tgl.month == 12:
            end = date(tgl.year + 1, 1, 20)
        else:
            end = date(tgl.year, tgl.month + 1, 20)
    else:
        if tgl.month == 1:
            start = date(tgl.year - 1, 12, 21)
        else:
            start = date(tgl.year, tgl.month - 1, 21)
        end = date(tgl.year, tgl.month, 20)

    return start, end

start_periode, end_periode = get_periode()

st.info(f"📅 Periode aktif: {start_periode} s/d {end_periode}")

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

# ================= LOAD DATA =================
def load_users():
    return pd.DataFrame(user_sheet.get_all_records())

def load_data():
    return pd.DataFrame(sheet.get_all_records())

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login = False

users_df = load_users()

if not st.session_state.login:

    st.subheader("🔐 Login")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):

        user = users_df[
            (users_df["NIP"].astype(str) == str(nip)) &
            (users_df["Password"].astype(str) == str(pw))
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

# ================= HEADER USER =================
st.success(f"Login: {st.session_state.nama} ({st.session_state.role})")

if st.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

# ================= MENU =================
menu = st.sidebar.selectbox(
    "Menu",
    ["Dashboard", "Input Kinerja", "Data Kinerja", "Download Rekap", "Admin"]
)

# ================= LOAD DATA =================
def get_data():
    df = pd.DataFrame(sheet.get_all_records())
    return df

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.subheader("📊 Dashboard")
    df = get_data()

    if not df.empty:
        df["Durasi (Jam)"] = pd.to_numeric(df["Durasi (Jam)"], errors="coerce").fillna(0)
        st.bar_chart(df.groupby("Nama")["Durasi (Jam)"].sum())
    else:
        st.info("Belum ada data")

# ================= INPUT =================
elif menu == "Input Kinerja":

    st.subheader("📝 Input Kinerja")

    with st.form("form"):
        tanggal = st.date_input("Tanggal", datetime.today())
        jam_masuk = st.text_input("Jam Masuk")
        jam_keluar = st.text_input("Jam Keluar")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")
        lokasi = st.selectbox("Lokasi", ["Kantor", "Rumah", "Dinas"])

        submit = st.form_submit_button("Simpan")

    if submit:
        sheet.append_row([
            st.session_state.nama,
            st.session_state.nip,
            st.session_state.jabatan,
            str(tanggal),
            jam_masuk,
            jam_keluar,
            uraian,
            output,
            lokasi
        ])
        st.success("Data tersimpan")

# ================= DOWNLOAD REKAP =================
elif menu == "Download Rekap":

    st.subheader("📥 Download Rekap Pegawai")

    df = get_data()

    if df.empty:
        st.warning("Tidak ada data")
        st.stop()

    pegawai_list = df["Nama"].unique()
    pilih = st.selectbox("Pilih Pegawai", pegawai_list)

    df_user = df[df["Nama"] == pilih]

    df_user["Tanggal"] = pd.to_datetime(df_user["Tanggal"], errors="coerce")

    df_filter = df_user[
        (df_user["Tanggal"] >= pd.to_datetime(start_periode)) &
        (df_user["Tanggal"] <= pd.to_datetime(end_periode))
    ]

    st.write(df_filter)

    def to_excel(data):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            data.to_excel(writer, index=False)
        return output.getvalue()

    if st.button("⬇️ Download Excel"):
        st.download_button(
            "Download File",
            data=to_excel(df_filter),
            file_name=f"Rekap_{pilih}_{start_periode}_{end_periode}.xlsx"
        )

# ================= ADMIN (SIMPLIFIED) =================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    st.subheader("⚙️ Admin Panel")

    st.info("Kelola user dilakukan di sheet users")
