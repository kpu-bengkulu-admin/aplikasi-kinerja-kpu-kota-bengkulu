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

# tambah index baris (penting untuk edit/hapus)
def get_data_with_index():
    df = load_data()
    if df.empty:
        return df
    df["row_index"] = range(2, len(df) + 2)
    return df

# ================= SESSION =================
if "login" not in st.session_state:
    st.session_state.login = False

# ================= LOGIN =================
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

# ================= PARSER JAM =================
def parse_jam(jam_str):
    try:
        jam_str = str(jam_str).strip().replace(".", ":")
        j, m = jam_str.split(":")
        j = int(j); m = int(m)
        if j < 0 or j > 23 or m < 0 or m > 59:
            return None
        return j * 60 + m
    except:
        return None

def safe(val):
    return "" if val is None else str(val)

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.subheader("📊 Dashboard")

    data = load_data()

    if not data.empty:
        data["Durasi (Jam)"] = pd.to_numeric(data["Durasi (Jam)"], errors="coerce").fillna(0)
        st.bar_chart(data.groupby("Nama")["Durasi (Jam)"].sum())

    else:
        st.info("Belum ada data")

# ================= INPUT =================
elif menu == "Input Kinerja":

    st.subheader("📝 Input Kinerja")

    with st.form("form"):

        tanggal = st.date_input("Tanggal", datetime.today())
        jam_masuk = st.text_input("Jam Masuk")
        jam_keluar = st.text_input("Jam Keluar")

        uraian = st.text_area("Uraian")
        output = st.text_area("Output")
        lokasi = st.selectbox("Lokasi", ["Kantor", "Rumah", "Dinas"])

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

        st.success("Data tersimpan")

# ================= DATA KINERJA (EDIT + HAPUS) =================
elif menu == "Data Kinerja":

    st.subheader("📋 Data Kinerja")

    data = get_data_with_index()

    if data.empty:
        st.warning("Belum ada data")
        st.stop()

    for i, row in data.iterrows():

        with st.container():
            col1, col2, col3 = st.columns([5,2,2])

            with col1:
                st.write(f"👤 **{row['Nama']}**")
                st.caption(f"{row['Tanggal']} | {row['Uraian']}")

            with col2:
                st.write(f"⏱ {row['Durasi (Jam)']} jam")

            with col3:
                if st.button("✏️ Edit", key=f"edit_{i}"):

                    st.session_state.edit_mode = True
                    st.session_state.edit_row = row
                    st.session_state.edit_index = row["row_index"]

                if st.button("🗑 Hapus", key=f"del_{i}"):

                    sheet.delete_rows(row["row_index"])
                    st.success("Data dihapus")
                    st.rerun()

        st.divider()

    # ================= EDIT FORM =================
    if "edit_mode" in st.session_state and st.session_state.edit_mode:

        st.subheader("✏️ Edit Data")

        ed = st.session_state.edit_row

        jam_masuk = st.text_input("Jam Masuk", ed["Jam Masuk"])
        jam_keluar = st.text_input("Jam Keluar", ed["Jam Keluar"])
        uraian = st.text_area("Uraian", ed["Uraian"])
        output = st.text_area("Output", ed["Output"])

        lokasi = st.selectbox(
            "Lokasi",
            ["Kantor", "Rumah", "Dinas"],
            index=["Kantor","Rumah","Dinas"].index(ed["Lokasi"])
        )

        if st.button("💾 Simpan Perubahan"):

            jm = parse_jam(jam_masuk)
            jk = parse_jam(jam_keluar)

            if jm is None or jk is None:
                st.error("Format jam salah")
                st.stop()

            durasi = round((jk - jm) / 60, 2)

            sheet.update(
                f"E{st.session_state.edit_index}:J{st.session_state.edit_index}",
                [[jam_masuk, jam_keluar, durasi, uraian, output, lokasi]]
            )

            st.success("Data berhasil diupdate")

            st.session_state.edit_mode = False
            st.rerun()

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
            user_sheet.append_row([nip_b, nama_b, jabatan_b, pw_b, role_b])
            st.success("User ditambahkan")

    # ===== EDIT USER =====
    with tab2:

        if not users_df.empty:

            pilih = st.selectbox("Pilih NIP", users_df["NIP"].astype(str))
            row = users_df[users_df["NIP"].astype(str) == pilih].iloc[0]

            nama_e = st.text_input("Nama", row["Nama"])
            jabatan_e = st.text_input("Jabatan", row["Jabatan"])
            pw_e = st.text_input("Password (kosong = tidak ubah)")
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