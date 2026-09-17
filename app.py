import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Page Configuration
st.set_page_config(page_title="Müşteri Kayıp Zaman Takip Sistemi", layout="wide", page_icon="⏱️")

# Google Sheet URL & Ayarları
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UsGlWxzRmiriAufzk14D0oiS3CyHMAjENyFhIbw9VG4/edit?pli=1&gid=0#gid=0"

SUTUNLAR = [
    "ID", "Tarih", "Müşteri Adı", "Sorumlu Mühendis", "İrsaliye No", 
    "Referans No", "Seri No", "Duruş Nedeni", "İşlem Açıklaması", 
    "Gelen Parti Miktarı", "Hata Oranı (%)", "P/H", 
    "Hesaplanan Zaman (Saat)", "Kayıp Zaman (Saat)", "Son Durum", 
    "Etiket Görseli Linki", "Hata Görseli Linki", "Onay Belgesi Linki"
]

DURUM_OPSIYONLARI = ["Mail Atıldı", "Onay Geldi", "Red Oldu", "Revize İstendi"]
DURUS_NEDENLERI = [
    "Rework / Yeniden İşleme", 
    "Malzeme Eksikliği / Bekleme", 
    "Kalite Problemi / Ayıklama", 
    "Ekipman / Line Arızası", 
    "Kalıp / Parça Uyumsuzluğu", 
    "Diğer"
]

# --- GOOGLE SHEETS BAĞLANTI FONKSİYONU (GSPREAD) ---
def get_gspread_client():
    try:
        # Streamlit secrets içinde gcp_service_account tanımlıysa onu kullanır
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            return client
    except Exception:
        pass
    return None

def load_data():
    try:
        client = get_gspread_client()
        if client:
            sheet = client.open_by_url(SHEET_URL).sheet1
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
        else:
            # Yedek okuma denemesi
            df = pd.DataFrame()
            
        for col in SUTUNLAR:
            if col not in df.columns:
                df[col] = None
        df = df[SUTUNLAR]
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
        return df
    except Exception as e:
        # Bağlantı kurulamazsa boş şema döner
        return pd.DataFrame(columns=SUTUNLAR)

def save_data(df):
    try:
        client = get_gspread_client()
        if client:
            sheet = client.open_by_url(SHEET_URL).sheet1
            sheet.clear()
            # DataFrame'i liste formatına çevirip yazma
            sheet.update([df.columns.values.tolist()] + df.fillna("").values.tolist())
            return True
    except Exception as e:
        st.error(f"Google Sheets Kayıt Hatası: {e}")
    return False

# --- KULLANICI / YETKİLENDİRME VERİ TABANI ---
if "users" not in st.session_state:
    st.session_state["users"] = {
        "omer.ocak": {
            "password": "OCK6161",
            "name": "Ömer OCAK",
            "role": "admin"
        },
        "mehmet.alasar": {
            "password": "MHMT3434",
            "name": "Mehmet ALAŞAR",
            "role": "viewer"
        }
    }

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

# --- LOGIN EKRANI ---
if not st.session_state["logged_in"]:
    st.title("⏱️ Müşteri Kayıp Zaman & Fatura Takip Sistemi")
    st.markdown("---")
    
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.subheader("🔒 Kullanıcı Girişi")
        with st.form("login_form"):
            username_input = st.text_input("Kullanıcı Adı").strip().lower()
            password_input = st.text_input("Parola", type="password").strip()
            login_btn = st.form_submit_button("Giriş Yap", use_container_width=True)
            
            if login_btn:
                users = st.session_state["users"]
                if username_input in users and users[username_input]["password"] == password_input:
                    st.session_state["logged_in"] = True
                    st.session_state["user_info"] = {
                        "username": username_input,
                        "name": users[username_input]["name"],
                        "role": users[username_input]["role"]
                    }
                    st.success(f"Hoş geldiniz, {users[username_input]['name']}!")
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya parola!")
    st.stop()

# --- SİDEBAR ---
user = st.session_state["user_info"]
st.sidebar.title(f"👤 {user['name']}")
st.sidebar.caption(f"Rol: {'Yönetici (Tam Yetki)' if user['role'] == 'admin' else 'Görüntüleyici'}")

if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None
    st.rerun()

# --- ANA UYGULAMA ---
st.title("⏱️ Müşteri Kayıp Zaman & Fatura Takip Sistemi")
st.markdown("---")

if user["role"] == "admin":
    tab1, tab2, tab3 = st.tabs(["➕ Yeni Kayıt Ekle", "📊 Kayıt Yönetimi", "📈 Analiz & Rapor"])
else:
    tab2, tab3 = st.tabs(["📊 Kayıt Listesi", "📈 Analiz & Rapor"])

if user["role"] == "admin":
    with tab1:
        st.subheader("Referans Bazlı Kayıp Zaman Kayıt Formu")
        
        col1, col2 = st.columns(2)
        with col1:
            musteri_adi = st.text_input("Müşteri Adı *", key="f_musteri")
            sorumlu_muhendis = st.text_input("Sorumlu Mühendis", key="f_muhendis")
            irsaliye_no = st.text_input("İrsaliye No", key="f_irsaliye")
            referans_no = st.text_input("Referans No *", key="f_ref")
            seri_no = st.text_input("Seri No", key="f_seri")
            durus_nedeni = st.selectbox("Duruş Nedeni *", DURUS_NEDENLERI, key="f_neden")
            
        with col2:
            gelen_parti = st.number_input("Gelen Parti / Stok Miktarı", min_value=1, value=1000, step=10, key="f_parti")
            hata_orani = st.number_input("Hata Oranı (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5, key="f_hata")
            ph = st.number_input("P/H (Parça / Saat)", min_value=0.1, value=100.0, step=1.0, key="f_ph")
            
            canli_islem_adet = gelen_parti * (hata_orani / 100.0)
            canli_hesaplanan_saat = round(canli_islem_adet / ph, 2) if ph > 0 else 0.0
            
            zaman_modu = st.radio("Mod:", ["🤖 Otomatik", "✍️ Manuel"], horizontal=True, key="f_zaman_modu")
            if "Manuel" in zaman_modu:
                hesaplanan_zaman = st.number_input("Hesaplanan Zaman (Saat)", min_value=0.0, value=canli_hesaplanan_saat, step=0.1)
            else:
                hesaplanan_zaman = canli_hesaplanan_saat
                st.success(f"⏱️ Hesaplanan Zaman: {hesaplanan_zaman} Saat")
                
            kayip_zaman_saat = st.number_input("Kayıp Zaman (Saat) *", min_value=0.0, value=1.0, step=0.1)
            son_durum = st.selectbox("Son Durum *", DURUM_OPSIYONLARI)

        islem_aciklamasi = st.text_area("İşlem Açıklaması", key="f_aciklama")
        
        c1, c2, c3 = st.columns(3)
        with c1: etiket_gorseli_link = st.text_input("🏷️ Etiket Görseli Linki")
        with c2: hata_gorseli_link = st.text_input("📷 Hata Görseli Linki")
        with c3: onay_belgesi_link = st.text_input("📄 Onay Belgesi Linki")
            
        if st.button("💾 Kaydet", use_container_width=True, type="primary"):
            if not musteri_adi or not referans_no:
                st.error("Müşteri Adı ve Referans No zorunludur!")
            else:
                df = load_data()
                valid_ids = df['ID'].dropna()
                valid_ids = valid_ids[pd.to_numeric(valid_ids, errors='coerce').notnull()]
                yeni_id = int(valid_ids.max()) + 1 if not valid_ids.empty else 1
                
                yeni_kayit = pd.DataFrame([{
                    "ID": yeni_id, "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Müşteri Adı": musteri_adi, "Sorumlu Mühendis": sorumlu_muhendis,
                    "İrsaliye No": irsaliye_no, "Referans No": referans_no, "Seri No": seri_no,
                    "Duruş Nedeni": durus_nedeni, "İşlem Açıklaması": islem_aciklamasi,
                    "Gelen Parti Miktarı": gelen_parti, "Hata Oranı (%)": hata_orani, "P/H": ph,
                    "Hesaplanan Zaman (Saat)": hesaplanan_zaman, "Kayıp Zaman (Saat)": kayip_zaman_saat,
                    "Son Durum": son_durum, "Etiket Görseli Linki": etiket_gorseli_link,
                    "Hata Görseli Linki": hata_gorseli_link, "Onay Belgesi Linki": onay_belgesi_link
                }])
                
                guncel_df = pd.concat([df, yeni_kayit], ignore_index=True)
                if save_data(guncel_df):
                    st.success(f"ID #{yeni_id} başarıyla kaydedildi!")
                    st.rerun()

with tab2:
    df = load_data()
    if user["role"] == "admin":
        st.subheader("📊 Kayıt Yönetimi")
        if df.empty:
            st.info("Kayıt bulunamadı.")
        else:
            if "Seç" not in df.columns: df.insert(0, "Seç", False)
            edited_df = st.data_editor(df, use_container_width=True, key="editor")
            
            if st.button("🔄 Değişiklikleri Kaydet"):
                clean_df = edited_df.drop(columns=["Seç"], errors="ignore")
                if save_data(clean_df):
                    st.success("Güncellendi!")
                    st.rerun()
    else:
        st.dataframe(df, use_container_width=True)

with tab3:
    st.subheader("Analiz & Özet")
    df = load_data()
    if not df.empty:
        m1, m2 = st.columns(2)
        m1.metric("Toplam Kayıt", len(df))
        m2.metric("Toplam Kayıp Zaman", f"{pd.to_numeric(df['Kayıp Zaman (Saat)'], errors='coerce').sum():.1f} Saat")
