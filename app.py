import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIG =================
st.set_page_config(page_title="Aplikasi Kinerja KPU", layout="wide")
st.title("📊 Aplikasi Kinerja KPU")

# ================= GOOGLE SHEETS =================
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

# ================= LOAD DATA =================
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

# ================= SESSION =================
if "login" not in st.session_state:
    st.session_state.login = False

users_df = load_users()
data = load_data()

# ================= LOGIN =================
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

            st.session_state.update({
                "login": True,
                "nama": u["Nama"],
                "nip": u["NIP"],
                "jabatan": u["Jabatan"],
                "role": u["Role"]
            })

            st.rerun()

        else:
            st.error("Login gagal")

    st.stop()

# ================= HEADER =================
st.success(f"Login sebagai: {st.session_state.nama} ({st.session_state.role})")

if st.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

# ================= MENU =================
menu = st.sidebar.selectbox(
    "Menu",
    ["Dashboard", "Input Kinerja", "Data Kinerja", "Admin"]
)

# ================= FUNGSI JAM FLEXIBEL =================
def parse_jam(jam_str):
    try:
        jam_str = str(jam_str).strip().replace(".", ":")

        parts = jam_str.split(":")
        if len(parts) != 2:
            return None

        jam = int(parts[0])
        menit = int(parts[1])

        if jam < 0 or jam > 23 or menit < 0 or menit > 59:
            return None

        return jam * 60 + menit

    except:
        return None

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.subheader("📊 Dashboard")

    if not data.empty:
        data["Durasi (Jam)"] = pd.to_numeric(data["Durasi (Jam)"], errors="coerce").fillna(0)
        st.bar_chart(data.groupby("Nama")["Durasi (Jam)"].sum())

# ================= INPUT =================
elif menu == "Input Kinerja":

    st.subheader("📝 Input Kinerja")

    with st.form("form"):

        tanggal = st.date_input("Tanggal", datetime.today())
        jam_masuk = st.text_input("Jam Masuk (contoh 08:00 / 8:00 / 08.00)")
        jam_keluar = st.text_input("Jam Keluar (contoh 17:00 / 17.00)")

        uraian = st.text_area("Uraian")
        output = st.text_area("Output")
        lokasi = st.selectbox("Lokasi", ["Kantor", "Rumah", "Dinas"])

        submit = st.form_submit_button("Simpan")

    if submit:

        jm = parse_jam(jam_masuk)
        jk = parse_jam(jam_keluar)

        if jm is None or jk is None:
            st.error("Format jam tidak valid (contoh: 08:00 atau 8:00)")
            st.stop()

        if jk <= jm:
            st.error("Jam keluar harus lebih besar dari jam masuk")
            st.stop()

        durasi = round((jk - jm) / 60, 2)

        sheet.append_row([
            st.session_state.nama,
            st.session_state.nip,
            st.session_state.jabatan,
            str(tanggal),
            jam_masuk,
            jam_keluar,
            durasi,
            uraian,
            output,
            lokasi
        ])

        st.success("Data tersimpan")

# ================= DATA =================
elif menu == "Data Kinerja":

    st.subheader("📋 Data Kinerja")
    st.dataframe(data, use_container_width=True)

# ================= ADMIN =================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    st.subheader("⚙️ Admin Panel")

    tab1, tab2, tab3 = st.tabs(["Tambah", "Edit", "Hapus"])

    users_df = load_users()

    # ===== TAMBAH USER =====
    with tab1:

        nip_b = st.text_input("NIP")
        nama_b = st.text_input("Nama")
        jabatan_b = st.text_input("Jabatan")
        pw_b = st.text_input("Password")
        role_b = st.selectbox("Role", ["pegawai", "admin", "pimpinan"])

        if st.button("Tambah User"):

            user_sheet.append_row([
                nip_b,
                nama_b,
                jabatan_b,
                pw_b,
                role_b
            ])

            st.success("User ditambahkan")

    # ===== EDIT USER =====
    with tab2:

        if not users_df.empty:

            pilih = st.selectbox("Pilih NIP", users_df["NIP"].astype(str))
            row = users_df[users_df["NIP"].astype(str) == pilih].iloc[0]

            nama_e = st.text_input("Nama", row["Nama"])
            jabatan_e = st.text_input("Jabatan", row["Jabatan"])
            pw_e = st.text_input("Password baru (kosong = tidak ubah)")
            role_e = st.selectbox("Role", ["pegawai","admin","pimpinan"])

            if st.button("Update User"):

                all_data = user_sheet.get_all_values()

                for i, r in enumerate(all_data):
                    if r[0] == pilih:

                        pw_final = r[3] if pw_e == "" else pw_e

                        user_sheet.update(
                            f"A{i+1}:E{i+1}",
                            [[pilih, nama_e, jabatan_e, pw_final, role_e]]
                        )

                        st.success("User diupdate")
                        st.rerun()

    # ===== HAPUS USER =====
    with tab3:

        hapus = st.selectbox("Hapus NIP", users_df["NIP"].astype(str))

        if st.button("Hapus User"):

            all_data = user_sheet.get_all_values()

            for i, r in enumerate(all_data):
                if r[0] == hapus:
                    user_sheet.delete_rows(i+1)
                    st.success("User dihapus")
                    st.rerun()