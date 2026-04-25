import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import io

# ================= CONFIG =================
st.set_page_config(page_title="E-Kinerja KPU Kota Bengkulu", layout="wide")

# ================= UI =================
st.markdown("""
<style>
[data-testid="stSidebar"] {background:#0f172a;}
[data-testid="stSidebar"] * {color:white !important;}
.stButton button {background:#ef4444;color:white;border-radius:8px;}
.card {padding:15px;border-radius:12px;color:white;text-align:center;}
.c1{background:#ef4444;} .c2{background:#22c55e;}
.c3{background:#f59e0b;} .c4{background:#3b82f6;}
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

# ================= HELPER =================
def safe(x): return "" if x is None else str(x)

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

def hitung_durasi(masuk, keluar):
    jm = parse_jam(masuk)
    jk = parse_jam(keluar)
    if jm and jk and jk > jm:
        return round((jk-jm)/60,2)
    return 0

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login=False

users = load_users()

if not st.session_state.login:
    st.title("🔐 Login E-Kinerja KPU Kota Bengkulu")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        cek = users[
            (users["NIP"].astype(str)==str(nip)) &
            (users["Password"].astype(str)==str(pw))
        ]
        if not cek.empty:
            u = cek.iloc[0]
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

    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')

    # RANGE OTOMATIS (FIX)
    start_default = df["Tanggal"].min()
    end_default = df["Tanggal"].max()

    tgl = st.date_input("Range Tanggal", value=(start_default, end_default))

    if len(tgl)==2:
        df = df[(df["Tanggal"]>=pd.to_datetime(tgl[0])) & (df["Tanggal"]<=pd.to_datetime(tgl[1]))]

    pegawai = st.multiselect("Pegawai", sorted(df["Nama"].unique()))
    lokasi = st.multiselect("Lokasi", sorted(df["Lokasi"].unique()))

    if pegawai:
        df = df[df["Nama"].isin(pegawai)]
    if lokasi:
        df = df[df["Lokasi"].isin(lokasi)]

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='card c1'><h3>{len(df)}</h3>Total</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card c2'><h3>{df['Durasi'].sum():.2f}</h3>Jam</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card c3'><h3>{df['Tanggal'].nunique()}</h3>Hari</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card c4'><h3>{df['Nama'].nunique()}</h3>Pegawai</div>", unsafe_allow_html=True)

    st.bar_chart(df.groupby("Nama")["Durasi"].sum())

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
    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')

    # ================= FILTER ROLE =================
    if st.session_state.role in ["admin","pimpinan"]:
        mode = st.radio("Mode Data", ["Semua Data","Data Saya"])
        if mode == "Data Saya":
            df = df[df["NIP"].astype(str)==st.session_state.nip]
    else:
        df = df[df["NIP"].astype(str)==st.session_state.nip]

    # ================= FILTER TANGGAL =================
    st.subheader("📅 Filter Tanggal")

    start_default = df["Tanggal"].min()
    end_default = df["Tanggal"].max()

    tgl = st.date_input(
        "Pilih Range Tanggal",
        value=(start_default, end_default)
    )

    if len(tgl) == 2:
        df = df[
            (df["Tanggal"] >= pd.to_datetime(tgl[0])) &
            (df["Tanggal"] <= pd.to_datetime(tgl[1]))
        ]

    # ================= TAMPIL DATA =================
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

    # ================= EDIT =================
    if "edit" in st.session_state:
        ed = st.session_state.edit

        st.subheader("✏️ Edit Data")

        masuk = st.text_input("Jam Masuk", ed["Jam Masuk"])
        keluar = st.text_input("Jam Keluar", ed["Jam Keluar"])
        uraian = st.text_area("Uraian", ed["Uraian"])
        output = st.text_area("Output", ed["Output"])

        opsi = ["Kantor","Rumah","Dinas Luar / SPT"]
        lokasi = st.selectbox(
            "Lokasi",
            opsi,
            index=opsi.index(ed["Lokasi"]) if ed["Lokasi"] in opsi else 0
        )

        if st.button("Update"):
            dur = hitung_durasi(masuk, keluar)

            sheet.update(
                f"E{int(ed['row'])}:J{int(ed['row'])}",
                [[masuk, keluar, dur, uraian, output, lokasi]]
            )

            del st.session_state.edit
            st.success("Update berhasil")
            st.rerun()

    # ================= DOWNLOAD SESUAI FILTER =================
    st.divider()
    st.subheader("📥 Download Data (Sesuai Filter)")

    export = df.copy()
    export["Tanggal"] = export["Tanggal"].dt.strftime("%Y-%m-%d")

    excel = io.BytesIO()
    export.to_excel(excel, index=False)

    st.download_button(
        "📥 Download Excel",
        excel.getvalue(),
        file_name="data_kinerja_filtered.xlsx"
    )

# ================= ADMIN =================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    nip = st.text_input("NIP")
    nama = st.text_input("Nama")
    jab = st.text_input("Jabatan")
    pw = st.text_input("Password")
    role = st.selectbox("Role", ["pegawai","admin","pimpinan"])

    if st.button("Tambah User"):
        user_sheet.append_row([nip,nama,jab,pw,role])
        st.success("User ditambahkan")