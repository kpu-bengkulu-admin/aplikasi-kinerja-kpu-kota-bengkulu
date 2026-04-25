# app.py
# ======================================================
# APLIKASI E-KINERJA KPU KOTA BENGKULU
# FINAL FULL VERSION - STABIL & SIAP DEPLOY
# ======================================================

import streamlit as st
import pandas as pd
import io
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# ======================================================
# OPTIONAL PDF
# ======================================================
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    PDF_READY = True
except:
    PDF_READY = False

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="Aplikasi E-Kinerja KPU Kota Bengkulu",
    layout="wide"
)

# ======================================================
# CSS
# ======================================================
st.markdown("""
<style>
.block-container{
    padding-top:2rem;
    max-width:1450px;
}
.titlex{
    font-size:34px;
    font-weight:800;
    text-align:center;
    color:#0f4c81;
    margin-bottom:15px;
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
.stButton > button{
    width:100%;
    border:none;
    border-radius:10px;
    background:#0f4c81;
    color:white;
    font-weight:700;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# SAFE
# ======================================================
def safe(x):
    if x is None:
        return ""
    return str(x)

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

    return client.open_by_key(
        "16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM"
    )

spreadsheet = connect_sheet()
sheet = spreadsheet.sheet1

# USERS SHEET
try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet("users", 100, 5)
    user_sheet.append_row(
        ["NIP","Nama","Jabatan","Password","Role"]
    )

# ======================================================
# LOAD DATA
# ======================================================
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
        h,m = x.split(":")
        h = int(h)
        m = int(m)

        if h < 0 or h > 23:
            return None
        if m < 0 or m > 59:
            return None

        return h*60 + m
    except:
        return None

def hitung_durasi(row):
    try:
        jm = parse_jam(row["Jam Masuk"])
        jk = parse_jam(row["Jam Keluar"])

        if jm is None or jk is None:
            return 0

        if jk <= jm:
            return 0

        return round((jk-jm)/60,2)
    except:
        return 0

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

    st.markdown(
        "<div class='titlex'>📊 Aplikasi E-Kinerja KPU Kota Bengkulu</div>",
        unsafe_allow_html=True
    )

    st.subheader("🔐 Login")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):

        if users.empty:
            st.error("Data users kosong")
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
st.markdown(
"<div class='titlex'>📊 Aplikasi E-Kinerja KPU Kota Bengkulu</div>",
unsafe_allow_html=True
)

a,b = st.columns([8,2])

with a:
    st.success(
        f"Login sebagai {st.session_state.nama} ({st.session_state.role})"
    )

with b:
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

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi (Jam)"] = df.apply(hitung_durasi, axis=1)

    total_jam = round(df["Durasi (Jam)"].sum(),2)
    total_data = len(df)
    hari = df["Tanggal"].nunique()
    rata = round(total_jam/hari,2) if hari else 0

    c1,c2,c3,c4 = st.columns(4)

    with c1:
        st.markdown(f"<div class='card'><div class='small'>⏱ Total Jam</div><div class='big'>{total_jam}</div></div>", unsafe_allow_html=True)

    with c2:
        st.markdown(f"<div class='card'><div class='small'>📄 Total Data</div><div class='big'>{total_data}</div></div>", unsafe_allow_html=True)

    with c3:
        st.markdown(f"<div class='card'><div class='small'>📅 Hari Aktif</div><div class='big'>{hari}</div></div>", unsafe_allow_html=True)

    with c4:
        st.markdown(f"<div class='card'><div class='small'>📈 Rata-rata</div><div class='big'>{rata}</div></div>", unsafe_allow_html=True)

    st.markdown("### 📊 Grafik Kinerja")
    st.bar_chart(df.groupby("Nama")["Durasi (Jam)"].sum())

# ======================================================
# INPUT
# ======================================================
elif menu == "Input Kinerja":

    st.subheader("📝 Input Kinerja")

    with st.form("form_input", clear_on_submit=True):

        tanggal = st.date_input("Tanggal", date.today())
        masuk = st.text_input("Jam Masuk", "07:30")
        keluar = st.text_input("Jam Keluar", "16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")

        lokasi = st.selectbox(
            "Lokasi",
            ["Kantor","Rumah","Dinas Luar / SPT"]
        )

        simpan = st.form_submit_button("💾 Simpan Data")

    if simpan:

        if uraian.strip()=="":
            st.warning("Uraian wajib diisi")
            st.stop()

        if output.strip()=="":
            st.warning("Output wajib diisi")
            st.stop()

        jm = parse_jam(masuk)
        jk = parse_jam(keluar)

        if jm is None or jk is None:
            st.error("Format jam salah")
            st.stop()

        if jk <= jm:
            st.error("Jam keluar harus lebih besar")
            st.stop()

        durasi = round((jk-jm)/60,2)

        with st.spinner("Menyimpan data..."):

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
        st.rerun()

# ======================================================
# DATA KINERJA
# ======================================================
elif menu == "Data Kinerja":

    df = get_data_with_index()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    if st.session_state.role == "pegawai":
        df = df[df["NIP"].astype(str)==str(st.session_state.nip)]

    df["Durasi (Jam)"] = df.apply(hitung_durasi, axis=1)

    st.subheader("📋 Data Kinerja")

    for i,row in df.iterrows():

        with st.container():

            x1,x2,x3 = st.columns([6,2,2])

            with x1:
                st.write(f"**{row['Nama']}**")
                st.caption(
                    f"{row['Tanggal']} | {row['Uraian']}"
                )

            with x2:
                st.write(f"{row['Durasi (Jam)']} Jam")

            with x3:

                if st.button("✏️ Edit", key=f"edit{i}"):

                    st.session_state.edit = True
                    st.session_state.edit_row = row

                if st.button("🗑 Hapus", key=f"hapus{i}"):

                    sheet.delete_rows(
                        int(row["row_index"])
                    )

                    st.success("Data dihapus")
                    st.rerun()

        st.divider()

    # EDIT FORM
    if st.session_state.get("edit", False):

        ed = st.session_state.edit_row

        st.subheader("✏️ Edit Data")

        masuk = st.text_input(
            "Jam Masuk",
            ed["Jam Masuk"]
        )

        keluar = st.text_input(
            "Jam Keluar",
            ed["Jam Keluar"]
        )

        uraian = st.text_area(
            "Uraian",
            ed["Uraian"]
        )

        output = st.text_area(
            "Output",
            ed["Output"]
        )

        opsi = [
            "Kantor",
            "Rumah",
            "Dinas Luar / SPT"
        ]

        lokasi = st.selectbox(
            "Lokasi",
            opsi,
            index=opsi.index(ed["Lokasi"])
            if ed["Lokasi"] in opsi else 0
        )

        if st.button("💾 Simpan Perubahan"):

            jm = parse_jam(masuk)
            jk = parse_jam(keluar)

            if jm is None or jk is None:
                st.error("Format jam salah")
                st.stop()

            if jk <= jm:
                st.error("Jam keluar harus lebih besar")
                st.stop()

            durasi = round((jk-jm)/60,2)

            idx = int(ed["row_index"])

            sheet.update(
                f"E{idx}:J{idx}",
                [[
                    safe(masuk),
                    safe(keluar),
                    float(durasi),
                    safe(uraian),
                    safe(output),
                    safe(lokasi)
                ]]
            )

            st.success("Berhasil diupdate")
            st.session_state.edit = False
            st.rerun()

    # DOWNLOAD EXCEL
    excel = io.BytesIO()

    export = df.drop(columns=["row_index"]).copy()
    export["NIP"] = export["NIP"].astype(str)

    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        export.to_excel(writer, index=False)

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

    st.subheader("⚙️ Admin")

    tab1,tab2 = st.tabs(
        ["Tambah User","Daftar User"]
    )

    with tab1:

        nip = st.text_input("NIP Baru")
        nama = st.text_input("Nama")
        jabatan = st.text_input("Jabatan")
        pw = st.text_input("Password")
        role = st.selectbox(
            "Role",
            ["pegawai","admin","pimpinan"]
        )

        if st.button("Tambah User"):

            user_sheet.append_row([
                safe(nip),
                safe(nama),
                safe(jabatan),
                safe(pw),
                safe(role)
            ])

            st.success("User ditambah")
            st.rerun()

    with tab2:
        st.dataframe(load_users(), use_container_width=True)