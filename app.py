import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import io
import plotly.express as px
import base64
import os

# ================= CONFIG =================
st.set_page_config(page_title="E-Kinerja KPU Kota Bengkulu", layout="wide")

# ================= UI =================
st.markdown("""
<style>
[data-testid="stSidebar"] {background:#0f172a;}
[data-testid="stSidebar"] * {color:white !important;}

.stButton button {
    background:#ef4444;
    color:white;
    border-radius:10px;
}

.card {
    padding:18px;
    border-radius:14px;
    color:white;
    text-align:center;
}

.c1{background:#ef4444;}
.c2{background:#22c55e;}
.c3{background:#f59e0b;}
.c4{background:#3b82f6;}

.sidebar-user {
    text-align:center;
    padding:20px 10px;
    border-bottom:1px solid rgba(255,255,255,0.1);
}
</style>
""", unsafe_allow_html=True)

# ================= HELPER =================
def get_base64(file):
    path = os.path.join(os.getcwd(), file)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def safe(x):
    return "" if x is None else str(x)

def parse_jam(x):
    try:
        h, m = str(x).replace(".", ":").split(":")
        return int(h) * 60 + int(m)
    except:
        return None

def hitung_durasi(masuk, keluar):
    jm = parse_jam(masuk)
    jk = parse_jam(keluar)
    if jm and jk and jk > jm:
        return round((jk - jm) / 60, 2)
    return 0

# ================= GOOGLE =================
@st.cache_resource
def connect():
    creds = Credentials.from_service_account_info(
        st.secrets["connections"]["gsheets"]["service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )
    return gspread.authorize(creds).open_by_key(
        "16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM"
    )

spreadsheet = connect()
sheet = spreadsheet.sheet1

try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet("users", 100, 5)
    user_sheet.append_row(["NIP","Nama","Jabatan","Password","Role"])

def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty:
        df["row"] = range(2, len(df)+2)
    return df

def load_users():
    return pd.DataFrame(user_sheet.get_all_records())

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login = False

users = load_users()

if not st.session_state.login:
    st.title("🔐 Login E-Kinerja KPU Kota Bengkulu")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        cek = users[
            (users["NIP"].astype(str) == str(nip)) &
            (users["Password"].astype(str) == str(pw))
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

# ================= SIDEBAR =================
nama = st.session_state.nama
role = st.session_state.role

role_color = {
    "admin": "#ef4444",
    "pimpinan": "#22c55e",
    "pegawai": "#3b82f6"
}.get(role, "#999")

st.sidebar.markdown(f"""
<div class='sidebar-user'>
    <h3>{nama}</h3>
    <div style='background:{role_color};padding:5px;border-radius:8px;font-size:12px'>
        {role.upper()}
    </div>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("", ["Dashboard","Input","Data Kinerja","Admin"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "Dashboard":

    logo = get_base64("logo.png")
    gedung = get_base64("gedung.png")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#ef4444,#f87171);
    padding:25px;border-radius:15px;color:white;
    display:flex;align-items:center;gap:20px;position:relative;overflow:hidden">

        <img src="data:image/png;base64,{gedung}"
             style="position:absolute;right:0;bottom:0;width:280px;opacity:0.12">

        <img src="data:image/png;base64,{logo}" style="width:65px;z-index:2">

        <div style="z-index:2">
            <h2 style="margin:0">Aplikasi E-Kinerja</h2>
            <p style="margin:0">{nama} - KPU Kota Bengkulu</p>
        </div>

    </div>
    """, unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')

    df["Lokasi"] = df["Lokasi"].replace({"Dinas": "Dinas Luar / SPT"})

    col1,col2,col3 = st.columns(3)

    with col1:
        tgl = st.date_input("Range Tanggal", value=(df["Tanggal"].min(), df["Tanggal"].max()))

    with col2:
        pegawai = st.multiselect("Pegawai", sorted(df["Nama"].unique()))

    with col3:
        lokasi = st.multiselect("Lokasi", sorted(df["Lokasi"].unique()))

    if len(tgl)==2:
        df = df[(df["Tanggal"]>=pd.to_datetime(tgl[0])) & (df["Tanggal"]<=pd.to_datetime(tgl[1]))]

    if pegawai:
        df = df[df["Nama"].isin(pegawai)]

    if lokasi:
        df = df[df["Lokasi"].isin(lokasi)]

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='card c1'><h2>{len(df)}</h2>Total</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card c2'><h2>{df['Durasi'].sum():.2f}</h2>Jam</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card c3'><h2>{df['Tanggal'].nunique()}</h2>Hari</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card c4'><h2>{df['Nama'].nunique()}</h2>Pegawai</div>", unsafe_allow_html=True)

    chart = df.groupby("Nama")["Durasi"].sum().reset_index()

    fig = px.bar(chart, x="Nama", y="Durasi", color="Durasi", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

# ================= INPUT =================
elif menu == "Input":

    with st.form("form", clear_on_submit=True):
        tgl = st.date_input("Tanggal")
        masuk = st.text_input("Jam Masuk","07:30")
        keluar = st.text_input("Jam Keluar","16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")
        lokasi = st.selectbox("Lokasi", ["Kantor","Rumah","Dinas Luar / SPT"])

        submit = st.form_submit_button("Simpan")

    if submit:
        dur = hitung_durasi(masuk, keluar)
        if dur == 0:
            st.error("Jam tidak valid")
            st.stop()

        sheet.append_row([
            safe(nama),
            safe(str(st.session_state.nip)),
            safe(st.session_state.jabatan),
            safe(tgl.strftime("%Y-%m-%d")),
            safe(masuk),
            safe(keluar),
            dur,
            safe(uraian),
            safe(output),
            safe(lokasi)
        ])

        st.success("✅ Data tersimpan")

# ================= DATA =================
elif menu == "Data Kinerja":

    df = load_data()
    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')

    if role in ["admin","pimpinan"]:
        mode = st.radio("Mode Data", ["Semua Data","Data Saya"])
        if mode == "Data Saya":
            df = df[df["NIP"].astype(str)==st.session_state.nip]
    else:
        df = df[df["NIP"].astype(str)==st.session_state.nip]

    tgl = st.date_input("Filter Tanggal", value=(df["Tanggal"].min(), df["Tanggal"].max()))

    if len(tgl)==2:
        df = df[(df["Tanggal"]>=pd.to_datetime(tgl[0])) & (df["Tanggal"]<=pd.to_datetime(tgl[1]))]

    for i,row in df.iterrows():
        c1,c2,c3,c4 = st.columns([5,2,1,1])
        c1.write(f"**{row['Nama']}** - {row['Tanggal'].date()}")
        c1.caption(row["Uraian"])
        c2.write(f"{row['Durasi']:.2f} jam")

        if c3.button("✏️", key=f"edit{i}"):
            st.session_state.edit = row

        if c4.button("🗑", key=f"del{i}"):
            sheet.delete_rows(int(row["row"]))
            st.rerun()

    excel = io.BytesIO()
    df.to_excel(excel, index=False)
    st.download_button("📥 Download Excel", excel.getvalue())

# ================= ADMIN =================
elif menu == "Admin":

    if role != "admin":
        st.error("Akses ditolak")
        st.stop()

    nip = st.text_input("NIP")
    nama_u = st.text_input("Nama")
    jab = st.text_input("Jabatan")
    pw = st.text_input("Password")
    role_u = st.selectbox("Role", ["pegawai","admin","pimpinan"])

    if st.button("Tambah User"):
        user_sheet.append_row([nip,nama_u,jab,pw,role_u])
        st.success("User ditambahkan")