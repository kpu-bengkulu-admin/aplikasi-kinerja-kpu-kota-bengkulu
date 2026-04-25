# ======================================================
# E-KINERJA KPU KOTA BENGKULU (FINAL UI PRO)
# ======================================================

import streamlit as st
import pandas as pd
import io
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="E-Kinerja KPU", layout="wide")

# ======================================================
# CSS PRO
# ======================================================
st.markdown("""
<style>
body {background:#f4f6f9;}

section[data-testid="stSidebar"]{
    background: linear-gradient(180deg,#0d1b2a,#1b263b);
}
section[data-testid="stSidebar"] *{
    color:white !important;
}

.header-banner{
    background: linear-gradient(90deg,#ffffff 50%,#e63946 100%);
    padding:20px;
    border-radius:16px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:20px;
}

.card{
    background:white;
    padding:20px;
    border-radius:16px;
    box-shadow:0 6px 14px rgba(0,0,0,0.08);
    text-align:center;
}

.activity{
    background:white;
    padding:12px;
    border-radius:12px;
    margin-bottom:10px;
    box-shadow:0 2px 6px rgba(0,0,0,.05);
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# SAFE
# ======================================================
def safe(x):
    if x is None:
        return ""
    try:
        return str(x)
    except:
        return ""

# ======================================================
# GOOGLE SHEETS
# ======================================================
@st.cache_resource
def connect():
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

spreadsheet = connect()
sheet = spreadsheet.sheet1

# USERS
try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet("users", 100, 5)
    user_sheet.append_row(["NIP","Nama","Jabatan","Password","Role"])

# ======================================================
# LOAD
# ======================================================
@st.cache_data(ttl=60)
def load_data():
    return pd.DataFrame(sheet.get_all_records())

@st.cache_data(ttl=60)
def load_users():
    return pd.DataFrame(user_sheet.get_all_records())

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
        x = str(x).replace(".",":")
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

users = load_users()

# ======================================================
# LOGIN
# ======================================================
if not st.session_state.login:

    st.title("📊 E-Kinerja KPU Kota Bengkulu")

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
# HEADER
# ======================================================
today = datetime.now().strftime("%A, %d %B %Y")

st.markdown(f"""
<div class="header-banner">
    <div>
        <b style="font-size:28px;">Aplikasi <span style="color:red;">E-Kinerja</span></b><br>
        <small>KPU Kota Bengkulu</small>
    </div>
    <div>📅 {today}</div>
</div>
""", unsafe_allow_html=True)

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

    c1,c2,c3,c4 = st.columns(4)

    c1.markdown(f"<div class='card'><h4>Total</h4><h2>{total}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><h4>Jam</h4><h2>{jam}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><h4>Hari</h4><h2>{hari}</h2></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card'><h4>Lokasi</h4><h2>{lokasi}</h2></div>", unsafe_allow_html=True)

    col1,col2 = st.columns([2,1])

    with col1:
        st.bar_chart(df.groupby("Nama")["Durasi (Jam)"].sum())

    with col2:
        latest = df.sort_values("Tanggal", ascending=False).head(5)
        for _,r in latest.iterrows():
            st.markdown(f"""
            <div class='activity'>
            <b>{r['Tanggal']}</b><br>
            {r['Uraian']}<br>
            <b>{r['Durasi (Jam)']} jam</b>
            </div>
            """, unsafe_allow_html=True)

# ======================================================
# INPUT KINERJA (FIX CLEAR FORM)
# ======================================================
elif menu == "Input Kinerja":

    with st.form("form_input", clear_on_submit=True):

        tgl = st.date_input("Tanggal", date.today())
        masuk = st.text_input("Jam Masuk","07:30")
        keluar = st.text_input("Jam Keluar","16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")
        lokasi = st.selectbox("Lokasi",["Kantor","Rumah","Dinas Luar / SPT"])

        simpan = st.form_submit_button("💾 Simpan")

    if simpan:

        jm = parse_jam(masuk)
        jk = parse_jam(keluar)

        if jm is None or jk is None:
            st.error("Format jam salah")
            st.stop()

        durasi = hitung_durasi({"Jam Masuk":masuk,"Jam Keluar":keluar})

        row = [
            st.session_state.nama,
            st.session_state.nip,
            "",
            tgl.strftime("%Y-%m-%d"),
            masuk,
            keluar,
            float(durasi),
            uraian,
            output,
            lokasi
        ]

        row = [safe(x) for x in row]

        sheet.append_row(row)

        st.success("✅ Data berhasil disimpan")
        st.cache_data.clear()

# ======================================================
# DATA KINERJA
# ======================================================
elif menu == "Data Kinerja":

    df = get_data_with_index()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

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
            st.success("Dihapus")
            st.cache_data.clear()
            st.rerun()

        st.divider()

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
        user_sheet.append_row([nip,nama,jabatan,pw,role])
        st.success("User ditambah")
        st.rerun()

    st.dataframe(load_users())