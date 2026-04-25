# app.py
# ======================================================
# APLIKASI E-KINERJA KPU KOTA BENGKULU
# FULL SUPER FINAL UX VERSION
# Siap Deploy Streamlit Cloud
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
# CSS FINAL
# ======================================================
st.markdown("""
<style>
.block-container{
    padding-top:3rem;
    max-width:1450px;
}
.titlex{
    font-size:34px;
    font-weight:800;
    text-align:center;
    color:#0f4c81;
    margin-bottom:20px;
}
.card{
    background:white;
    padding:18px;
    border-radius:16px;
    box-shadow:0 4px 12px rgba(0,0,0,.08);
    border-left:6px solid #0f4c81;
}
.small{
    font-size:13px;
    color:#666;
}
.big{
    font-size:28px;
    font-weight:800;
    color:#0f4c81;
}
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

try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet("users", 100, 5)
    user_sheet.append_row(
        ["NIP", "Nama", "Jabatan", "Password", "Role"]
    )

# ======================================================
# LOAD
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
# TIME PARSER
# ======================================================
def parse_jam(x):
    try:
        x = str(x).replace(".", ":").strip()
        a, b = x.split(":")
        a = int(a)
        b = int(b)

        if a < 0 or a > 23:
            return None
        if b < 0 or b > 59:
            return None

        return a * 60 + b
    except:
        return None

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

# ======================================================
# HEADER
# ======================================================
st.markdown(
    "<div class='titlex'>📊 Aplikasi E-Kinerja KPU Kota Bengkulu</div>",
    unsafe_allow_html=True
)

a, b = st.columns([8,2])

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
    ["Dashboard", "Input Kinerja", "Data Kinerja", "Admin"]
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
        df = df[df["NIP"].astype(str) == str(st.session_state.nip)]

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi (Jam)"] = pd.to_numeric(
        df["Durasi (Jam)"],
        errors="coerce"
    ).fillna(0)

    total_jam = round(df["Durasi (Jam)"].sum(), 2)
    total_data = len(df)
    hari = df["Tanggal"].nunique()
    rata = round(total_jam / hari, 2) if hari else 0

    c1,c2,c3,c4 = st.columns(4)

    with c1:
        st.markdown(
            f"<div class='card'><div class='small'>⏱ Total Jam</div><div class='big'>{total_jam}</div></div>",
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"<div class='card'><div class='small'>📄 Total Data</div><div class='big'>{total_data}</div></div>",
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            f"<div class='card'><div class='small'>📅 Hari Aktif</div><div class='big'>{hari}</div></div>",
            unsafe_allow_html=True
        )

    with c4:
        st.markdown(
            f"<div class='card'><div class='small'>📈 Rata-rata</div><div class='big'>{rata}</div></div>",
            unsafe_allow_html=True
        )

    st.markdown("### 📊 Grafik Kinerja")
    st.bar_chart(df.groupby("Nama")["Durasi (Jam)"].sum())

# ======================================================
# INPUT KINERJA (UX FINAL)
# ======================================================
elif menu == "Input Kinerja":

    st.subheader("📝 Input Kinerja")

    with st.form("form_input", clear_on_submit=True):

        tanggal = st.date_input("Tanggal", date.today())
        jam_masuk = st.text_input("Jam Masuk", "07:30")
        jam_keluar = st.text_input("Jam Keluar", "16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")

        lokasi = st.selectbox(
            "Lokasi",
            ["Kantor", "Rumah", "Dinas Luar / SPT"]
        )

        simpan = st.form_submit_button("💾 Simpan Data")

    if simpan:

        if uraian.strip() == "":
            st.warning("Uraian wajib diisi")
            st.stop()

        if output.strip() == "":
            st.warning("Output wajib diisi")
            st.stop()

        jm = parse_jam(jam_masuk)
        jk = parse_jam(jam_keluar)

        if jm is None or jk is None:
            st.error("Format jam salah. Contoh 07:30")
            st.stop()

        if jk <= jm:
            st.error("Jam keluar harus lebih besar")
            st.stop()

        durasi = round((jk - jm) / 60, 2)

        with st.spinner("Menyimpan data..."):

            sheet.append_row([
                safe(st.session_state.nama),
                safe(st.session_state.nip),
                safe(st.session_state.jabatan),
                safe(tanggal.strftime("%Y-%m-%d")),
                safe(jam_masuk.replace(".", ":")),
                safe(jam_keluar.replace(".", ":")),
                float(durasi),
                safe(uraian),
                safe(output),
                safe(lokasi)
            ])

        st.success("✅ Data berhasil disimpan")

        try:
            st.toast("Data tersimpan")
        except:
            pass

        st.rerun()

# ======================================================
# DATA KINERJA + EDIT + HAPUS
# ======================================================
elif menu == "Data Kinerja":

    df = get_data_with_index()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    if st.session_state.role == "pegawai":
        df = df[df["NIP"].astype(str) == str(st.session_state.nip)]

    st.subheader("📋 Data Kinerja")

    for i, row in df.iterrows():

        with st.container():

            x1,x2,x3 = st.columns([6,2,2])

            with x1:
                st.write(f"**{row['Nama']}**")
                st.caption(f"{row['Tanggal']} | {row['Uraian']}")

            with x2:
                st.write(f"{row['Durasi (Jam)']} Jam")

            with x3:

                if st.button("✏️ Edit", key=f"edit{i}"):
                    st.session_state.edit = True
                    st.session_state.edit_row = row

                if st.button("🗑 Hapus", key=f"hapus{i}"):
                    sheet.delete_rows(int(row["row_index"]))
                    st.success("Data dihapus")
                    st.rerun()

        st.divider()

    # EDIT FORM
    if st.session_state.get("edit", False):

        ed = st.session_state.edit_row

        st.subheader("✏️ Edit Data")

        masuk = st.text_input("Jam Masuk", ed["Jam Masuk"])
        keluar = st.text_input("Jam Keluar", ed["Jam Keluar"])
        uraian = st.text_area("Uraian", ed["Uraian"])
        output = st.text_area("Output", ed["Output"])

        opsi = ["Kantor", "Rumah", "Dinas Luar / SPT"]

        lokasi = st.selectbox(
            "Lokasi",
            opsi,
            index=opsi.index(ed["Lokasi"]) if ed["Lokasi"] in opsi else 0
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

            durasi = round((jk - jm) / 60, 2)

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

            st.success("Perubahan berhasil disimpan")
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

    # DOWNLOAD PDF
    if PDF_READY:

        pdf = io.BytesIO()
        c = canvas.Canvas(pdf, pagesize=A4)

        c.drawString(50, 800, "Laporan Kinerja")

        y = 770

        for _, r in df.iterrows():

            text = f"{r['Tanggal']} | {r['Uraian']} | {r['Durasi (Jam)']} Jam"

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

# ======================================================
# ADMIN
# ======================================================
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
                safe(nip),
                safe(nama),
                safe(jabatan),
                safe(pw),
                safe(role)
            ])

            st.success("User berhasil ditambah")
            st.rerun()

    with tab2:
        st.dataframe(load_users(), use_container_width=True)