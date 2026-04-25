import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
import gspread
from google.oauth2.service_account import Credentials

# PDF
from reportlab.pdfgen import canvas

# ================= CONFIG =================
st.set_page_config(page_title="E-Kinerja KPU", layout="wide")

# ================= CSS =================
st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
.stDeployButton {display:none;}

section[data-testid="stSidebar"] {
    background:#0b1c2c;
}
section[data-testid="stSidebar"] * {
    color:white !important;
}

.card {
    background:white;
    padding:18px;
    border-radius:12px;
    box-shadow:0 4px 10px rgba(0,0,0,0.08);
    text-align:center;
}
.big {font-size:28px;font-weight:bold;}
.header {
    background:linear-gradient(90deg,#ff4b2b,#ff416c);
    padding:20px;
    border-radius:12px;
    color:white;
}
.activity {
    background:white;
    padding:12px;
    border-radius:10px;
    margin-bottom:10px;
}
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
        ]
    )
    client = gspread.authorize(creds)
    return client.open_by_key("16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM")

spreadsheet = connect()
sheet = spreadsheet.sheet1

try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet("users",100,5)
    user_sheet.append_row(["NIP","Nama","Jabatan","Password","Role"])

# ================= UTIL =================
def safe(x): return "" if x is None else str(x)

def load_data():
    try: return pd.DataFrame(sheet.get_all_records())
    except: return pd.DataFrame()

def load_users():
    try: return pd.DataFrame(user_sheet.get_all_records())
    except: return pd.DataFrame()

def parse_jam(x):
    try:
        x=str(x).replace(".",":")
        h,m=map(int,x.split(":"))
        return h*60+m
    except:
        return None

def hitung_durasi(row):
    jm=parse_jam(row["Jam Masuk"])
    jk=parse_jam(row["Jam Keluar"])
    if jm is None or jk is None or jk<=jm:
        return 0
    return round((jk-jm)/60,2)

def get_data_with_index():
    df=load_data()
    if not df.empty:
        df["row_index"]=range(2,len(df)+2)
    return df

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login=False

users=load_users()

if not st.session_state.login:
    st.title("🔐 Login E-Kinerja")
    nip=st.text_input("NIP")
    pw=st.text_input("Password",type="password")

    if st.button("Login"):
        cek=users[(users["NIP"].astype(str)==str(nip)) &
                  (users["Password"].astype(str)==str(pw))]
        if not cek.empty:
            u=cek.iloc[0]
            st.session_state.login=True
            st.session_state.nama=u["Nama"]
            st.session_state.nip=u["NIP"]
            st.session_state.jabatan=u["Jabatan"]
            st.session_state.role=u["Role"]
            st.rerun()
        else:
            st.error("Login gagal")
    st.stop()

# ================= SIDEBAR =================
st.sidebar.write(f"👤 {st.session_state.nama}")

if st.session_state.role=="pegawai":
    menu=st.sidebar.radio("Menu",["Dashboard","Input","Data"])
elif st.session_state.role=="superadmin":
    menu=st.sidebar.radio("Menu",["Dashboard","Input","Data","Admin","System"])
else:
    menu=st.sidebar.radio("Menu",["Dashboard","Input","Data","Admin"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu=="Dashboard":
    df=load_data()
    if df.empty:
        st.info("Belum ada data"); st.stop()

    if st.session_state.role=="pegawai":
        df=df[df["NIP"].astype(str)==str(st.session_state.nip)]

    df["Durasi"]=df.apply(hitung_durasi,axis=1)

    total=len(df)
    jam=df["Durasi"].sum()
    hari=df["Tanggal"].nunique()

    st.markdown(f"<div class='header'><h2>Selamat datang {st.session_state.nama}</h2></div>",unsafe_allow_html=True)

    c1,c2,c3=st.columns(3)
    c1.markdown(f"<div class='card'><div class='big'>{total}</div>Total</div>",unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><div class='big'>{round(jam,2)}</div>Jam</div>",unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><div class='big'>{hari}</div>Hari</div>",unsafe_allow_html=True)

    col1,col2=st.columns([2,1])
    col1.bar_chart(df.groupby("Nama")["Durasi"].sum())

    latest=df.tail(5)
    for _,r in latest.iterrows():
        col2.markdown(f"<div class='activity'>{r['Tanggal']}<br>{r['Uraian']}</div>",unsafe_allow_html=True)

# ================= INPUT =================
elif menu=="Input":
    with st.form("form",clear_on_submit=True):
        tgl=st.date_input("Tanggal",date.today())
        masuk=st.text_input("Jam Masuk","07:30")
        keluar=st.text_input("Jam Keluar","16:00")
        uraian=st.text_area("Uraian")
        output=st.text_area("Output")
        lokasi=st.selectbox("Lokasi",["Kantor","Rumah","Dinas Luar / SPT"])
        simpan=st.form_submit_button("Simpan")

    if simpan:
        jm=parse_jam(masuk)
        jk=parse_jam(keluar)

        if jm is None or jk is None:
            st.error("Format jam salah")
        elif jk<=jm:
            st.error("Jam keluar salah")
        else:
            durasi=round((jk-jm)/60,2)

            sheet.append_row([
                safe(st.session_state.nama),
                safe(st.session_state.nip),
                safe(st.session_state.jabatan),
                safe(tgl.strftime("%Y-%m-%d")),
                safe(masuk),
                safe(keluar),
                float(durasi),
                safe(uraian),
                safe(output),
                safe(lokasi)
            ])

            st.success("Data tersimpan")

# ================= DATA =================
elif menu=="Data":

    df=get_data_with_index()
    df["Durasi (Jam)"]=df.apply(hitung_durasi,axis=1)

    if st.session_state.role=="pegawai":
        df=df[df["NIP"].astype(str)==str(st.session_state.nip)]
    else:
        mode=st.radio("Mode",["Semua Data","Data Saya"])
        if mode=="Data Saya":
            df=df[df["NIP"].astype(str)==str(st.session_state.nip)]

    st.dataframe(df)

    # EDIT HAPUS
    for i,row in df.iterrows():
        c1,c2,c3=st.columns([6,2,2])
        c1.write(row["Nama"])
        c2.write(row["Durasi (Jam)"])
        if c3.button("🗑",key=f"h{i}"):
            sheet.delete_rows(int(row["row_index"]))
            st.rerun()

    # DOWNLOAD EXCEL
    excel=io.BytesIO()
    df.to_excel(excel,index=False)
    st.download_button("Download Excel",excel.getvalue(),"data.xlsx")

    # PDF
    buffer=io.BytesIO()
    c=canvas.Canvas(buffer)
    y=800
    for _,r in df.iterrows():
        c.drawString(40,y,f"{r['Tanggal']} - {r['Nama']}")
        y-=20
    c.save()
    st.download_button("Download PDF",buffer.getvalue(),"data.pdf")

# ================= ADMIN =================
elif menu=="Admin":
    if st.session_state.role not in ["admin","superadmin"]:
        st.error("Akses ditolak"); st.stop()

    nip=st.text_input("NIP")
    nama=st.text_input("Nama")
    jabatan=st.text_input("Jabatan")
    pw=st.text_input("Password")
    role=st.selectbox("Role",["pegawai","admin","pimpinan","superadmin"])

    if st.button("Tambah"):
        user_sheet.append_row([nip,nama,jabatan,pw,role])
        st.success("User ditambah")

# ================= SYSTEM =================
elif menu=="System":
    if st.session_state.role!="superadmin":
        st.error("Akses ditolak"); st.stop()

    if st.button("Clear Cache"):
        st.cache_resource.clear()
        st.success("Cache dibersihkan")

    if st.button("Reload"):
        st.rerun()