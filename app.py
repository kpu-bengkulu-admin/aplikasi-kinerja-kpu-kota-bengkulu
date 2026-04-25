# ======================================================
# E-KINERJA KPU KOTA BENGKULU
# FINAL VERSION (UI UPGRADE + FULL FITUR)
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
st.set_page_config(page_title="E-Kinerja KPU", layout="wide")

# ======================================================
# CSS UI UPGRADE
# ======================================================
st.markdown("""
<style>

body {background-color:#f4f6f9;}

section[data-testid="stSidebar"] {
    background:#0d1b2a;
}
section[data-testid="stSidebar"] * {
    color:white !important;
}

.title-main {
    font-size:38px;
    font-weight:800;
    text-align:center;
    margin-bottom:20px;
}

.card {
    background:white;
    padding:22px;
    border-radius:18px;
    box-shadow:0 6px 14px rgba(0,0,0,0.08);
    text-align:center;
}

.card-red {border-top:5px solid #e63946;}
.card-green {border-top:5px solid #2a9d8f;}
.card-orange {border-top:5px solid #f4a261;}
.card-blue {border-top:5px solid #4361ee;}

.activity {
    background:white;
    padding:12px;
    border-radius:10px;
    margin-bottom:10px;
    box-shadow:0 2px 6px rgba(0,0,0,.05);
}

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
    creds = Credentials.from_service_account_info(
        st.secrets["connections"]["gsheets"]["service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return gspread.authorize(creds).open_by_key(
        "16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM"
    )

spreadsheet = connect_sheet()
sheet = spreadsheet.sheet1

# USERS
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
        x = str(x).replace(".", ":")
        h,m = map(int,x.split(":"))
        return h*60+m
    except:
        return None

def hitung_durasi(row):
    jm = parse_jam(row.get("Jam Masuk"))
    jk = parse_jam(row.get("Jam Keluar"))

    if jm is None or jk is None:
        return 0

    if jk < jm:
        jk += 1440

    return round((jk-jm)/60,2)

# ======================================================
# SESSION
# ======================================================
if "login" not in st.session_state:
    st.session_state.login = False

# ======================================================
# LOGIN (NO HASH)
# ======================================================
users = load_users()

if not st.session_state.login:

    st.markdown("<div class='title-main'>📊 E-Kinerja KPU Kota Bengkulu</div>", unsafe_allow_html=True)

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):

        cek = users[
            (users["NIP"].astype(str)==str(nip)) &
            (users["Password"].astype(str)==str(pw))
        ]

        if not cek.empty:
            u = cek.iloc[0]
            st.session_state.login = True
            st.session_state.nama = u["Nama"]
            st.session_state.nip = u["NIP"]
            st.session_state.role = u["Role"]
            st.rerun()
        else:
            st.error("Login gagal")

    st.stop()

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.markdown(f"### 👤 {st.session_state.nama}")
menu = st.sidebar.radio("Menu",[
    "Dashboard","Input Kinerja","Data Kinerja","Admin"
])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ======================================================
# DASHBOARD
# ======================================================
if menu == "Dashboard":

    df = load_data()

    if st.session_state.role == "pegawai":
        df = df[df["NIP"].astype(str)==str(st.session_state.nip)]

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi (Jam)"] = df.apply(hitung_durasi, axis=1)

    total = len(df)
    jam = round(df["Durasi (Jam)"].sum(),2)
    hari = df["Tanggal"].nunique()
    lokasi = df["Lokasi"].mode()[0]

    st.markdown(f"""
    <div class="title-main">
        Selamat datang, <span style='color:#e63946'>{st.session_state.nama}</span>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)

    c1.markdown(f"<div class='card card-red'><h4>Total Kegiatan</h4><h2>{total}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card card-green'><h4>Total Jam</h4><h2>{jam}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card card-orange'><h4>Hari Aktif</h4><h2>{hari}</h2></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card card-blue'><h4>Lokasi</h4><h2>{lokasi}</h2></div>", unsafe_allow_html=True)

    col1, col2 = st.columns([2,1])

    with col1:
        st.subheader("📊 Grafik Kinerja")
        st.bar_chart(df.groupby("Nama")["Durasi (Jam)"].sum())

    with col2:
        st.subheader("📝 Kegiatan Terbaru")
        latest = df.sort_values("Tanggal", ascending=False).head(5)
        for _, r in latest.iterrows():
            st.markdown(f"""
            <div class="activity">
                <b>{r['Tanggal']}</b><br>
                {r['Uraian']}<br>
                <span style="color:#2a9d8f">{r['Durasi (Jam)']} jam</span>
            </div>
            """, unsafe_allow_html=True)

# ======================================================
# INPUT KINERJA
# ======================================================
elif menu == "Input Kinerja":

    with st.form("form"):

        tgl = st.date_input("Tanggal", date.today())
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

        jm = parse_jam(masuk)
        jk = parse_jam(keluar)

        if jm is None or jk is None:
            st.error("Format jam salah")
            st.stop()

        durasi = hitung_durasi({"Jam Masuk":masuk,"Jam Keluar":keluar})

        df = load_data()
        if not df.empty:
            cek = df[
                (df["NIP"].astype(str)==str(st.session_state.nip)) &
                (df["Tanggal"]==tgl.strftime("%Y-%m-%d"))
            ]
            if not cek.empty:
                st.warning("Data hari ini sudah ada")
                st.stop()

        sheet.append_row([
            st.session_state.nama,
            st.session_state.nip,
            "",
            tgl.strftime("%Y-%m-%d"),
            masuk, keluar, durasi,
            uraian, output, lokasi
        ])

        st.success("Data tersimpan")
        st.cache_data.clear()
        st.rerun()

# ======================================================
# DATA KINERJA (FULL FITUR)
# ======================================================
elif menu == "Data Kinerja":

    df = get_data_with_index()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    if st.session_state.role == "pegawai":
        df = df[df["NIP"].astype(str)==str(st.session_state.nip)]

    elif st.session_state.role == "admin":
        opsi = st.selectbox("Filter",["Semua","Data Saya","Filter Nama"])
        if opsi == "Data Saya":
            df = df[df["NIP"].astype(str)==str(st.session_state.nip)]
        elif opsi == "Filter Nama":
            nama = st.selectbox("Nama",df["Nama"].unique())
            df = df[df["Nama"]==nama]

    df["Durasi (Jam)"] = df.apply(hitung_durasi, axis=1)

    for i,row in df.iterrows():

        c1,c2,c3 = st.columns([6,2,2])

        c1.write(f"**{row['Nama']}**")
        c1.caption(f"{row['Tanggal']} | {row['Uraian']}")

        c2.write(f"{row['Durasi (Jam)']} jam")

        if c3.button("✏️", key=f"edit{i}"):
            st.session_state.edit = True
            st.session_state.row = row

        if c3.button("🗑", key=f"del{i}"):
            sheet.delete_rows(int(row["row_index"]))
            st.success("Data dihapus")
            st.cache_data.clear()
            st.rerun()

        st.divider()

    # EDIT
    if st.session_state.get("edit", False):

        ed = st.session_state.row

        masuk = st.text_input("Masuk", ed["Jam Masuk"])
        keluar = st.text_input("Keluar", ed["Jam Keluar"])
        uraian = st.text_area("Uraian", ed["Uraian"])
        output = st.text_area("Output", ed["Output"])

        if st.button("Simpan Perubahan"):

            durasi = hitung_durasi({
                "Jam Masuk":masuk,
                "Jam Keluar":keluar
            })

            idx = int(ed["row_index"])

            sheet.update(
                f"E{idx}:J{idx}",
                [[masuk, keluar, durasi, uraian, output, ed["Lokasi"]]]
            )

            st.success("Berhasil update")
            st.session_state.edit = False
            st.cache_data.clear()
            st.rerun()

    # DOWNLOAD EXCEL
    excel = io.BytesIO()
    df.drop(columns=["row_index"]).to_excel(excel, index=False)

    st.download_button(
        "📥 Download Excel",
        excel.getvalue(),
        file_name="rekap_kinerja.xlsx"
    )

# ======================================================
# ADMIN
# ======================================================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    nip = st.text_input("NIP")
    nama = st.text_input("Nama")
    jabatan = st.text_input("Jabatan")
    pw = st.text_input("Password")
    role = st.selectbox("Role",["pegawai","admin"])

    if st.button("Tambah User"):

        user_sheet.append_row([
            nip,nama,jabatan,pw,role
        ])

        st.success("User ditambahkan")
        st.cache_data.clear()
        st.rerun()

    st.dataframe(load_users(), use_container_width=True)