import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import io

# ================= CONFIG =================
st.set_page_config(page_title="E-Kinerja KPU", layout="wide")

# ================= UI PRO MAX =================
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background: #0f172a;
}
[data-testid="stSidebar"] * {
    color: white !important;
    font-weight: 500;
}

.stButton button {
    background: #ef4444;
    color: white;
    border-radius: 10px;
    font-weight: bold;
}

.card {
    padding:20px;
    border-radius:16px;
    color:white;
    text-align:center;
    font-weight:600;
}

.c1 {background: linear-gradient(135deg,#ef4444,#f87171);}
.c2 {background: linear-gradient(135deg,#22c55e,#4ade80);}
.c3 {background: linear-gradient(135deg,#f59e0b,#fbbf24);}
.c4 {background: linear-gradient(135deg,#3b82f6,#60a5fa);}

.box {
    background:white;
    padding:15px;
    border-radius:12px;
    margin-bottom:10px;
    box-shadow:0 3px 8px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

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
    client = gspread.authorize(creds)
    return client.open_by_key("16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM")

spreadsheet = connect()
sheet = spreadsheet.sheet1

try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet("users", 100, 5)
    user_sheet.append_row(["NIP","Nama","Jabatan","Password","Role"])

# ================= HELPER =================
def safe(x):
    return "" if x is None else str(x)

def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty:
        df["row"] = range(2, len(df)+2)
    return df

def load_users():
    return pd.DataFrame(user_sheet.get_all_records())

def parse_jam(x):
    try:
        h,m = str(x).replace(".",":").split(":")
        return int(h)*60 + int(m)
    except:
        return None

def durasi(row):
    jm = parse_jam(row["Jam Masuk"])
    jk = parse_jam(row["Jam Keluar"])
    if jm and jk and jk>jm:
        return round((jk-jm)/60,2)
    return 0

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
            st.session_state.nip = str(u["NIP"])
            st.session_state.jabatan = u["Jabatan"]
            st.session_state.role = u["Role"]
            st.rerun()
        else:
            st.error("Login gagal")

    st.stop()

# ================= SIDEBAR =================
st.sidebar.title(st.session_state.nama)
menu = st.sidebar.radio("Menu", ["Dashboard","Input","Data Kinerja","Admin"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "Dashboard":

    df = load_data()
    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(durasi, axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')

    # FILTER
    c1,c2,c3 = st.columns(3)
    with c1:
        tgl = st.date_input("Tanggal", value=(date.today(), date.today()))
    with c2:
        pegawai = st.multiselect("Pegawai", sorted(df["Nama"].unique()))
    with c3:
        lokasi = st.multiselect("Lokasi", sorted(df["Lokasi"].unique()))

    if len(tgl)==2:
        df = df[(df["Tanggal"]>=pd.to_datetime(tgl[0])) & (df["Tanggal"]<=pd.to_datetime(tgl[1]))]
    if pegawai:
        df = df[df["Nama"].isin(pegawai)]
    if lokasi:
        df = df[df["Lokasi"].isin(lokasi)]

    total = len(df)
    jam = round(df["Durasi"].sum(),2)
    hari = df["Tanggal"].nunique()
    peg = df["Nama"].nunique()

    k1,k2,k3,k4 = st.columns(4)
    k1.markdown(f"<div class='card c1'><h2>{total}</h2>Total</div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='card c2'><h2>{jam:.2f}</h2>Jam</div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='card c3'><h2>{hari}</h2>Hari</div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='card c4'><h2>{peg}</h2>Pegawai</div>", unsafe_allow_html=True)

    # GRAFIK + RANKING
    col1,col2 = st.columns(2)

    with col1:
        st.subheader("📊 Durasi per Pegawai")
        st.bar_chart(df.groupby("Nama")["Durasi"].sum())

    with col2:
        st.subheader("🏆 Top Pegawai")
        top = df.groupby("Nama")["Durasi"].sum().sort_values(ascending=False).head(5)
        st.dataframe(top)

    # KEGIATAN TERBARU
    st.subheader("🕒 Kegiatan Terbaru")
    latest = df.sort_values("Tanggal", ascending=False).head(5)
    for _,r in latest.iterrows():
        st.markdown(f"""
        <div class='box'>
        <b>{r['Tanggal'].date()}</b><br>
        {r['Uraian']}<br>
        ⏱ {r['Durasi']:.2f} jam
        </div>
        """, unsafe_allow_html=True)

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
        jm = parse_jam(masuk)
        jk = parse_jam(keluar)

        if not jm or not jk or jk<=jm:
            st.error("Jam tidak valid")
            st.stop()

        dur = round((jk-jm)/60,2)

        sheet.append_row([
            safe(st.session_state.nama),
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
    df["Durasi"] = df.apply(durasi, axis=1)

    if st.session_state.role in ["admin","pimpinan"]:
        mode = st.radio("Mode", ["Semua Data","Data Saya"])
        if mode == "Data Saya":
            df = df[df["NIP"].astype(str)==st.session_state.nip]
    else:
        df = df[df["NIP"].astype(str)==st.session_state.nip]

    for i,row in df.iterrows():
        c1,c2,c3 = st.columns([6,2,2])

        c1.write(f"**{row['Nama']}** - {row['Tanggal']}")
        c1.caption(row["Uraian"])
        c2.write(f"{row['Durasi']:.2f} jam")

        if st.session_state.role != "pegawai":
            if c3.button("🗑", key=i):
                sheet.delete_rows(int(row["row"]))
                st.rerun()

    excel = io.BytesIO()
    df.to_excel(excel, index=False)
    st.download_button("📥 Download Excel", excel.getvalue(), "data.xlsx")

# ================= ADMIN =================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    st.subheader("Tambah User")

    nip = st.text_input("NIP")
    nama = st.text_input("Nama")
    jabatan = st.text_input("Jabatan")
    pw = st.text_input("Password")
    role = st.selectbox("Role", ["pegawai","admin","pimpinan"])

    if st.button("Tambah"):
        user_sheet.append_row([nip,nama,jabatan,pw,role])
        st.success("User ditambah")