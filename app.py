import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import base64
import uuid
from PIL import Image
from openpyxl.styles import Alignment

# ================= CONFIG =================
st.set_page_config(
    page_title="E-Kinerja KPU KOTA BENGKULU",
    page_icon="logo_kpu.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.empty()

# ================= CSS (TETAP PUNYA KAMU) =================
st.markdown("""
<style>
header {background: transparent !important;}
section[data-testid="stSidebar"] {background-color:#0f172a !important;width:260px !important;}
.block-container {padding:1rem 2rem !important;}
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ================= DRIVE =================
FOLDER_ID = "1c2dL7ojqrQPqt7SjYCeI7L_NBhRApped"

# ================= SESSION =================
if "gps" not in st.session_state:
    st.session_state.gps = ""

# ================= CONNECT SHEETS =================
@st.cache_resource
def connect():
    info = dict(st.secrets["connections"]["gsheets"])
    info["private_key"] = info["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )

    return gspread.authorize(creds).open_by_key(st.secrets["SPREADSHEET_ID"])

@st.cache_resource
def get_drive_service():
    info = dict(st.secrets["connections"]["gsheets"])
    info["private_key"] = info["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    return build("drive", "v3", credentials=creds)

spreadsheet = connect()
sheet = spreadsheet.worksheet("data_kinerja")

# ================= USERS =================
try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet("users", 100, 5)
    user_sheet.append_row(["NIP","Nama","Jabatan","Password","Role"])

# ================= HELPER =================
def safe(x):
    return "" if x is None else str(x)

def hitung_durasi(masuk, keluar):
    try:
        h1, m1 = str(masuk).split(":")
        h2, m2 = str(keluar).split(":")
        return round((int(h2)*60+int(m2)-int(h1)*60-int(m1))/60,2)
    except:
        return 0

# ================= DRIVE UPLOAD (FIX FINAL) =================
def upload_to_drive(file, filename):
    if file is None:
        return ""

    try:
        service = get_drive_service()

        file.seek(0)

        media = MediaIoBaseUpload(file, mimetype="image/jpeg")

        uploaded = service.files().create(
            body={"name": filename, "parents": [FOLDER_ID]},
            media_body=media,
            fields="id"
        ).execute()

        return f"https://drive.google.com/file/d/{uploaded['id']}/view"

    except Exception as e:
        st.error(f"Drive error: {e}")
        return ""

# ================= LOAD DATA =================
@st.cache_data(ttl=300)
def load_data():
    data = sheet.get_values()
    if len(data) < 2:
        return pd.DataFrame()

    df = pd.DataFrame(data[1:], columns=data[0])
    df["row"] = range(2, len(df)+2)
    return df

@st.cache_data(ttl=300)
def load_users():
    data = user_sheet.get_values()
    if len(data) < 2:
        return pd.DataFrame()
    return pd.DataFrame(data[1:], columns=data[0])

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login = False

users = load_users()

if not st.session_state.login:
    st.title("🔐 Login E-Kinerja")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        cek = users[
            (users["NIP"].astype(str) == nip) &
            (users["Password"].astype(str) == pw)
        ]

        if not cek.empty:
            u = cek.iloc[0]
            st.session_state.login = True
            st.session_state.nama = u["Nama"]
            st.session_state.nip = str(u["NIP"])
            st.session_state.jabatan = u["Jabatan"]
            st.session_state.role = u["Role"]
            st.rerun()
        else:
            st.error("Login gagal")

    st.stop()

# ================= SIDEBAR (TETAP) =================
st.sidebar.title(st.session_state.nama)

menu = st.sidebar.radio("Menu", ["Dashboard","Input","Data Kinerja","Admin"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= INPUT =================
if menu == "Input":

    st.subheader("📍 Input Kinerja")

    lokasi = st.selectbox("Lokasi", ["Kantor","Rumah","Dinas Luar / SPT"])

    foto = None
    koordinat = ""
    waktu_absen = "-"

    if lokasi == "Rumah":
        foto = st.camera_input("Foto WFH")
        koordinat = st.text_input("Koordinat GPS")

    tgl = st.date_input("Tanggal")
    masuk = st.text_input("Jam Masuk","07:30")
    keluar = st.text_input("Jam Keluar","16:00")
    uraian = st.text_area("Uraian")
    output = st.text_area("Output")

    if st.button("Simpan Data", type="primary"):

        uid = str(uuid.uuid4())
        dur = hitung_durasi(masuk, keluar)

        if not uraian or not output:
            st.error("Uraian wajib diisi")

        elif dur == 0:
            st.error("Jam tidak valid")

        elif lokasi == "Rumah" and (foto is None or koordinat == ""):
            st.error("Foto & GPS wajib")

        else:

            link_foto = ""
            if lokasi == "Rumah":
                link_foto = upload_to_drive(
                    foto,
                    f"{st.session_state.nip}_{uid}.jpg"
                )

            sheet.append_row([
                uid,
                safe(st.session_state.nama),
                safe(st.session_state.nip),
                safe(st.session_state.jabatan),
                str(tgl),
                masuk,
                keluar,
                dur,
                uraian,
                output,
                lokasi,
                waktu_absen,
                koordinat,
                link_foto
            ])

            load_data.clear()
            st.success("Data berhasil disimpan")
            st.rerun()

# ================= DASHBOARD =================
elif menu == "Dashboard":

    st.subheader("Dashboard Kinerja")

    df = load_data()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    st.metric("Total Data", len(df))

    st.dataframe(df)

# ================= DATA =================
elif menu == "Data Kinerja":

    st.subheader("Data Kinerja")

    df = load_data()

    st.dataframe(df)

# ================= ADMIN =================
elif menu == "Admin":

    if st.session_state.role != "Admin":
        st.error("Tidak ada akses")
        st.stop()

    st.subheader("Admin Panel")

    st.dataframe(load_users())