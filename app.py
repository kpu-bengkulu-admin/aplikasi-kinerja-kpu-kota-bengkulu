# app.py
# =====================================================
# APLIKASI E-KINERJA KPU KOTA BENGKULU
# VERSI STABIL - SIAP DEPLOY STREAMLIT CLOUD
# =====================================================

import streamlit as st
import pandas as pd
import io
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# PDF optional-safe
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    PDF_READY = True
except:
    PDF_READY = False

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Aplikasi E-Kinerja KPU Kota Bengkulu",
    layout="wide"
)

# =====================================================
# UI
# =====================================================
st.markdown("""
<style>
.block-container{
    padding-top:3rem;
    max-width:1400px;
}
.titlex{
    font-size:34px;
    font-weight:800;
    color:#0f4c81;
    text-align:center;
    margin-bottom:20px;
}
.card{
    background:white;
    padding:18px;
    border-radius:16px;
    box-shadow:0 4px 12px rgba(0,0,0,.08);
    border-left:6px solid #0f4c81;
}
.small{font-size:13px;color:#666;}
.big{font-size:28px;font-weight:800;color:#0f4c81;}
.stButton>button{
    width:100%;
    border:none;
    border-radius:10px;
    background:#0f4c81;
    color:white;
    font-weight:700;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# GOOGLE SHEETS CONNECT
# =====================================================
@st.cache_resource
def connect_sheet():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(
            st.secrets["connections"]["gsheets"]["service_account"],
            scopes=scope
        )

        client = gspread.authorize(creds)

        ss = client.open_by_key(
            "16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM"
        )

        return ss

    except Exception as e:
        st.error("Gagal koneksi Google Sheets")
        st.stop()

spreadsheet = connect_sheet()

# worksheet utama
sheet = spreadsheet.sheet1

# worksheet users
try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet(
        title="users",
        rows=100,
        cols=5
    )
    user_sheet.append_row(
        ["NIP", "Nama", "Jabatan", "Password", "Role"]
    )

# =====================================================
# LOAD DATA
# =====================================================
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

# =====================================================
# UTILS
# =====================================================
def parse_jam(jam):
    try:
        jam = str(jam).replace(".", ":").strip()
        h, m = jam.split(":")
        h = int(h)
        m = int(m)

        if h < 0 or h > 23 or m < 0 or m > 59:
            return None

        return h * 60 + m
    except:
        return None

# =====================================================
# SESSION
# =====================================================
if "login" not in st.session_state:
    st.session_state.login = False

# =====================================================
# LOGIN
# =====================================================
users = load_users()

if not st.session_state.login:

    st.markdown(
        "<div class='titlex'>📊 Aplikasi E-Kinerja KPU Kota Bengkulu</div>",
        unsafe_allow_html=True
    )

    st.subheader("🔐 Login")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):

        if users.empty:
            st.error("Data user kosong")
            st.stop()

        cek = users[
            (users["NIP"].astype(str) == str(nip)) &
            (users["Password"].astype(str) == str(pw))
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

# =====================================================
# HEADER
# =====================================================
st.markdown(
    "<div class='titlex'>📊 Aplikasi E-Kinerja KPU Kota Bengkulu</div>",
    unsafe_allow_html=True
)

col1, col2 = st.columns([8,2])

with col1:
    st.success(
        f"Login sebagai {st.session_state.nama} ({st.session_state.role})"
    )

with col2:
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

# =====================================================
# MENU
# =====================================================
menu = st.sidebar.selectbox(
    "Menu",
    ["Dashboard", "Input Kinerja", "Data Kinerja", "Admin"]
)

# =====================================================
# DASHBOARD
# =====================================================
if menu == "Dashboard":

    df = load_data()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    if st.session_state.role == "pegawai":
        df = df[df["NIP"].astype(str) == str(st.session_state.nip)]

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    if "Durasi (Jam)" in df.columns:
        df["Durasi (Jam)"] = pd.to_numeric(
            df["Durasi (Jam)"],
            errors="coerce"
        ).fillna(0)
    else:
        df["Durasi (Jam)"] = 0

    total_jam = round(df["Durasi (Jam)"].sum(), 2)
    total_data = len(df)
    hari = df["Tanggal"].nunique() if "Tanggal" in df.columns else 0
    rata = round(total_jam / hari, 2) if hari else 0

    a,b,c,d = st.columns(4)

    with a:
        st.markdown(f"<div class='card'><div class='small'>⏱ Total Jam</div><div class='big'>{total_jam}</div></div>", unsafe_allow_html=True)

    with b:
        st.markdown(f"<div class='card'><div class='small'>📄 Total Data</div><div class='big'>{total_data}</div></div>", unsafe_allow_html=True)

    with c:
        st.markdown(f"<div class='card'><div class='small'>📅 Hari Aktif</div><div class='big'>{hari}</div></div>", unsafe_allow_html=True)

    with d:
        st.markdown(f"<div class='card'><div class='small'>📈 Rata-rata</div><div class='big'>{rata}</div></div>", unsafe_allow_html=True)

    st.markdown("### Grafik Kinerja")
    if "Nama" in df.columns:
        st.bar_chart(df.groupby("Nama")["Durasi (Jam)"].sum())

# =====================================================
# INPUT
# =====================================================
elif menu == "Input Kinerja":

    st.subheader("📝 Input Kinerja")

    with st.form("form"):

        tanggal = st.date_input("Tanggal", date.today())
        jam_masuk = st.text_input("Jam Masuk", "07:30")
        jam_keluar = st.text_input("Jam Keluar", "16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")

        lokasi = st.selectbox(
            "Lokasi",
            ["Kantor", "Rumah", "Dinas Luar / SPT"]
        )

        submit = st.form_submit_button("Simpan")

    if submit:

        jm = parse_jam(jam_masuk)
        jk = parse_jam(jam_keluar)

        if jm is None or jk is None:
            st.error("Format jam salah")
            st.stop()

        if jk <= jm:
            st.error("Jam keluar harus lebih besar")
            st.stop()

        durasi = round((jk - jm) / 60, 2)

        sheet.append_row([
            st.session_state.nama,
            st.session_state.nip,
            st.session_state.jabatan,
            tanggal.strftime("%Y-%m-%d"),
            jam_masuk.replace(".", ":"),
            jam_keluar.replace(".", ":"),
            durasi,
            uraian,
            output,
            lokasi
        ])

        st.success("Data berhasil disimpan")

# =====================================================
# DATA KINERJA
# =====================================================
elif menu == "Data Kinerja":

    df = load_data()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    if st.session_state.role == "pegawai":
        df = df[df["NIP"].astype(str) == str(st.session_state.nip)]

    st.subheader("📋 Data Kinerja")
    st.dataframe(df, use_container_width=True)

    # EXCEL
    excel = io.BytesIO()

    export = df.copy()
    if "NIP" in export.columns:
        export["NIP"] = export["NIP"].astype(str)

    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        export.to_excel(writer, index=False)

    st.download_button(
        "📥 Download Excel",
        excel.getvalue(),
        file_name="rekap_kinerja.xlsx"
    )

    # PDF
    if PDF_READY:
        pdf = io.BytesIO()
        c = canvas.Canvas(pdf, pagesize=A4)

        c.drawString(50, 800, "Laporan Kinerja")

        y = 770
        for _, row in df.iterrows():

            text = " | ".join([str(x) for x in row.values])

            c.drawString(30, y, text[:100])

            y -= 18
            if y < 50:
                c.showPage()
                y = 800

        c.save()

        st.download_button(
            "📄 Download PDF",
            pdf.getvalue(),
            file_name="laporan_kinerja.pdf"
        )

# =====================================================
# ADMIN
# =====================================================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    st.subheader("⚙️ Admin Panel")

    tab1, tab2 = st.tabs(["Tambah User", "Daftar User"])

    with tab1:

        nip = st.text_input("NIP Baru")
        nama = st.text_input("Nama Baru")
        jabatan = st.text_input("Jabatan Baru")
        pw = st.text_input("Password Baru")
        role = st.selectbox(
            "Role",
            ["pegawai", "admin", "pimpinan"]
        )

        if st.button("Tambah User"):

            user_sheet.append_row([
                nip,
                nama,
                jabatan,
                pw,
                role
            ])

            st.success("User berhasil ditambah")

    with tab2:
        st.dataframe(load_users(), use_container_width=True)