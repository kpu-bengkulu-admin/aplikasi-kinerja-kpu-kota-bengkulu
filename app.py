import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import hashlib

# ================= CONFIG =================
st.set_page_config(page_title="Aplikasi Kinerja KPU", layout="wide")

st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}
.block-container {padding:1rem;}
button {height:45px;border-radius:8px;}
</style>
""", unsafe_allow_html=True)

st.title("📊 Aplikasi Kinerja KPU")

# ================= AUTH =================
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

# ================= FUNCTION =================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

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
            (users_df["NIP"].astype(str) == nip) &
            (users_df["Password"] == hash_password(pw))
        ]

        if not user.empty:
            u = user.iloc[0]
            st.session_state.login = True
            st.session_state.nama = u["Nama"]
            st.session_state.nip = u["NIP"]
            st.session_state.jabatan = u["Jabatan"]
            st.session_state.role = u["Role"]
            st.success("Login berhasil")
            st.rerun()
        else:
            st.error("Login gagal")

    st.stop()

# ================= HEADER =================
st.success(f"Login sebagai: {st.session_state.nama} ({st.session_state.role})")

if st.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

data = load_data()

# ================= ROLE: PIMPINAN =================
if st.session_state.role == "pimpinan":

    st.subheader("📊 Dashboard Pimpinan")

    if not data.empty:
        data["Durasi (Jam)"] = pd.to_numeric(data.get("Durasi (Jam)", 0), errors='coerce').fillna(0)

        grafik = data.groupby("Nama")["Durasi (Jam)"].sum()
        st.bar_chart(grafik)

        st.dataframe(data, use_container_width=True)

    st.stop()

# ================= ROLE: PEGAWAI =================
if st.session_state.role == "pegawai":
    data = data[data["NIP"].astype(str) == str(st.session_state.nip)]

# ================= FORM INPUT =================
st.subheader("📝 Input Kinerja")

with st.form("form"):
    nama = st.text_input("Nama", value=st.session_state.nama, disabled=True)
    nip = st.text_input("NIP", value=st.session_state.nip, disabled=True)
    jabatan = st.text_input("Jabatan", value=st.session_state.jabatan, disabled=True)

    tanggal = st.date_input("Tanggal", datetime.today())
    jam_masuk = st.text_input("Jam Masuk (HH:MM)", "08:00")
    jam_keluar = st.text_input("Jam Keluar (HH:MM)", "17:00")

    uraian = st.text_area("Uraian")
    output = st.text_area("Output")

    lokasi = st.selectbox("Lokasi", ["Kantor", "Rumah", "Dinas"])

    submit = st.form_submit_button("Simpan")

if submit:
    try:
        jm = datetime.strptime(jam_masuk, "%H:%M")
        jk = datetime.strptime(jam_keluar, "%H:%M")

        durasi = (jk - jm).seconds // 3600

        sheet.append_row([
            nama, nip, jabatan,
            str(tanggal),
            jam_masuk, jam_keluar,
            durasi,
            uraian, output, lokasi
        ])

        st.success("Data tersimpan")
        st.rerun()

    except:
        st.error("Format jam salah")

# ================= DATA =================
st.subheader("📋 Data")

st.dataframe(data, use_container_width=True)

# ================= ADMIN =================
if st.session_state.role == "admin":

    tab1, tab2, tab3 = st.tabs(["➕ User", "✏️ Edit User", "🗑️ Hapus User"])

    users_df = load_users()

    # ===== TAMBAH USER =====
    with tab1:
        nip_b = st.text_input("NIP Baru")
        nama_b = st.text_input("Nama Baru")
        jabatan_b = st.text_input("Jabatan")
        pw_b = st.text_input("Password", type="password")
        role_b = st.selectbox("Role", ["pegawai","admin","pimpinan"])

        if st.button("Tambah User"):
            user_sheet.append_row([
                nip_b, nama_b, jabatan_b,
                hash_password(pw_b),
                role_b
            ])
            st.success("User ditambahkan")
            st.rerun()

    # ===== EDIT USER =====
    with tab2:
        pilih = st.selectbox("Pilih NIP", users_df["NIP"].astype(str))

        u = users_df[users_df["NIP"].astype(str)==pilih].iloc[0]

        nama_e = st.text_input("Nama", u["Nama"])
        jabatan_e = st.text_input("Jabatan", u["Jabatan"])
        pw_e = st.text_input("Password Baru", type="password")
        role_e = st.selectbox("Role", ["pegawai","admin","pimpinan"])

        if st.button("Update User"):
            all_data = user_sheet.get_all_values()
            for i,row in enumerate(all_data):
                if row[0]==pilih:
                    pw_final = row[3] if pw_e=="" else hash_password(pw_e)
                    user_sheet.update(f"A{i+1}:E{i+1}", [[pilih,nama_e,jabatan_e,pw_final,role_e]])
                    st.success("Updated")
                    st.rerun()

    # ===== HAPUS USER =====
    with tab3:
        hapus = st.selectbox("Hapus NIP", users_df["NIP"].astype(str))

        if st.button("Hapus User"):
            all_data = user_sheet.get_all_values()
            for i,row in enumerate(all_data):
                if row[0]==hapus:
                    user_sheet.delete_rows(i+1)
                    st.success("Dihapus")
                    st.rerun()

    # ===== RESET PASSWORD =====
    st.subheader("🔑 Reset Password")
    reset_nip = st.selectbox("Pilih User", users_df["NIP"].astype(str))
    new_pw = st.text_input("Password Baru", type="password")

    if st.button("Reset"):
        all_data = user_sheet.get_all_values()
        for i,row in enumerate(all_data):
            if row[0]==reset_nip:
                user_sheet.update(f"D{i+1}", hash_password(new_pw))
                st.success("Password direset")
                st.rerun()

    # ===== EDIT DATA =====
    st.subheader("✏️ Edit Data Kinerja")

    if not data.empty:
        idx = st.selectbox("Pilih Index", data.index)

        uraian_e = st.text_area("Uraian", data.loc[idx,"Uraian Pekerjaan"])
        output_e = st.text_area("Output", data.loc[idx,"Output Pekerjaan"])

        if st.button("Update Data"):
            row_num = idx + 2
            sheet.update(f"H{row_num}:I{row_num}", [[uraian_e,output_e]])
            st.success("Updated")
            st.rerun()

    # ===== HAPUS DATA =====
    st.subheader("🗑️ Hapus Data")

    idx_h = st.selectbox("Pilih Data", data.index)

    if st.button("Hapus Data"):
        sheet.delete_rows(idx_h+2)
        st.success("Dihapus")
        st.rerun()