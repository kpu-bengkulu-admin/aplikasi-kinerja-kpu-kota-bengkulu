import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIG =================
st.set_page_config(page_title="E-Kinerja KPU", layout="wide")

# ================= CSS PRO =================
st.markdown("""
<style>

body {background:#f4f6f9;}

[data-testid="stSidebar"] {
    background:#0b1c2c;
    color:white;
}

.sidebar-title {
    font-size:20px;
    font-weight:bold;
    margin-bottom:20px;
}

.header-box {
    background: linear-gradient(90deg,#ff4b2b,#ff416c);
    padding:25px;
    border-radius:15px;
    color:white;
}

.card-red {border-top:5px solid #ff4b4b;}
.card-green {border-top:5px solid #28a745;}
.card-yellow {border-top:5px solid #ffc107;}
.card-blue {border-top:5px solid #007bff;}

.card {
    background:white;
    padding:20px;
    border-radius:15px;
    text-align:center;
    box-shadow:0 4px 10px rgba(0,0,0,0.1);
}

.big {font-size:30px; font-weight:bold;}
.small {color:#666;}

.activity {
    background:white;
    padding:15px;
    border-radius:10px;
    margin-bottom:10px;
    box-shadow:0 2px 6px rgba(0,0,0,0.1);
}

</style>
""", unsafe_allow_html=True)

# ================= GOOGLE =================
@st.cache_resource
def connect():
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

spreadsheet = connect()
sheet = spreadsheet.sheet1

try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet("users", 100, 5)
    user_sheet.append_row(["NIP","Nama","Jabatan","Password","Role"])

# ================= UTIL =================
def safe(x):
    return "" if x is None else str(x)

def load_data():
    try:
        return pd.DataFrame(sheet.get_all_records())
    except:
        return pd.DataFrame()

def load_users():
    try:
        return pd.DataFrame(user_sheet.get_all_records())
    except:
        return pd.DataFrame()

def parse_jam(x):
    try:
        x = str(x).replace(".",":")
        h,m = map(int,x.split(":"))
        return h*60+m
    except:
        return None

def hitung_durasi(row):
    jm = parse_jam(row["Jam Masuk"])
    jk = parse_jam(row["Jam Keluar"])
    if jm is None or jk is None or jk <= jm:
        return 0
    return round((jk-jm)/60,2)

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

# ================= SIDEBAR ROLE BASED =================
st.sidebar.markdown(f"### 👤 {st.session_state.nama}")

if st.session_state.role == "pegawai":
    menu = st.sidebar.radio("Menu", ["Dashboard","Input","Data"])
else:
    menu = st.sidebar.radio("Menu", ["Dashboard","Input","Data","Admin"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "Dashboard":

    df = load_data()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    if st.session_state.role == "pegawai":
        df = df[df["NIP"].astype(str)==str(st.session_state.nip)]

    df["Durasi"] = df.apply(hitung_durasi, axis=1)

    total = len(df)
    jam = df["Durasi"].sum()
    hari = df["Tanggal"].nunique()
    lokasi = df["Lokasi"].mode()[0]

    st.markdown(f"""
    <div class='header-box'>
        <h2>Selamat datang, {st.session_state.nama}</h2>
        <p>{datetime.now().strftime("%A, %d %B %Y")}</p>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)

    c1.markdown(f"<div class='card card-red'><div class='big'>{total}</div><div>Total Kegiatan</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card card-green'><div class='big'>{round(jam,2)}</div><div>Total Jam</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card card-yellow'><div class='big'>{hari}</div><div>Hari Aktif</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card card-blue'><div class='big'>{lokasi}</div><div>Lokasi</div></div>", unsafe_allow_html=True)

    col1,col2 = st.columns([2,1])

    with col1:
        st.subheader("Grafik Durasi")
        st.bar_chart(df.groupby("Nama")["Durasi"].sum())

    with col2:
        st.subheader("Kegiatan Terbaru")
        latest = df.sort_values("Tanggal", ascending=False).head(5)
        for _,r in latest.iterrows():
            st.markdown(f"""
            <div class='activity'>
            <b>{r['Tanggal']}</b><br>
            {r['Uraian']}<br>
            <b>{r['Durasi']} jam</b>
            </div>
            """, unsafe_allow_html=True)

# ================= INPUT =================
elif menu == "Input":

    st.subheader("Input Kinerja")

    with st.form("form", clear_on_submit=True):
        tanggal = st.date_input("Tanggal", date.today())
        masuk = st.text_input("Jam Masuk","07:30")
        keluar = st.text_input("Jam Keluar","16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")

        lokasi = st.selectbox("Lokasi",[
            "Kantor",
            "Rumah",
            "Dinas Luar / SPT"
        ])

        simpan = st.form_submit_button("Simpan")

    if simpan:
        jm = parse_jam(masuk)
        jk = parse_jam(keluar)

        if jm is None or jk is None:
            st.error("Format jam salah")
        elif jk <= jm:
            st.error("Jam keluar harus lebih besar")
        else:
            durasi = round((jk-jm)/60,2)

            sheet.append_row([
                safe(st.session_state.nama),
                safe(st.session_state.nip),
                safe(st.session_state.jabatan),
                safe(tanggal.strftime("%Y-%m-%d")),
                safe(masuk),
                safe(keluar),
                float(durasi),
                safe(uraian),
                safe(output),
                safe(lokasi)
            ])

            st.success("✅ Data berhasil disimpan")

# ================= DATA =================
elif menu == "Data":

    df = load_data()
    df["Durasi"] = df.apply(hitung_durasi, axis=1)

    if st.session_state.role == "pegawai":
        df = df[df["NIP"].astype(str)==str(st.session_state.nip)]
    else:
        mode = st.radio("Mode",["Semua Data","Data Saya"])
        if mode == "Data Saya":
            df = df[df["NIP"].astype(str)==str(st.session_state.nip)]

    st.dataframe(df)

# ================= ADMIN =================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    nip = st.text_input("NIP")
    nama = st.text_input("Nama")
    jabatan = st.text_input("Jabatan")
    pw = st.text_input("Password")
    role = st.selectbox("Role",["pegawai","admin","pimpinan"])

    if st.button("Tambah"):
        user_sheet.append_row([nip,nama,jabatan,pw,role])
        st.success("User ditambah")