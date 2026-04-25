# ======================================================
# APLIKASI E-KINERJA KPU KOTA BENGKULU
# FINAL VERSION - SIMPLE LOGIN (NO HASH)
# ======================================================

import streamlit as st
import pandas as pd
import io
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="E-Kinerja KPU Kota Bengkulu",
    layout="wide"
)

# ======================================================
# STYLE
# ======================================================
st.markdown("""
<style>
.block-container{padding-top:2rem;max-width:1400px;}
.titlex{font-size:32px;font-weight:800;text-align:center;color:#0f4c81;}
.card{background:white;padding:15px;border-radius:14px;
box-shadow:0 3px 10px rgba(0,0,0,.08);border-left:5px solid #0f4c81;}
</style>
""", unsafe_allow_html=True)

# ======================================================
# UTIL
# ======================================================
def safe(x):
    return "" if x is None else str(x)

# ======================================================
# GOOGLE SHEETS
# ======================================================
@st.cache_resource
def connect_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["connections"]["gsheets"]["service_account"],
        scopes=scope
    )

    client = gspread.authorize(creds)
    return client.open_by_key("16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM")

spreadsheet = connect_sheet()
sheet = spreadsheet.sheet1

# USERS SHEET
try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet("users", 100, 5)
    user_sheet.append_row(["NIP","Nama","Jabatan","Password","Role"])

# ======================================================
# DATA
# ======================================================
@st.cache_data(ttl=60)
def load_data():
    try:
        return pd.DataFrame(sheet.get_all_records())
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_users():
    try:
        return pd.DataFrame(user_sheet.get_all_records())
    except:
        return pd.DataFrame()

def get_data_with_index():
    df = load_data()
    if not df.empty:
        df["row_index"] = range(2, len(df)+2)
    return df

# ======================================================
# TIME
# ======================================================
def parse_jam(x):
    try:
        x = str(x).replace(".", ":").strip()
        if ":" not in x:
            return None
        h, m = x.split(":")
        h, m = int(h), int(m)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return h * 60 + m
    except:
        return None

def hitung_durasi(row):
    jm = parse_jam(row.get("Jam Masuk"))
    jk = parse_jam(row.get("Jam Keluar"))

    if jm is None or jk is None:
        return 0

    # support shift malam
    if jk < jm:
        jk += 24 * 60

    return round((jk - jm) / 60, 2)

# ======================================================
# SESSION
# ======================================================
if "login" not in st.session_state:
    st.session_state.login = False

# ======================================================
# LOGIN
# ======================================================
users = load_users()

if not st.session_state.login:

    st.markdown("<div class='titlex'>📊 E-Kinerja KPU Kota Bengkulu</div>", unsafe_allow_html=True)
    st.subheader("🔐 Login")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):

        if users.empty:
            st.error("Data user kosong")
            st.stop()

        cek = users[
            (users["NIP"].astype(str)==str(nip)) &
            (users["Password"].astype(str)==str(pw))
        ]

        if not cek.empty:
            u = cek.iloc[0]
            st.session_state.login = True
            st.session_state.nama = u["Nama"]
            st.session_state.nip = u["NIP"]
            st.session_state.jabatan = u["Jabatan"]
            st.session_state.role = u["Role"]
            st.rerun()
        else:
            st.error("Login gagal")

    st.stop()

# ======================================================
# HEADER
# ======================================================
st.markdown("<div class='titlex'>📊 E-Kinerja KPU Kota Bengkulu</div>", unsafe_allow_html=True)

col1,col2 = st.columns([8,2])
with col1:
    st.success(f"{st.session_state.nama} ({st.session_state.role})")
with col2:
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

# ======================================================
# MENU
# ======================================================
menu = st.sidebar.selectbox(
    "Menu",
    ["Dashboard","Input Kinerja","Data Kinerja","Admin"]
)

# ======================================================
# DASHBOARD
# ======================================================
if menu == "Dashboard":

    df = load_data()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    if st.session_state.role == "pegawai":
        df = df[df["NIP"].astype(str)==str(st.session_state.nip)]

    df["Durasi (Jam)"] = df.apply(hitung_durasi, axis=1)

    st.metric("Total Jam", round(df["Durasi (Jam)"].sum(),2))
    st.bar_chart(df.groupby("Nama")["Durasi (Jam)"].sum())

# ======================================================
# INPUT
# ======================================================
elif menu == "Input Kinerja":

    st.subheader("📝 Input Kinerja")

    with st.form("form"):

        tanggal = st.date_input("Tanggal", date.today())
        masuk = st.text_input("Jam Masuk","07:30")
        keluar = st.text_input("Jam Keluar","16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")
        lokasi = st.selectbox("Lokasi",["Kantor","Rumah","Dinas Luar / SPT"])

        simpan = st.form_submit_button("Simpan")

    if simpan:

        if uraian.strip()=="" or output.strip()=="":
            st.warning("Uraian & Output wajib diisi")
            st.stop()

        jm, jk = parse_jam(masuk), parse_jam(keluar)

        if jm is None or jk is None:
            st.error("Format jam salah")
            st.stop()

        # hitung durasi (support shift malam)
        durasi = round((jk-jm)/60,2) if jk >= jm else round(((jk+1440)-jm)/60,2)

        df = load_data()
        if not df.empty:
            cek = df[
                (df["NIP"].astype(str)==str(st.session_state.nip)) &
                (df["Tanggal"]==tanggal.strftime("%Y-%m-%d"))
            ]
            if not cek.empty:
                st.warning("Data hari ini sudah ada")
                st.stop()

        try:
            sheet.append_row([
                safe(st.session_state.nama),
                safe(st.session_state.nip),
                safe(st.session_state.jabatan),
                tanggal.strftime("%Y-%m-%d"),
                masuk, keluar, durasi,
                uraian, output, lokasi
            ])
            st.success("Data tersimpan")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Gagal simpan: {e}")

# ======================================================
# DATA KINERJA
# ======================================================
elif menu == "Data Kinerja":

    df = get_data_with_index()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    # FILTER
    if st.session_state.role == "pegawai":
        df = df[df["NIP"].astype(str)==str(st.session_state.nip)]

    elif st.session_state.role == "admin":
        opsi = st.selectbox("Filter",["Semua","Data Saya","Filter Nama"])
        if opsi == "Data Saya":
            df = df[df["NIP"].astype(str)==str(st.session_state.nip)]
        elif opsi == "Filter Nama":
            nama = st.selectbox("Nama", df["Nama"].unique())
            df = df[df["Nama"]==nama]

    df["Durasi (Jam)"] = df.apply(hitung_durasi, axis=1)

    st.subheader("📋 Data Kinerja")

    for i,row in df.iterrows():

        col1,col2,col3 = st.columns([6,2,2])

        with col1:
            st.write(f"**{row['Nama']}**")
            st.caption(f"{row['Tanggal']} | {row['Uraian']}")

        with col2:
            st.write(f"{row['Durasi (Jam)']} Jam")

        with col3:

            if st.button("✏️", key=f"edit{i}"):
                st.session_state.edit = True
                st.session_state.row = row

            if st.button("🗑", key=f"del{i}"):
                sheet.delete_rows(int(row["row_index"]))
                st.success("Dihapus")
                st.cache_data.clear()
                st.rerun()

    # EDIT
    if st.session_state.get("edit", False):

        ed = st.session_state.row

        st.subheader("Edit Data")

        masuk = st.text_input("Masuk", ed["Jam Masuk"])
        keluar = st.text_input("Keluar", ed["Jam Keluar"])
        uraian = st.text_area("Uraian", ed["Uraian"])
        output = st.text_area("Output", ed["Output"])

        if st.button("Simpan Perubahan"):

            jm, jk = parse_jam(masuk), parse_jam(keluar)

            if jm is None or jk is None:
                st.error("Jam salah")
                st.stop()

            durasi = round((jk-jm)/60,2) if jk>=jm else round(((jk+1440)-jm)/60,2)

            idx = int(ed["row_index"])

            sheet.update(
                f"E{idx}:J{idx}",
                [[masuk, keluar, durasi, uraian, output, ed["Lokasi"]]]
            )

            st.success("Update berhasil")
            st.session_state.edit = False
            st.cache_data.clear()
            st.rerun()

# ======================================================
# ADMIN
# ======================================================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    st.subheader("Tambah User")

    nip = st.text_input("NIP")
    nama = st.text_input("Nama")
    jabatan = st.text_input("Jabatan")
    pw = st.text_input("Password")
    role = st.selectbox("Role",["pegawai","admin"])

    if st.button("Tambah"):

        if nip=="" or pw=="":
            st.warning("NIP & Password wajib")
            st.stop()

        user_sheet.append_row([
            nip, nama, jabatan,
            pw,
            role
        ])

        st.success("User ditambahkan")
        st.cache_data.clear()
        st.rerun()

    st.subheader("Daftar User")
    st.dataframe(load_users(), use_container_width=True)