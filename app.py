import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import io

# ================= CONFIG =================
st.set_page_config(page_title="E-Kinerja KPU", layout="wide")

# ================= CSS =================
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0b1f3a,#061224);
    color:white;
}
div[role="radiogroup"] label {
    color:white !important;
}
.header {
    background: linear-gradient(90deg,#ff4b4b,#ff7a7a);
    padding:20px;border-radius:15px;color:white;
}
.card {
    background:white;padding:20px;border-radius:15px;
    box-shadow:0 4px 10px rgba(0,0,0,0.1);
    text-align:center;
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
user_sheet = spreadsheet.worksheet("users")

# ================= FUNCTION =================
def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty:
        df["row_index"] = range(2, len(df)+2)
    return df

def load_users():
    return pd.DataFrame(user_sheet.get_all_records())

def parse_jam(x):
    try:
        h,m = str(x).replace(".",":").split(":")
        return int(h)*60 + int(m)
    except:
        return None

def hitung(jm,jk):
    jm = parse_jam(jm)
    jk = parse_jam(jk)
    if jm is None or jk is None or jk<=jm:
        return 0
    return round((jk-jm)/60,2)

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login=False

if not st.session_state.login:

    st.title("Login E-Kinerja")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    users = load_users()

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
            st.session_state.role=u["Role"]
            st.session_state.jabatan=u["Jabatan"]
            st.rerun()
        else:
            st.error("Login gagal")

    st.stop()

# ================= SIDEBAR =================
st.sidebar.markdown(f"### 👤 {st.session_state.nama}")

menu = st.sidebar.radio("Menu",[
    "Dashboard",
    "Input",
    "Data Kinerja",
    "Admin",
    "Superadmin"
])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu=="Dashboard":

    df = load_data()

    st.markdown(f"""
    <div class='header'>
    <h2>Aplikasi E-Kinerja</h2>
    <p>{datetime.now().strftime("%A, %d %B %Y")}</p>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(lambda x: hitung(x["Jam Masuk"],x["Jam Keluar"]),axis=1)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total",len(df))
    c2.metric("Jam",df["Durasi"].sum())
    c3.metric("Hari",df["Tanggal"].nunique())
    c4.metric("Pegawai",df["Nama"].nunique())

    st.bar_chart(df.groupby("Nama")["Durasi"].sum())

# ================= INPUT =================
elif menu=="Input":

    with st.form("form",clear_on_submit=True):

        tgl = st.date_input("Tanggal",date.today())
        masuk = st.text_input("Masuk","07:30")
        keluar = st.text_input("Keluar","16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")
        lokasi = st.selectbox("Lokasi",["Kantor","Rumah","Dinas Luar / SPT"])

        simpan = st.form_submit_button("Simpan")

    if simpan:
        d = hitung(masuk,keluar)

        sheet.append_row([
            str(st.session_state.nama),
            str(st.session_state.nip),
            str(st.session_state.jabatan),
            tgl.strftime("%Y-%m-%d"),
            str(masuk), str(keluar),
            float(d),
            str(uraian),
            str(output),
            str(lokasi)
        ])

        st.success("Data tersimpan")
        st.rerun()

# ================= DATA =================
elif menu=="Data Kinerja":

    df = load_data()
    df["Durasi"] = df.apply(lambda x: hitung(x["Jam Masuk"],x["Jam Keluar"]),axis=1)

    for i,row in df.iterrows():

        c1,c2,c3 = st.columns([6,2,2])

        with c1:
            st.write(f"**{row['Nama']}**")
            st.caption(row["Uraian"])

        with c2:
            st.write(f"{row['Durasi']} Jam")

        with c3:
            if st.button("✏️",key=f"e{i}"):
                st.session_state.edit=row

            if st.button("🗑",key=f"d{i}"):
                sheet.delete_rows(int(row["row_index"]))
                st.rerun()

    if "edit" in st.session_state:
        ed = st.session_state.edit

        masuk = st.text_input("Masuk",ed["Jam Masuk"])
        keluar = st.text_input("Keluar",ed["Jam Keluar"])
        uraian = st.text_area("Uraian",ed["Uraian"])

        if st.button("Update"):
            d = hitung(masuk,keluar)
            sheet.update(f"E{int(ed['row_index'])}:J{int(ed['row_index'])}",[[
                masuk, keluar, d, uraian, ed["Output"], ed["Lokasi"]
            ]])
            del st.session_state.edit
            st.rerun()

# ================= ADMIN PRO+ =================
elif menu=="Admin":

    if st.session_state.role not in ["admin","superadmin"]:
        st.error("Akses ditolak")
        st.stop()

    tab1,tab2,tab3 = st.tabs(["Tambah User","Manajemen User","Data"])

    # TAMBAH
    with tab1:
        nip = st.text_input("NIP")
        nama = st.text_input("Nama")
        jab = st.text_input("Jabatan")
        pw = st.text_input("Password")
        role = st.selectbox("Role",["pegawai","admin","pimpinan","superadmin"])

        if st.button("Tambah"):
            user_sheet.append_row([nip,nama,jab,pw,role])
            st.success("User ditambah")
            st.rerun()

    # MANAJEMEN USER
    with tab2:
        users = load_users()
        st.dataframe(users)

        for i,row in users.iterrows():
            if st.button(f"Hapus {row['Nama']}",key=f"u{i}"):
                user_sheet.delete_rows(i+2)
                st.rerun()

    # DATA
    with tab3:
        df = load_data()
        st.dataframe(df)

        if st.button("Reset Data"):
            sheet.batch_clear(["A2:J10000"])
            st.warning("Data direset")

# ================= SUPERADMIN =================
elif menu=="Superadmin":

    if st.session_state.role!="superadmin":
        st.error("Khusus Superadmin")
        st.stop()

    st.subheader("Superadmin Panel")

    if st.button("🔥 Reset TOTAL"):
        sheet.clear()
        st.warning("Semua data dihapus")

    st.dataframe(load_data())
    st.dataframe(load_users())