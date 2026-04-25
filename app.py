import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Aplikasi E-Kinerja KPU Kota Bengkulu",
    layout="wide"
)

st.title("📊 Aplikasi E-Kinerja KPU Kota Bengkulu")

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
# LOAD DATA
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
    if df.empty:
        return df
    df["row_index"] = range(2, len(df) + 2)
    return df

# =====================================================
# UTILS
# =====================================================
def parse_jam(jam_str):
    try:
        jam_str = str(jam_str).strip().replace(".", ":")
        j, m = jam_str.split(":")
        j = int(j)
        m = int(m)

        if j < 0 or j > 23 or m < 0 or m > 59:
            return None

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
st.success(
    f"Login sebagai: {st.session_state.nama} ({st.session_state.role})"
)

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
# DASHBOARD
# =====================================================
if menu == "Dashboard":

    st.subheader("📈 Dashboard")

    data = load_data()

    if data.empty:
        st.info("Belum ada data")
    else:

        if st.session_state.role == "pegawai":
            data = data[
                data["NIP"].astype(str) == str(st.session_state.nip)
            ]

        data["Durasi (Jam)"] = pd.to_numeric(
            data["Durasi (Jam)"],
            errors="coerce"
        ).fillna(0)

        st.metric(
            "Total Jam Kerja",
            round(data["Durasi (Jam)"].sum(), 2)
        )

        st.bar_chart(
            data.groupby("Nama")["Durasi (Jam)"].sum()
        )

# =====================================================
# INPUT KINERJA
# =====================================================
elif menu == "Input Kinerja":

    st.subheader("📝 Input Kinerja")

    with st.form("form_input"):

        tanggal = st.date_input(
            "Tanggal",
            datetime.today()
        )

        jam_masuk = st.text_input("Jam Masuk (08:00)")
        jam_keluar = st.text_input("Jam Keluar (16:30)")

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
            safe(jam_masuk),
            safe(jam_keluar),
            safe(durasi),
            safe(uraian),
            safe(output),
            safe(lokasi)
        ])

        st.success("Data berhasil disimpan")

# =====================================================
# DATA KINERJA
# =====================================================
elif menu == "Data Kinerja":

    st.subheader("📋 Data Kinerja")

    data = get_data_with_index()

    if data.empty:
        st.warning("Belum ada data")
        st.stop()

    # ================= FILTER ROLE =================
    if st.session_state.role == "pegawai":
        data = data[
            data["NIP"].astype(str) == str(st.session_state.nip)
        ]

    # ================= FILTER TANGGAL =================
    col1, col2 = st.columns(2)

    with col1:
        tgl1 = st.date_input("Dari Tanggal")

    with col2:
        tgl2 = st.date_input("Sampai Tanggal")

    data["Tanggal"] = pd.to_datetime(
        data["Tanggal"],
        errors="coerce"
    )

    data = data[
        (data["Tanggal"] >= pd.to_datetime(tgl1)) &
        (data["Tanggal"] <= pd.to_datetime(tgl2))
    ]

    if data.empty:
        st.info("Tidak ada data")
        st.stop()

    # ================= TABEL =================
    st.dataframe(
        data.drop(columns=["row_index"]),
        use_container_width=True
    )

    # =================================================
    # DOWNLOAD EXCEL
    # =================================================
    excel_buffer = io.BytesIO()

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl"
    ) as writer:

        data.drop(columns=["row_index"]).to_excel(
            writer,
            index=False,
            sheet_name="Kinerja"
        )

    st.download_button(
        label="📥 Download Excel",
        data=excel_buffer.getvalue(),
        file_name=f"rekap_{st.session_state.nama}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # =================================================
    # DOWNLOAD PDF
    # =================================================
    pdf_buffer = io.BytesIO()

    c = canvas.Canvas(pdf_buffer, pagesize=A4)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(
        50, 800,
        "LAPORAN KINERJA PEGAWAI"
    )

    c.setFont("Helvetica", 10)
    c.drawString(
        50, 780,
        f"Nama : {st.session_state.nama}"
    )
    c.drawString(
        50, 765,
        f"NIP : {st.session_state.nip}"
    )
    c.drawString(
        50, 750,
        f"Periode : {tgl1} s/d {tgl2}"
    )

    y = 720

    for _, row in data.iterrows():

        teks = (
            f"{row['Tanggal'].date()} | "
            f"{row['Uraian']} | "
            f"{row['Durasi (Jam)']} jam"
        )

        c.drawString(50, y, teks)
        y -= 18

        if y < 50:
            c.showPage()
            y = 800

    c.save()

    st.download_button(
        label="📄 Download PDF",
        data=pdf_buffer.getvalue(),
        file_name=f"laporan_{st.session_state.nama}.pdf",
        mime="application/pdf"
    )

    # =================================================
    # EDIT + HAPUS
    # =================================================
    st.divider()
    st.subheader("✏️ Edit / Hapus Data")

    for i, row in data.iterrows():

        c1, c2, c3 = st.columns([5, 2, 2])

        with c1:
            st.write(f"👤 {row['Nama']}")
            st.caption(
                f"{row['Tanggal'].date()} | {row['Uraian']}"
            )

        with c2:
            st.write(f"⏱ {row['Durasi (Jam)']} jam")

        with c3:

            if st.button("Edit", key=f"edit{i}"):

                st.session_state.edit_mode = True
                st.session_state.edit_row = row
                st.session_state.edit_index = row["row_index"]

            if st.button("Hapus", key=f"hapus{i}"):

                sheet.delete_rows(row["row_index"])
                st.success("Data dihapus")
                st.rerun()

        st.divider()

    # ================= FORM EDIT =================
    if "edit_mode" in st.session_state:

        if st.session_state.edit_mode:

            st.subheader("📝 Form Edit")

            ed = st.session_state.edit_row

            jm = st.text_input(
                "Jam Masuk",
                ed["Jam Masuk"]
            )

            jk = st.text_input(
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

            lokasi = st.selectbox(
                "Lokasi",
                ["Kantor", "Rumah", "Dinas"],
                index=["Kantor", "Rumah", "Dinas"].index(
                    ed["Lokasi"]
                )
            )

            if st.button("💾 Simpan Perubahan"):

                masuk = parse_jam(jm)
                keluar = parse_jam(jk)

                durasi = round(
                    (keluar - masuk) / 60,
                    2
                )

                idx = st.session_state.edit_index

                sheet.update(
                    f"E{idx}:J{idx}",
                    [[jm, jk, durasi, uraian, output, lokasi]]
                )

                st.success("Data berhasil diupdate")

                st.session_state.edit_mode = False
                st.rerun()

# =====================================================
# ADMIN
# =====================================================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    st.subheader("⚙️ Admin Panel")

    users_df = load_users()

    tab1, tab2, tab3 = st.tabs(
        ["Tambah User", "Edit User", "Hapus User"]
    )

    # ==========================================
    # TAMBAH
    # ==========================================
    with tab1:

        nip = st.text_input("NIP Baru")
        nama = st.text_input("Nama Baru")
        jabatan = st.text_input("Jabatan Baru")
        password = st.text_input("Password Baru")
        role = st.selectbox(
            "Role",
            ["pegawai", "admin", "pimpinan"]
        )

        if st.button("Tambah User"):

            user_sheet.append_row([
                nip,
                nama,
                jabatan,
                password,
                role
            ])

            st.success("User berhasil ditambah")

    # ==========================================
    # EDIT
    # ==========================================
    with tab2:

        if not users_df.empty:

            pilih = st.selectbox(
                "Pilih User",
                users_df["NIP"].astype(str)
            )

            row = users_df[
                users_df["NIP"].astype(str) == pilih
            ].iloc[0]

            nama_e = st.text_input(
                "Nama",
                row["Nama"]
            )

            jabatan_e = st.text_input(
                "Jabatan",
                row["Jabatan"]
            )

            pw_e = st.text_input(
                "Password Baru (kosong=tidak ganti)"
            )

            role_e = st.selectbox(
                "Role Baru",
                ["pegawai", "admin", "pimpinan"]
            )

            if st.button("Update User"):

                all_data = user_sheet.get_all_values()

                for i, r in enumerate(all_data):

                    if r[0] == pilih:

                        pass_final = r[3]
                        if pw_e != "":
                            pass_final = pw_e

                        user_sheet.update(
                            f"A{i+1}:E{i+1}",
                            [[
                                pilih,
                                nama_e,
                                jabatan_e,
                                pass_final,
                                role_e
                            ]]
                        )

                        st.success("User berhasil diupdate")
                        st.rerun()

    # ==========================================
    # HAPUS
    # ==========================================
    with tab3:

        hapus = st.selectbox(
            "Pilih NIP Hapus",
            users_df["NIP"].astype(str)
        )

        if st.button("Hapus User"):

            all_data = user_sheet.get_all_values()

            for i, r in enumerate(all_data):

                if r[0] == hapus:
                    user_sheet.delete_rows(i + 1)
                    st.success("User berhasil dihapus")
                    st.rerun()