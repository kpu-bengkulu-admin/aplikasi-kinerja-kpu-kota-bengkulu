import streamlit as st
import pandas as pd
import io
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# ================= CONFIG =================
st.set_page_config(page_title="E-Kinerja KPU Bengkulu", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
section[data-testid="stSidebar"]{
    background:#0f172a;
    color:white;
}
.sidebar .sidebar-content {color:white;}
.stButton>button{
    background:#ef4444;
    color:white;
    border-radius:8px;
    border:none;
}
.card{
    background:white;
    padding:20px;
    border-radius:16px;
    box-shadow:0 4px 12px rgba(0,0,0,.08);
}
</style>
""", unsafe_allow_html=True)

# ================= GOOGLE SHEET =================
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
    user_sheet = spreadsheet.add_worksheet("users",100,5)
    user_sheet.append_row(["NIP","Nama","Jabatan","Password","Role"])

# ================= FUNCTION =================
def safe(x): return "" if x is None else str(x)

def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    return df

def load_users():
    return pd.DataFrame(user_sheet.get_all_records())

def parse_jam(x):
    try:
        x=str(x).replace(".",":")
        h,m = map(int,x.split(":"))
        return h*60+m
    except:
        return None

def durasi(row):
    jm = parse_jam(row["Jam Masuk"])
    jk = parse_jam(row["Jam Keluar"])
    if jm is None or jk is None or jk<=jm:
        return 0
    return round((jk-jm)/60,2)

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login=False

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
            u=cek.iloc[0]
            st.session_state.login=True
            st.session_state.nama=u["Nama"]
            st.session_state.nip=str(u["NIP"])
            st.session_state.jabatan=u["Jabatan"]
            st.session_state.role=u["Role"]
            st.rerun()
        else:
            st.error("Login gagal")

    st.stop()

# ================= SIDEBAR =================
st.sidebar.title(st.session_state.nama)
menu = st.sidebar.radio("Menu",
["Dashboard","Input Kinerja","Data Kinerja","Admin"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= LOAD =================
df = load_data()
if not df.empty:
    df["NIP"] = df["NIP"].astype(str)
    df["Durasi"] = df.apply(durasi, axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"])

# ================= DASHBOARD =================
if menu=="Dashboard":

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    if st.session_state.role=="pegawai":
        df = df[df["NIP"]==st.session_state.nip]

    # FILTER
    f1,f2,f3 = st.columns(3)

    with f1:
        tgl = st.date_input("Tanggal",
            [df["Tanggal"].min(), df["Tanggal"].max()])

    with f2:
        pegawai = st.multiselect("Pegawai",
            df["Nama"].unique(),
            default=df["Nama"].unique())

    with f3:
        lokasi = st.multiselect("Lokasi",
            df["Lokasi"].unique(),
            default=df["Lokasi"].unique())

    df = df[
        (df["Tanggal"]>=pd.to_datetime(tgl[0])) &
        (df["Tanggal"]<=pd.to_datetime(tgl[1])) &
        (df["Nama"].isin(pegawai)) &
        (df["Lokasi"].isin(lokasi))
    ]

    # KPI
    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Total", len(df))
    c2.metric("Jam", round(df["Durasi"].sum(),2))
    c3.metric("Hari", df["Tanggal"].nunique())
    c4.metric("Pegawai", df["Nama"].nunique())

    st.divider()

    # CHART
    col1,col2 = st.columns(2)

    with col1:
        bar = df.groupby("Nama")["Durasi"].sum().reset_index()
        fig = px.bar(bar,x="Nama",y="Durasi",text_auto=True,color="Durasi")
        st.plotly_chart(fig,use_container_width=True)

    with col2:
        pie = px.pie(df,names="Lokasi")
        st.plotly_chart(pie,use_container_width=True)

    trend = df.groupby("Tanggal")["Durasi"].sum().reset_index()
    fig2 = px.line(trend,x="Tanggal",y="Durasi",markers=True)
    st.plotly_chart(fig2,use_container_width=True)

# ================= INPUT =================
elif menu=="Input Kinerja":

    with st.form("form", clear_on_submit=True):

        tgl = st.date_input("Tanggal", date.today())
        masuk = st.text_input("Jam Masuk","07:30")
        keluar = st.text_input("Jam Keluar","16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")

        lokasi = st.selectbox("Lokasi",
        ["Kantor","Rumah","Dinas Luar / SPT"])

        submit = st.form_submit_button("Simpan")

    if submit:

        jm = parse_jam(masuk)
        jk = parse_jam(keluar)

        if jm is None or jk is None or jk<=jm:
            st.error("Jam salah")
            st.stop()

        dur = round((jk-jm)/60,2)

        sheet.append_row([
            safe(st.session_state.nama),
            safe(st.session_state.nip),
            safe(st.session_state.jabatan),
            safe(tgl.strftime("%Y-%m-%d")),
            safe(masuk),
            safe(keluar),
            float(dur),
            safe(uraian),
            safe(output),
            safe(lokasi)
        ])

        st.success("Data tersimpan")
        st.rerun()

# ================= DATA =================
elif menu=="Data Kinerja":

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    if st.session_state.role=="pegawai":
        df = df[df["NIP"]==st.session_state.nip]

    st.dataframe(df,use_container_width=True)

    # DOWNLOAD
    excel = io.BytesIO()
    df.to_excel(excel,index=False)

    st.download_button("Download Excel",excel.getvalue(),
    "kinerja.xlsx")

# ================= ADMIN =================
elif menu=="Admin":

    if st.session_state.role!="admin":
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