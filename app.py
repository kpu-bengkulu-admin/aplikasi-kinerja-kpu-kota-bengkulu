import streamlit as st
import pandas as pd
import io
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Aplikasi E-Kinerja KPU Kota Bengkulu",
    layout="wide"
)

# =====================================================
# CSS PREMIUM UI
# =====================================================
st.markdown("""
<style>
.main {
    background-color:#f8fafc;
}
.block-container {
    padding-top:1rem;
    padding-bottom:2rem;
}
.card {
    background:white;
    padding:18px;
    border-radius:14px;
    box-shadow:0 4px 12px rgba(0,0,0,0.08);
    border-left:6px solid #0f4c81;
}
.small {
    color:#666;
    font-size:13px;
}
.big {
    font-size:28px;
    font-weight:700;
    color:#0f4c81;
}
.titlex {
    font-size:34px;
    font-weight:800;
    color:#0f4c81;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# GOOGLE SHEETS
# =====================================================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["connections"]["gsheets"]["service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

SPREADSHEET_ID = "16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM"

spreadsheet = client.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.sheet1
user_sheet = spreadsheet.worksheet("users")

# =====================================================
# FUNCTIONS
# =====================================================
def load_users():
    try:
        return pd.DataFrame(user_sheet.get_all_records())
    except:
        return pd.DataFrame()

def load_data():
    try:
        return pd.DataFrame(sheet.get_all_records())
    except:
        return pd.DataFrame()

def get_data_with_index():
    df = load_data()
    if not df.empty:
        df["row_index"] = range(2, len(df) + 2)
    return df

def parse_jam(val):
    try:
        val = str(val).replace(".", ":").strip()
        j, m = val.split(":")
        j = int(j)
        m = int(m)
        return j * 60 + m
    except:
        return None

def safe(v):
    return "" if v is None else str(v)

# =====================================================
# SESSION
# =====================================================
if "login" not in st.session_state:
    st.session_state.login = False

# =====================================================
# LOGIN
# =====================================================
users_df = load_users()

if not st.session_state.login:

    st.markdown("<div class='titlex'>📊 Aplikasi E-Kinerja KPU Kota Bengkulu</div>", unsafe_allow_html=True)
    st.subheader("🔐 Login")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):

        user = users_df[
            (users_df["NIP"].astype(str) == str(nip)) &
            (users_df["Password"].astype(str) == str(pw))
        ]

        if not user.empty:
            u = user.iloc[0]

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
st.markdown("<div class='titlex'>📊 Aplikasi E-Kinerja KPU Kota Bengkulu</div>", unsafe_allow_html=True)

col1, col2 = st.columns([8,2])

with col1:
    st.success(
        f"Login sebagai: {st.session_state.nama} ({st.session_state.role})"
    )

with col2:
    if st.button("🚪 Logout"):
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
# DASHBOARD PREMIUM
# =====================================================
if menu == "Dashboard":

    data = load_data()

    if data.empty:
        st.info("Belum ada data")
        st.stop()

    if st.session_state.role == "pegawai":
        data = data[data["NIP"].astype(str) == str(st.session_state.nip)]

    data["Durasi (Jam)"] = pd.to_numeric(
        data["Durasi (Jam)"],
        errors="coerce"
    ).fillna(0)

    total_jam = round(data["Durasi (Jam)"].sum(), 2)
    total_data = len(data)
    hari_aktif = data["Tanggal"].nunique()

    rata = round(total_jam / hari_aktif, 2) if hari_aktif > 0 else 0

    st.subheader(f"Selamat Datang, {st.session_state.nama}")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class='card'>
        <div class='small'>⏱ Total Jam</div>
        <div class='big'>{total_jam}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class='card'>
        <div class='small'>📄 Total Input</div>
        <div class='big'>{total_data}</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class='card'>
        <div class='small'>📅 Hari Aktif</div>
        <div class='big'>{hari_aktif}</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class='card'>
        <div class='small'>📈 Rata-rata</div>
        <div class='big'>{rata}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📊 Grafik Kinerja")
    st.bar_chart(data.groupby("Nama")["Durasi (Jam)"].sum())

    st.markdown("### 🕒 Data Terbaru")
    st.dataframe(data.tail(5), use_container_width=True)

# =====================================================
# INPUT
# =====================================================
elif menu == "Input Kinerja":

    st.subheader("📝 Input Kinerja")

    with st.form("input"):

        tanggal = st.date_input("Tanggal", date.today())

        jam_masuk = st.text_input("Jam Masuk (07:30)")
        jam_keluar = st.text_input("Jam Keluar (16:00)")

        uraian = st.text_area("Uraian")
        output = st.text_area("Output")

        lokasi = st.selectbox(
            "Lokasi",
            ["Kantor", "Rumah", "Dinas"]
        )

        simpan = st.form_submit_button("💾 Simpan")

    if simpan:

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
            safe(st.session_state.nama),
            safe(st.session_state.nip),
            safe(st.session_state.jabatan),
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

    data = get_data_with_index()

    if data.empty:
        st.warning("Belum ada data")
        st.stop()

    if st.session_state.role == "pegawai":
        data = data[data["NIP"].astype(str) == str(st.session_state.nip)]

    st.subheader("📋 Data Kinerja")

    c1, c2 = st.columns(2)

    with c1:
        tgl1 = st.date_input("Dari", date.today().replace(day=1))

    with c2:
        tgl2 = st.date_input("Sampai", date.today())

    data["Tanggal"] = pd.to_datetime(data["Tanggal"], errors="coerce")

    data = data[
        (data["Tanggal"] >= pd.to_datetime(tgl1)) &
        (data["Tanggal"] <= pd.to_datetime(tgl2))
    ]

    st.dataframe(
        data.drop(columns=["row_index"]),
        use_container_width=True
    )

    # =================================================
    # DOWNLOAD EXCEL FIX
    # =================================================
    export = data.drop(columns=["row_index"]).copy()

    export["NIP"] = export["NIP"].astype(str)
    export["Jam Masuk"] = export["Jam Masuk"].astype(str)
    export["Jam Keluar"] = export["Jam Keluar"].astype(str)

    excel = io.BytesIO()

    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        export.to_excel(writer, index=False, sheet_name="Kinerja")

    st.download_button(
        "📥 Download Excel",
        excel.getvalue(),
        file_name="rekap_kinerja.xlsx"
    )

    # =================================================
    # DOWNLOAD PDF
    # =================================================
    pdf = io.BytesIO()

    c = canvas.Canvas(pdf, pagesize=A4)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, "LAPORAN KINERJA")

    c.setFont("Helvetica", 10)
    c.drawString(50, 780, f"Nama : {st.session_state.nama}")
    c.drawString(50, 765, f"Periode : {tgl1} s/d {tgl2}")

    y = 730

    for _, row in data.iterrows():

        txt = f"{row['Tanggal'].date()} | {row['Uraian']} | {row['Durasi (Jam)']} jam"

        c.drawString(40, y, txt)
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
                nip, nama, jabatan, pw, role
            ])

            st.success("User berhasil ditambah")

    with tab2:

        st.dataframe(load_users(), use_container_width=True)