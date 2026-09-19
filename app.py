import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# Sayfa Yapılandırması
st.set_page_config(page_title="Müşteri Kayıp Zaman Takip Sistemi", layout="wide", page_icon="⏱️")

# Google Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UsGlWxzRmiriAufzk14D0oiS3CyHMAjENyFhIbw9VG4/edit?pli=1&gid=0#gid=0"

# --- SABİT DEĞİŞKENLER VE OPSİYONLAR ---
DURUM_OPSİYONLARI = ["Mail Atıldı", "Onay Geldi", "Red Oldu", "Revize İstendi"]

KAYIP_ZAMAN_TURU_OPSIYONLARI = [
    "Gelen Ek İşçilik Talepleri / GKK Yakalamaları / Ücretli Rework",
    "Hat Duruşları Kaynaklı"
]

DURUS_NEDENLERI = [
    "Rework / Yeniden İşleme", 
    "Malzeme Eksikliği / Bekleme", 
    "Kalite Problemi / Ayıklama", 
    "Ekipman / Line Arızası", 
    "Kalıp / Parça Uyumsuzluğu", 
    "Diğer"
]

DONEM_LISTESI = [
    "Ocak 2026", "Şubat 2026", "Mart 2026", "Nisan 2026", "Mayıs 2026", "Haziran 2026",
    "Temmuz 2026", "Ağustos 2026", "Eylül 2026", "Ekim 2026", "Kasım 2026", "Aralık 2026",
    "Ocak 2027", "Şubat 2027", "Mart 2027", "Nisan 2027", "Mayıs 2027", "Haziran 2027",
    "Temmuz 2027", "Ağustos 2027", "Eylül 2027", "Ekim 2027", "Kasım 2027", "Aralık 2027"
]

SUTUNLAR = [
    "ID", "Tarih", "Kayıp Zaman Türü", "Dönem (Ay/Yıl)", "Müşteri Adı", "Sorumlu Mühendis", "İrsaliye No", 
    "Referans No", "Seri No", "Duruş Nedeni", "İşlem Açıklaması", 
    "Gelen Parti Miktarı", "Hata Oranı (%)", "P/H", 
    "Hesaplanan Zaman (Saat)", "Kayıp Zaman (Saat)", "Saatlik İşçilik Ücreti (TL)", "Toplam Tutar (TL)", "Son Durum", 
    "İrsaliye Görseli Linki", "Etiket Görseli Linki", "Hata Görseli Linki", "Onay Belgesi Linki"
]

GECMIS_SUTUNLAR = [
    "ID", "DÖNEM", "TALEP EDİLEN SAAT", "ONAYLANAN SAAT", "SAATLİK ÜCRET", 
    "TALEP EDİLEN TUTAR", "ONAYLANAN TUTAR", "KESİNTİ TUTARI", "KESİNTİ AÇIKLAMASI", "GENEL AÇIKLAMA"
]

ODEME_SUTUNLAR = [
    "ID", "MÜŞTERİ ADI", "ÖDEME DURUMU", "PARA BİRİMİ", "TCBM KUR", "AÇIKLAMA NOTLAR", "GERÇEKLEŞEN GELEN ÖZEL TUTAR"
]

# --- GSPREAD BAĞLANTISI ---
def get_gspread_client():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Kimlik doğrulama hatası: {e}")
        return None

# --- ANA TABLO (guncel) İŞLEMLERİ ---
@st.cache_data(ttl=600, show_spinner="Google Sheets'ten veriler yükleniyor...")
def load_data_cached():
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_url(SHEET_URL)
            try:
                worksheet = spreadsheet.worksheet("guncel")
            except:
                worksheet = spreadsheet.get_worksheet(0)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame(columns=SUTUNLAR)
            
        for col in SUTUNLAR:
            if col not in df.columns:
                df[col] = None
        df = df[SUTUNLAR]
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
        
        for num_col in ['Kayıp Zaman (Saat)', 'Hesaplanan Zaman (Saat)', 'Hata Oranı (%)', 'P/H', 'Saatlik İşçilik Ücreti (TL)', 'Toplam Tutar (TL)']:
            if num_col in df.columns:
                s = df[num_col].astype(str).str.strip().str.replace(',', '', regex=False).str.replace('.', '', regex=False)
                numeric_vals = pd.to_numeric(s, errors='coerce').fillna(0.0) / (100.0 if '%' in num_col else 1.0)
                df[num_col] = numeric_vals.round(2)
        
        df['Gelen Parti Miktarı'] = pd.to_numeric(df['Gelen Parti Miktarı'], errors='coerce').fillna(0).astype(int)
        
        if "Dönem (Ay/Yıl)" in df.columns:
            df["Dönem (Ay/Yıl)"] = df["Dönem (Ay/Yıl)"].astype(str).str.strip()
            df["Dönem (Ay/Yıl)"] = df["Dönem (Ay/Yıl)"].replace(["nan", "None", ""], "Eylül 2026")
            
        return df
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return pd.DataFrame(columns=SUTUNLAR)

def load_data():
    return load_data_cached()

def update_google_sheet(df):
    try:
        client = get_gspread_client()
        if not client:
            return False
        spreadsheet = client.open_by_url(SHEET_URL)
        try:
            worksheet = spreadsheet.worksheet("guncel")
        except:
            worksheet = spreadsheet.get_worksheet(0)
        
        df_to_write = df.copy()
        for col in ['Hesaplanan Zaman (Saat)', 'Kayıp Zaman (Saat)', 'Hata Oranı (%)', 'P/H', 'Saatlik İşçilik Ücreti (TL)', 'Toplam Tutar (TL)']:
            if col in df_to_write.columns:
                num_series = pd.to_numeric(df_to_write[col], errors='coerce').fillna(0.0).round(2)
                df_to_write[col] = num_series.apply(lambda x: f"{x:.2f}".replace('.', ','))
                
        df_to_write = df_to_write.fillna("")
        worksheet.clear()
        worksheet.update([df_to_write.columns.values.tolist()] + df_to_write.values.tolist())
        
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Google Sheets güncelleme hatası: {e}")
        return False

# --- GEÇMİŞ DÖNEM (gecmisdonem) İŞLEMLERİ ---
@st.cache_data(ttl=600, show_spinner="Geçmiş dönem verileri yükleniyor...")
def load_gecmis_data_cached():
    varsayilan_liste = [
        {"ID": 1, "DÖNEM": "Şubat 2026", "TALEP EDİLEN SAAT": 0.0, "ONAYLANAN SAAT": 0.0, "SAATLİK ÜCRET": 500.0, "TALEP EDİLEN TUTAR": 0.0, "ONAYLANAN TUTAR": 0.0, "KESİNTİ TUTARI": 0.0, "KESİNTİ AÇIKLAMASI": "Süreç başlangıcı", "GENEL AÇIKLAMA": "Başlangıç"},
        {"ID": 2, "DÖNEM": "Mart 2026", "TALEP EDİLEN SAAT": 0.0, "ONAYLANAN SAAT": 0.0, "SAATLİK ÜCRET": 500.0, "TALEP EDİLEN TUTAR": 0.0, "ONAYLANAN TUTAR": 0.0, "KESİNTİ TUTARI": 0.0, "KESİNTİ AÇIKLAMASI": "Veri bekleniyor", "GENEL AÇIKLAMA": "Beklemede"},
        {"ID": 3, "DÖNEM": "Nisan 2026", "TALEP EDİLEN SAAT": 0.0, "ONAYLANAN SAAT": 0.0, "SAATLİK ÜCRET": 500.0, "TALEP EDİLEN TUTAR": 0.0, "ONAYLANAN TUTAR": 0.0, "KESİNTİ TUTARI": 0.0, "KESİNTİ AÇIKLAMASI": "Veri bekleniyor", "GENEL AÇIKLAMA": "Beklemede"},
        {"ID": 4, "DÖNEM": "Mayıs 2026", "TALEP EDİLEN SAAT": 0.0, "ONAYLANAN SAAT": 0.0, "SAATLİK ÜCRET": 500.0, "TALEP EDİLEN TUTAR": 0.0, "ONAYLANAN TUTAR": 0.0, "KESİNTİ TUTARI": 0.0, "KESİNTİ AÇIKLAMASI": "Veri bekleniyor", "GENEL AÇIKLAMA": "Beklemede"},
        {"ID": 5, "DÖNEM": "Haziran 2026", "TALEP EDİLEN SAAT": 0.0, "ONAYLANAN SAAT": 0.0, "SAATLİK ÜCRET": 500.0, "TALEP EDİLEN TUTAR": 0.0, "ONAYLANAN TUTAR": 0.0, "KESİNTİ TUTARI": 0.0, "KESİNTİ AÇIKLAMASI": "Veri bekleniyor", "GENEL AÇIKLAMA": "Beklemede"},
        {"ID": 6, "DÖNEM": "Temmuz 2026", "TALEP EDİLEN SAAT": 0.0, "ONAYLANAN SAAT": 0.0, "SAATLİK ÜCRET": 500.0, "TALEP EDİLEN TUTAR": 0.0, "ONAYLANAN TUTAR": 0.0, "KESİNTİ TUTARI": 0.0, "KESİNTİ AÇIKLAMASI": "Veri bekleniyor", "GENEL AÇIKLAMA": "Beklemede"},
        {"ID": 7, "DÖNEM": "Ağustos 2026", "TALEP EDİLEN SAAT": 0.0, "ONAYLANAN SAAT": 0.0, "SAATLİK ÜCRET": 500.0, "TALEP EDİLEN TUTAR": 0.0, "ONAYLANAN TUTAR": 0.0, "KESİNTİ TUTARI": 0.0, "KESİNTİ AÇIKLAMASI": "Veri bekleniyor", "GENEL AÇIKLAMA": "Beklemede"},
        {"ID": 8, "DÖNEM": "Eylül 2026", "TALEP EDİLEN SAAT": 26.92, "ONAYLANAN SAAT": 26.92, "SAATLİK ÜCRET": 500.0, "TALEP EDİLEN TUTAR": 13460.0, "ONAYLANAN TUTAR": 13460.0, "KESİNTİ TUTARI": 0.0, "KESİNTİ AÇIKLAMASI": "Yok", "GENEL AÇIKLAMA": "Aktif Dönem"}
    ]
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_url(SHEET_URL)
            try:
                worksheet = spreadsheet.worksheet("gecmisdonem")
                data = worksheet.get_all_records()
                data = [row for row in data if row.get("ID") != "" and row.get("ID") is not None]
                df = pd.DataFrame(data)
                if df.empty:
                    df = pd.DataFrame(varsayilan_liste)
            except:
                df = pd.DataFrame(varsayilan_liste)
        else:
            df = pd.DataFrame(varsayilan_liste)
            
        for col in GECMIS_SUTUNLAR:
            if col not in df.columns:
                df[col] = 0.0 if "SAAT" in col or "TUTAR" in col or "ÜCRET" in col else ""
        df = df[GECMIS_SUTUNLAR]
        return df.to_dict(orient="records")
    except Exception:
        return varsayilan_liste

def update_gecmis_google_sheet(liste_veri):
    try:
        client = get_gspread_client()
        if not client:
            return True
        spreadsheet = client.open_by_url(SHEET_URL)
        try:
            worksheet = spreadsheet.worksheet("gecmisdonem")
        except:
            worksheet = spreadsheet.add_worksheet(title="gecmisdonem", rows="100", cols="20")
            
        df_to_write = pd.DataFrame(liste_veri)
        for col in GECMIS_SUTUNLAR:
            if col not in df_to_write.columns:
                df_to_write[col] = ""
        df_to_write = df_to_write[GECMIS_SUTUNLAR]
        
        for col in ["TALEP EDİLEN SAAT", "ONAYLANAN SAAT", "SAATLİK ÜCRET", "TALEP EDİLEN TUTAR", "ONAYLANAN TUTAR", "KESİNTİ TUTARI"]:
            if col in df_to_write.columns:
                num_series = pd.to_numeric(df_to_write[col], errors='coerce').fillna(0.0).round(2)
                df_to_write[col] = num_series.apply(lambda x: str(x).replace('.', ','))
                
        df_to_write = df_to_write.fillna("")
        worksheet.clear()
        worksheet.update([df_to_write.columns.values.tolist()] + df_to_write.values.tolist())
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Geçmiş dönem sheets güncelleme hatası: {e}")
        return False

# --- ÖDEME TAHSİLAT İŞLEMLERİ ---
@st.cache_data(ttl=600, show_spinner="Ödeme tahsilat verileri yükleniyor...")
def load_odeme_data_cached():
    varsayilan_odeme = [
        {"ID": 1, "MÜŞTERİ ADI": "Legrand (Geçmiş Devir)", "ÖDEME DURUMU": "Gelen Ödeme", "PARA BİRİMİ": "TL (₺)", "TCBM KUR": 1.0, "AÇIKLAMA NOTLAR": "Şubat dönemi geçmiş devir ödemesi.", "GERÇEKLEŞEN GELEN ÖZEL TUTAR": 120000.00},
        {"ID": 2, "MÜŞTERİ ADI": "Legrand", "ÖDEME DURUMU": "Gelen Ödeme", "PARA BİRİMİ": "TL (₺)", "TCBM KUR": 1.0, "AÇIKLAMA NOTLAR": "Eylül ayı fatura tahsilatı alındı.", "GERÇEKLEŞEN GELEN ÖZEL TUTAR": 155252.00}
    ]
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_url(SHEET_URL)
            try:
                worksheet = spreadsheet.worksheet("odeme-tahsilat-takip")
                data = worksheet.get_all_records()
                data = [row for row in data if row.get("ID") != "" and row.get("ID") is not None]
                df = pd.DataFrame(data)
                if df.empty:
                    df = pd.DataFrame(varsayilan_odeme)
            except:
                df = pd.DataFrame(varsayilan_odeme)
        else:
            df = pd.DataFrame(varsayilan_odeme)
            
        for col in ODEME_SUTUNLAR:
            if col not in df.columns:
                df[col] = ""
        df = df[ODEME_SUTUNLAR]
        return df.to_dict(orient="records")
    except Exception:
        return varsayilan_odeme

def update_odeme_google_sheet(liste_veri):
    try:
        client = get_gspread_client()
        if not client:
            return True
        spreadsheet = client.open_by_url(SHEET_URL)
        try:
            worksheet = spreadsheet.worksheet("odeme-tahsilat-takip")
        except:
            worksheet = spreadsheet.add_worksheet(title="odeme-tahsilat-takip", rows="100", cols="20")
            
        df_to_write = pd.DataFrame(liste_veri)
        for col in ODEME_SUTUNLAR:
            if col not in df_to_write.columns:
                df_to_write[col] = ""
        df_to_write = df_to_write[ODEME_SUTUNLAR]

        if "GERÇEKLEŞEN GELEN ÖZEL TUTAR" in df_to_write.columns:
            num_series = pd.to_numeric(df_to_write["GERÇEKLEŞEN GELEN ÖZEL TUTAR"], errors='coerce').fillna(0.0).round(2)
            df_to_write["GERÇEKLEŞEN GELEN ÖZEL TUTAR"] = num_series.apply(lambda x: str(x).replace('.', ','))
            
        df_to_write = df_to_write.fillna("")
        worksheet.clear()
        worksheet.update([df_to_write.columns.values.tolist()] + df_to_write.values.tolist())
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Ödeme sheets güncelleme hatası: {e}")
        return False

# --- KULLANICI / YETKİLENDİRME VERİ TABANI ---
if "users" not in st.session_state:
    st.session_state["users"] = {
        "omer.ocak": {"password": "OCK6161", "name": "Ömer OCAK", "role": "admin", "group": "Yönetim Kadrosu"},
        "mehmet.alasar": {"password": "malasar34.", "name": "Mehmet ALAŞAR", "role": "viewer", "group": "Yönetim Kadrosu"},
        "dilber.alasar": {"password": "dalasar34.", "name": "Dilber ALAŞAR", "role": "viewer", "group": "Yönetim Kadrosu"},
        "hakan.alasar": {"password": "halasar34.", "name": "Hakan ALAŞAR", "role": "viewer", "group": "Yönetim Kadrosu"},
        "uretim": {"password": "uretim34.", "name": "Üretim Birimi", "role": "user", "group": "Kullanıcı"},
        "muhasebe": {"password": "mhalasar34.", "name": "Muhasebe Birimi", "role": "accounting", "group": "Kullanıcı"},
        "turgay.yigit": {"password": "talasar34.", "name": "Turgay YİĞİT", "role": "user", "group": "Kullanıcı"}
    }

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

# --- ORTAK CHAT HAFIZASI ---
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = [
        {"zaman": "19.09.2026 10:30", "gonderen": "Mehmet ALAŞAR", "mesaj": "Ömer Bey, eylül ayı raporunu kontrol edebilir misiniz?", "dosya_linki": ""}
    ]

# Verileri Session State'e yükle
if "gecmis_ozetler" not in st.session_state:
    st.session_state["gecmis_ozetler"] = load_gecmis_data_cached()

if "odeme_kayitlari" not in st.session_state:
    st.session_state["odeme_kayitlari"] = load_odeme_data_cached()

# --- LOGIN EKRANI ---
if not st.session_state["logged_in"]:
    st.title("⏱️ Müşteri Kayıp Zaman & Fatura Takip Sistemi")
    st.markdown("---")
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.subheader("🔒 Kullanıcı Girişi")
        with st.form("login_form"):
            user_keys = list(st.session_state["users"].keys())
            secilen_kullanici = st.selectbox("Kullanıcı Adı Seçin", options=user_keys)
            password_input = st.text_input("Parola", type="password").strip()
            login_btn = st.form_submit_button("Giriş Yap", use_container_width=True)
            
            if login_btn:
                users = st.session_state["users"]
                if secilen_kullanici in users and users[secilen_kullanici]["password"] == password_input:
                    st.session_state["logged_in"] = True
                    st.session_state["user_info"] = {
                        "username": secilen_kullanici,
                        "name": users[secilen_kullanici]["name"],
                        "role": users[secilen_kullanici]["role"],
                        "group": users[secilen_kullanici]["group"]
                    }
                    st.success(f"Hoş geldiniz, {users[secilen_kullanici]['name']}!")
                    st.rerun()
                else:
                    st.error("Hatalı parola!")
    st.stop()

# --- SİDEBAR ---
user = st.session_state["user_info"]
st.sidebar.title(f"👤 {user['name']}")
st.sidebar.caption(f"Grup: {user['group']} | Rol: {'Yönetici (Admin)' if user['role'] == 'admin' else 'Muhasebe' if user['role'] == 'accounting' else 'Kullanıcı'}")

with st.sidebar.expander("🔑 Parola Değiştir"):
    with st.form("change_pass_form"):
        old_p = st.text_input("Mevcut Parola", type="password")
        new_p = st.text_input("Yeni Parola", type="password")
        btn_pass = st.form_submit_button("Parolayı Güncelle")
        
        if btn_pass:
            curr_pass = st.session_state["users"][user["username"]]["password"]
            if old_p != curr_pass:
                st.error("Mevcut parola yanlış!")
            elif len(new_p) < 4:
                st.warning("Parola en az 4 karakter olmalıdır.")
            else:
                st.session_state["users"][user["username"]]["password"] = new_p
                st.success("Parolanız başarıyla değiştirildi!")

if st.sidebar.button("🔄 Verileri Yenile (Cache Temizle)", use_container_width=True):
    st.cache_data.clear()
    st.success("Önbellek temizlendi, veriler yeniden yükleniyor...")
    st.rerun()

if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None
    st.rerun()

# --- ANA UYGULAMA ---
st.title("⏱️ Müşteri Kayıp Zaman & Fatura Takip Sistemi")
st.markdown("---")

df = load_data()

# Sekme Yapısı
if user["role"] == "admin":
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "➕ Yeni Kayıp Zaman Kaydı Ekle", 
        "📊 Kayıt Yönetimi (Düzenle & Sil)", 
        "📈 Analiz, Grafik & Ödemeler", 
        "📁 Geçmiş Dönem Manuel Veriler", 
        "💬 Canlı Soru & Sohbet",
        "💰 Gelen Ödemeler & Tahsilatlar"
    ])
elif user["role"] == "accounting":
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💰 Ödeme Bilgisi Gir",
        "📊 Kayıt Listesi", 
        "📈 Analiz, Grafik & Ödemeler", 
        "📁 Geçmiş Dönem Manuel Veriler", 
        "💬 Canlı Soru & Sohbet",
        "💰 Gelen Ödemeler & Tahsilatlar"
    ])
else:
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Kayıt Listesi (Salt Okunur)", 
        "📈 Analiz, Grafik & Ödemeler", 
        "📁 Geçmiş Dönem Manuel Veriler", 
        "💬 Canlı Soru & Sohbet",
        "💰 Gelen Ödemeler & Tahsilatlar",
        "ℹ️ Bilgi"
    ])

# ---------------- TAB 1 ----------------
with tab1:
    if user["role"] == "admin":
        st.subheader("Referans Bazlı Kayıp Zaman Kayıt Formu")
        
        kayip_zaman_turu = st.radio(
            "📌 Kayıp Zaman / İşlem Kategorisi Seçin *",
            options=KAYIP_ZAMAN_TURU_OPSIYONLARI,
            horizontal=True,
            key="f_kayip_zaman_turu"
        )
        st.markdown("---")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            secilen_donem_form = st.selectbox("Dönem Seçin (Ay / Yıl) *", options=DONEM_LISTESI, index=8, key="f_donem")
            musteri_adi = st.text_input("Müşteri Adı *", key="f_musteri")
            sorumlu_muhendis = st.text_input("Müşteri Sorumlu Mühendis Adı", key="f_muhendis")
            irsaliye_no = st.text_input("İrsaliye No", key="f_irsaliye")
            referans_no = st.text_input("Referans No *", key="f_ref")
            seri_no = st.text_input("Seri No", key="f_seri")
            durus_nedeni = st.selectbox("Duruş / Zaman Kaybı Nedeni *", DURUS_NEDENLERI, key="f_neden")
            
        with col_f2:
            gelen_parti = st.number_input("Gelen Parti / Stok Miktarı (Adet)", min_value=1, value=14000, step=10, key="f_parti")
            hata_orani = st.number_input("Hata Oranı (%)", min_value=0.0, max_value=100.0, value=100.0, step=0.5, key="f_hata")
            ph = st.number_input("P/H (Parça / Saat)", min_value=0.1, value=520.0, step=1.0, key="f_ph")
            
            canli_islem_adet = gelen_parti * (hata_orani / 100.0)
            canli_hesaplanan_saat = round(canli_islem_adet / ph, 2) if ph > 0 else 0.0
            
            st.markdown("---")
            zaman_modu = st.radio(
                "Mod Seçimi:",
                ["🤖 Otomatik Formülle Hesapla", "✍️ Manuel Zaman Gir"],
                horizontal=True,
                key="f_zaman_modu"
            )
            
            if "Manuel" in zaman_modu:
                hesaplanan_zaman = st.number_input(
                    "⏱️ Hesaplanan Zaman (Saat) [Manuel Giriş]", 
                    min_value=0.0, 
                    value=canli_hesaplanan_saat, 
                    step=0.1, 
                    format="%.2f",
                    key="f_hesaplanan_manuel"
                )
            else:
                hesaplanan_zaman = canli_hesaplanan_saat
                st.success(f"⏱️ **Hesaplanan Zaman: {hesaplanan_zaman:.2f} Saat**  \n*(Detay: {int(canli_islem_adet)} Adet Hatalı Parça / {ph} P/H)*")
                
            st.markdown("---")
            kayip_zaman_saat = st.number_input("Kayıp Zaman / Fiili Duruş (Saat) *", min_value=0.0, value=26.92, step=0.1, format="%.2f", key="f_kayip")
            
            saatlik_ucret = st.number_input("💵 Saatlik İşçilik Ücreti (TL) *", min_value=0.0, value=500.0, step=10.0, format="%.2f", key="f_saatlik_ucret")
            toplam_tutar_hesaplanan = round(kayip_zaman_saat * saatlik_ucret, 2)
            st.info(f"💰 **Hesaplanan Toplam Tutar: {toplam_tutar_hesaplanan:,.2f} TL**".replace(",", "X").replace(".", ",").replace("X", "."))
            
            son_durum = st.selectbox("Son Durum *", ["Mail Atıldı", "Onay Geldi", "Red Oldu", "Revize İstendi"], key="f_durum")

        islem_aciklamasi = st.text_area("İşlem Açıklaması", placeholder="Yapılan işlem, duruş gerekçesi ve detaylar...", key="f_aciklama")
        
        c_link0, c_link1, c_link2, c_link3 = st.columns(4)
        with c_link0:
            irsaliye_gorseli_link = st.text_input("📦 İrsaliye Görseli Linki", key="f_irsaliye_link")
        with c_link1:
            etiket_gorseli_link = st.text_input("🏷️ Etiket Görseli Linki", key="f_etiket")
        with c_link2:
            hata_gorseli_link = st.text_input("📷 Hata Görseli Linki", key="f_gorsel")
        with c_link3:
            onay_belgesi_link = st.text_input("📄 Onay Belgesi Linki", key="f_onay")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Kaydı Google Tabloya Kaydet", use_container_width=True, type="primary"):
            if not musteri_adi or not referans_no:
                st.error("Lütfen Müşteri Adı ve Referans No alanlarını doldurunuz!")
            else:
                mevcut_df = load_data()
                valid_ids = mevcut_df['ID'].dropna()
                valid_ids = valid_ids[pd.to_numeric(valid_ids, errors='coerce').notnull()]
                yeni_id = int(valid_ids.max()) + 1 if not valid_ids.empty else 1
                bugun = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                yeni_kayit = pd.DataFrame([{
                    "ID": yeni_id,
                    "Tarih": bugun,
                    "Kayıp Zaman Türü": kayip_zaman_turu,
                    "Dönem (Ay/Yıl)": secilen_donem_form,
                    "Müşteri Adı": musteri_adi,
                    "Sorumlu Mühendis": sorumlu_muhendis,
                    "İrsaliye No": irsaliye_no,
                    "Referans No": referans_no,
                    "Seri No": seri_no,
                    "Duruş Nedeni": durus_nedeni,
                    "İşlem Açıklaması": islem_aciklamasi,
                    "Gelen Parti Miktarı": gelen_parti,
                    "Hata Oranı (%)": float(hata_orani),
                    "P/H": float(ph),
                    "Hesaplanan Zaman (Saat)": round(float(hesaplanan_zaman), 2),
                    "Kayıp Zaman (Saat)": round(float(kayip_zaman_saat), 2),
                    "Saatlik İşçilik Ücreti (TL)": round(float(saatlik_ucret), 2),
                    "Toplam Tutar (TL)": round(float(toplam_tutar_hesaplanan), 2),
                    "Son Durum": son_durum,
                    "İrsaliye Görseli Linki": irsaliye_gorseli_link,
                    "Etiket Görseli Linki": etiket_gorseli_link,
                    "Hata Görseli Linki": hata_gorseli_link,
                    "Onay Belgesi Linki": onay_belgesi_link
                }])
                
                guncel_df = pd.concat([mevcut_df, yeni_kayit], ignore_index=True)
                if update_google_sheet(guncel_df):
                    st.success(f"ID #{yeni_id} ({secilen_donem_form} - {musteri_adi}) başarıyla Google Sheets'e kaydedildi!")
                    st.rerun()

    elif user["role"] == "accounting":
        st.subheader("💰 Müşteri Ödemesi / Tahsilat Girişi")
        
        gecmis_liste = st.session_state["gecmis_ozetler"]
        donem_secenekleri = [
            f"{item.get('DÖNEM', '')} — Onaylanan Tutar: {float(item.get('ONAYLANAN TUTAR', 0) or 0):,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".") 
            for item in gecmis_liste 
            if isinstance(item, dict) and item.get('DÖNEM')
        ]
        
        if not donem_secenekleri:
            donem_secenekleri = ["Eylül 2026 — Onaylanan Tutar: 0,00 TL"]

        if "muh_secilen_donem_str" not in st.session_state:
            st.session_state["muh_secilen_donem_str"] = donem_secenekleri[0]

        secilen_donem_str = st.selectbox("Dönem ve Onaylanan Tutarlar *", options=donem_secenekleri, key="muh_secilen_donem_str")
        
        secilen_donem_adi = secilen_donem_str.split(" — ")[0]
        secilen_item = next((item for item in gecmis_liste if item.get("DÖNEM") == secilen_donem_adi), None)
        varsayilan_onaylanan_tutar = float(secilen_item.get("ONAYLANAN TUTAR", 0.0) or 0.0) if secilen_item else 0.0
        
        farkli_tutar_var_mi = st.checkbox("Gelen tutar onaylanan tutardan farklı mı?", key="muh_farkli_tutar_check")
        
        with st.form("muhasebe_odeme_form", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                muh_musteri = st.text_input("Müşteri Adı *", value="Legrand", key="muh_musteri_adi")
                muh_durum_tipi = st.selectbox("Ödeme Durumu", options=["Gelen Ödeme", "Bekleyen Ödeme"], key="muh_durum_tipi")
                muh_para_birimi = st.selectbox("Para Birimi", options=["TL (₺)", "USD ($)", "EUR (€)"], key="muh_pb")
                
            with col_m2:
                if farkli_tutar_var_mi:
                    muh_tutar = st.number_input("Gerçekleşen / Gelen Özel Tutar *", min_value=0.0, value=float(varsayilan_onaylanan_tutar), step=100.0, format="%.2f", key="muh_ozel_tutar")
                else:
                    muh_tutar = float(varsayilan_onaylanan_tutar)
                    
                muh_kur = st.number_input("TCMB Kur / Çevrim Çarpanı", min_value=0.0001, value=1.0 if "TL" in muh_para_birimi else 35.0, step=0.01, format="%.4f", key="muh_kur_val")
            
            muh_aciklama = st.text_area("Açıklama / Notlar", placeholder="Notlar...", key="muh_aciklama_val")
            
            btn_odeme_kaydet = st.form_submit_button("💾 Ödeme / Tahsilat Kaydet", use_container_width=True, type="primary")
            
            if btn_odeme_kaydet:
                if not muh_musteri.strip() or muh_tutar < 0:
                    st.error("Lütfen geçerli bir Müşteri Adı ve Tutar giriniz!")
                else:
                    mevcut_odemeler = st.session_state["odeme_kayitlari"]
                    yeni_odeme_id = max([item.get("ID", 0) for item in mevcut_odemeler]) + 1 if mevcut_odemeler else 1

                    yeni_kayit_dict = {
                        "ID": yeni_odeme_id,
                        "MÜŞTERİ ADI": muh_musteri.strip(),
                        "ÖDEME DURUMU": muh_durum_tipi,
                        "PARA BİRİMİ": muh_para_birimi,
                        "TCBM KUR": muh_kur,
                        "AÇIKLAMA NOTLAR": muh_aciklama.strip() if muh_aciklama.strip() else f"{secilen_donem_adi} dönemi tahsilatı.",
                        "GERÇEKLEŞEN GELEN ÖZEL TUTAR": muh_tutar
                    }
                    
                    mevcut_odemeler.append(yeni_kayit_dict)
                    if update_odeme_google_sheet(mevcut_odemeler):
                        st.session_state["odeme_kayitlari"] = mevcut_odemeler
                        st.success("Ödeme kaydı sisteme ve Google Sheets'e başarıyla işlendi!")
                        st.rerun()
    else:
        st.subheader("📊 Kayıt Listesi (Salt Okunur)")
        st.dataframe(df, use_container_width=True)

# ---------------- TAB 2: YÖNETİM ----------------
with tab2:
    df = load_data()
    if user["role"] == "admin":
        st.subheader("📊 Kayıt Yönetimi (Düzenle & Sil)")
        if df.empty or df.dropna(how='all').empty:
            st.info("Henüz kayıtlı veri bulunmuyor.")
        else:
            if "Seç" not in df.columns:
                df.insert(0, "Seç", False)
            
            edited_df = st.data_editor(
                df,
                column_config={
                    "Seç": st.column_config.CheckboxColumn("Seç", default=False),
                    "ID": st.column_config.NumberColumn("ID", disabled=True),
                    "Kayıp Zaman Türü": st.column_config.SelectboxColumn("Kayıp Zaman Türü", options=KAYIP_ZAMAN_TURU_OPSIYONLARI, required=True),
                    "Dönem (Ay/Yıl)": st.column_config.SelectboxColumn("Dönem (Ay/Yıl)", options=DONEM_LISTESI, required=True),
                    "Hata Oranı (%)": st.column_config.NumberColumn("Hata Oranı (%)", min_value=0.0, max_value=100.0, format="%.2f"),
                    "Hesaplanan Zaman (Saat)": st.column_config.NumberColumn("Hesaplanan Zaman (Saat)", format="%.2f"),
                    "Kayıp Zaman (Saat)": st.column_config.NumberColumn("Kayıp Zaman (Saat)", format="%.2f"),
                    "Saatlik İşçilik Ücreti (TL)": st.column_config.NumberColumn("Saatlik Ücret (TL)", format="%.2f"),
                    "Toplam Tutar (TL)": st.column_config.NumberColumn("Toplam Tutar (TL)", format="%.2f"),
                    "Son Durum": st.column_config.SelectboxColumn("Son Durum", options=["Mail Atıldı", "Onay Geldi", "Red Oldu", "Revize İstendi"], required=True),
                    "Duruş Nedeni": st.column_config.SelectboxColumn("Duruş Nedeni", options=DURUS_NEDENLERI, required=True),
                },
                use_container_width=True,
                key="editor"
            )
            
            c_kaydet, c_secili_sil, c_indir = st.columns([1.2, 1.2, 1])
            with c_kaydet:
                if st.button("🔄 Tablo Değişikliklerini Google Sheets'e Kaydet", use_container_width=True):
                    clean_df = edited_df.drop(columns=["Seç"], errors="ignore")
                    if update_google_sheet(clean_df):
                        st.success("Tablo değişiklikleri başarıyla Google Sheets'e kaydedildi!")
                        st.rerun()
            with c_secili_sil:
                if st.button("🗑️ İşaretlenen Kayıtları Sil", use_container_width=True, type="primary"):
                    secilenler = edited_df[edited_df["Seç"] == True]
                    if secilenler.empty:
                        st.warning("Lütfen silmek istediğiniz satırın solundaki 'Seç' kutucuğunu işaretleyin!")
                    else:
                        kalan_df = edited_df[edited_df["Seç"] == False].drop(columns=["Seç"], errors="ignore")
                        if update_google_sheet(kalan_df):
                            st.success(f"Seçilen {len(secilenler)} adet kayıt Google Sheets'ten silindi!")
                            st.rerun()
            with c_indir:
                download_df = df.drop(columns=["Seç"], errors="ignore")
                csv_data = download_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 CSV İndir", data=csv_data, file_name="kayip_zaman.csv", mime="text/csv", use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 🔍 ID ile Doğrudan Hızlı Silme")
            col_id1, col_id2 = st.columns([2, 1])
            with col_id1:
                silinecek_id_input = st.number_input("Silmek İstediğiniz Kaydın ID Numarası", min_value=1, step=1, key="tekli_sil_id_input")
            with col_id2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("❌ Bu ID'ye Sahip Kaydı Sil", type="primary", use_container_width=True):
                    mevcut_df_id = load_data()
                    if 'ID' in mevcut_df_id.columns and silinecek_id_input in mevcut_df_id['ID'].values:
                        yeni_temiz_df = mevcut_df_id[mevcut_df_id['ID'] != silinecek_id_input]
                        if update_google_sheet(yeni_temiz_df):
                            st.success(f"ID #{silinecek_id_input} numaralı kayıt başarıyla silindi!")
                            st.rerun()
                    else:
                        st.error(f"Sistemde #{silinecek_id_input} ID numarasına ait kayıt bulunamadı.")
    else:
        st.subheader("📊 Kayıt Listesi")
        st.dataframe(df, use_container_width=True)

# ---------------- TAB 3: ANALİZ, GRAFİK & ÖDEMELER ----------------
with tab3:
    st.subheader("📈 Analitik Grafikler & Ödemeler")
    df = load_data()
    
    manuel_df = pd.DataFrame(st.session_state["gecmis_ozetler"])
    for col in GECMIS_SUTUNLAR:
        if col not in manuel_df.columns:
            manuel_df[col] = 0.0 if "SAAT" in col or "TUTAR" in col or "ÜCRET" in col else ""

    odeme_analiz_df = pd.DataFrame(st.session_state["odeme_kayitlari"])
    for col in ODEME_SUTUNLAR:
        if col not in odeme_analiz_df.columns:
            odeme_analiz_df[col] = 0.0 if "TUTAR" in col or "KUR" in col else ""
    
    aktif_talep = pd.to_numeric(df['Hesaplanan Zaman (Saat)'], errors='coerce').sum() if not df.empty and 'Hesaplanan Zaman (Saat)' in df.columns else 0.0
    aktif_onay = pd.to_numeric(df.loc[df['Son Durum'] == 'Onay Geldi', 'Hesaplanan Zaman (Saat)'], errors='coerce').sum() if not df.empty and 'Hesaplanan Zaman (Saat)' in df.columns else 0.0
    
    m_talep = pd.to_numeric(manuel_df['TALEP EDİLEN SAAT'], errors='coerce').sum() if not manuel_df.empty else 0.0
    m_onay = pd.to_numeric(manuel_df['ONAYLANAN SAAT'], errors='coerce').sum() if not manuel_df.empty else 0.0
    
    st.markdown("### 🌐 Kümülatif Zaman Özeti")
    tz1, tz2 = st.columns(2)
    tz1.metric("Toplam Talep Edilen Kayıp Zaman", f"{aktif_talep + m_talep:.2f} Saat")
    tz2.metric("Toplam Onaylanan Kayıp Zaman", f"{aktif_onay + m_onay:.2f} Saat")
    
    st.markdown("### 💼 Geçmiş Dönem Finansal & Kesinti Özeti")
    m_talep_tutar = pd.to_numeric(manuel_df['TALEP EDİLEN TUTAR'], errors='coerce').sum() if not manuel_df.empty else 0.0
    m_onay_tutar = pd.to_numeric(manuel_df['ONAYLANAN TUTAR'], errors='coerce').sum() if not manuel_df.empty else 0.0
    m_kesinti_tutar = pd.to_numeric(manuel_df['KESİNTİ TUTARI'], errors='coerce').sum() if not manuel_df.empty else 0.0
    
    ft1, ft2, ft3 = st.columns(3)
    ft1.metric("Geçmiş Toplam Talep Edilen Tutar", f"{m_talep_tutar:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
    ft2.metric("Geçmiş Toplam Onaylanan Tutar", f"{m_onay_tutar:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
    ft3.metric("Geçmiş Toplam Kesinti Tutarı", f"{m_kesinti_tutar:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
    
    st.markdown("---")
    st.markdown("### 💰 Finansal Ödeme Analizi")
    
    if not odeme_analiz_df.empty:
        if "ÖDEME DURUMU" not in odeme_analiz_df.columns:
            odeme_analiz_df["ÖDEME DURUMU"] = "Gelen Ödeme"
            
        def hesapla_tl_karsilik(row):
            tutar = float(row.get("GERÇEKLEŞEN GELEN ÖZEL TUTAR", 0.0) or 0.0)
            kur = float(row.get("TCBM KUR", 1.0) or 1.0)
            pb = str(row.get("PARA BİRİMİ", "TL"))
            return tutar if "TL" in pb else tutar * kur

        odeme_analiz_df["TL_Karsiligi"] = odeme_analiz_df.apply(hesapla_tl_karsilik, axis=1)
        
        gelen_toplam = odeme_analiz_df[odeme_analiz_df["ÖDEME DURUMU"] == "Gelen Ödeme"]["TL_Karsiligi"].sum()
        bekleyen_toplam = odeme_analiz_df[odeme_analiz_df["ÖDEME DURUMU"] == "Bekleyen Ödeme"]["TL_Karsiligi"].sum()
        tum_toplam = odeme_analiz_df["TL_Karsiligi"].sum()
        
        od_col1, od_col2, od_col3 = st.columns(3)
        od_col1.metric("📥 Gelen Ödemeler", f"{gelen_toplam:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
        od_col2.metric("⏳ Bekleyen Ödemeler", f"{bekleyen_toplam:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
        od_col3.metric("📊 Kümülatif Toplam", f"{tum_toplam:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
        
        st.dataframe(odeme_analiz_df.drop(columns=["TL_Karsiligi"], errors="ignore"), use_container_width=True)
    else:
        st.info("Kayıtlı finansal ödeme verisi bulunmuyor.")

    st.markdown("---")
    st.markdown("### 📊 Görsel Dağılım Grafikleri")
    if not df.empty and not df.dropna(how='all').empty:
        cg1, cg2 = st.columns(2)
        with cg1:
            g_mus = df.groupby('Müşteri Adı')['Hesaplanan Zaman (Saat)'].sum().reset_index()
            fig_m = px.bar(g_mus, x='Müşteri Adı', y='Hesaplanan Zaman (Saat)', title="Müşteri Bazlı Toplam Zaman")
            st.plotly_chart(fig_m, use_container_width=True)
        with cg2:
            g_ned = df.groupby('Duruş Nedeni')['Hesaplanan Zaman (Saat)'].sum().reset_index()
            fig_n = px.bar(g_ned, x='Duruş Nedeni', y='Hesaplanan Zaman (Saat)', title="Duruş Nedenleri Dağılımı")
            st.plotly_chart(fig_n, use_container_width=True)
            
        fig_trend = px.line(df, x='Dönem (Ay/Yıl)', y='Hesaplanan Zaman (Saat)', color='Müşteri Adı', markers=True, title="Dönemsel Zaman Trend Analizi")
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Grafik oluşturulabilmesi için yeterli aktif sistem verisi bulunmuyor.")

# ---------------- TAB 4: GEÇMİŞ DÖNEM ----------------
with tab4:
    st.subheader("📁 Geçmiş Dönem Manuel Özet Veriler (`gecmisdonem`)")
    gecmis_temp_df = pd.DataFrame(st.session_state["gecmis_ozetler"])
    for col in GECMIS_SUTUNLAR:
        if col not in gecmis_temp_df.columns:
            gecmis_temp_df[col] = 0.0 if "SAAT" in col or "TUTAR" in col or "ÜCRET" in col else ""
            
    gecmis_df_editable = st.data_editor(
        gecmis_temp_df,
        column_config={
            "ID": st.column_config.NumberColumn("ID", disabled=True),
            "DÖNEM": st.column_config.TextColumn("DÖNEM", disabled=True),
            "TALEP EDİLEN SAAT": st.column_config.NumberColumn("TALEP EDİLEN SAAT", format="%.2f"),
            "ONAYLANAN SAAT": st.column_config.NumberColumn("ONAYLANAN SAAT", format="%.2f"),
            "SAATLİK ÜCRET": st.column_config.NumberColumn("SAATLİK ÜCRET", format="%.2f"),
            "TALEP EDİLEN TUTAR": st.column_config.NumberColumn("TALEP EDİLEN TUTAR", format="%.2f"),
            "ONAYLANAN TUTAR": st.column_config.NumberColumn("ONAYLANAN TUTAR", format="%.2f"),
            "KESİNTİ TUTARI": st.column_config.NumberColumn("KESİNTİ TUTARI", format="%.2f"),
            "KESİNTİ AÇIKLAMASI": st.column_config.TextColumn("KESİNTİ AÇIKLAMASI"),
            "GENEL AÇIKLAMA": st.column_config.TextColumn("GENEL AÇIKLAMA")
        },
        use_container_width=True,
        key="gecmis_editor_final"
    )
    
    if st.button("🔄 Saatleri Saatlik Ücretle Çarp & Sheets'e Kaydet", use_container_width=True, type="primary"):
        updated_records = []
        for index, row in gecmis_df_editable.iterrows():
            t_saat = float(row.get("TALEP EDİLEN SAAT", 0.0) or 0.0)
            o_saat = float(row.get("ONAYLANAN SAAT", 0.0) or 0.0)
            s_ucret = float(row.get("SAATLİK ÜCRET", 0.0) or 0.0)
            
            row["TALEP EDİLEN TUTAR"] = round(t_saat * s_ucret, 2)
            row["ONAYLANAN TUTAR"] = round(o_saat * s_ucret, 2)
            updated_records.append(row.to_dict())
            
        if update_gecmis_google_sheet(updated_records):
            st.session_state["gecmis_ozetler"] = updated_records
            st.success("Geçmiş dönem verileriniz başarıyla Google Sheets'e kaydedildi!")
            st.rerun()

# ---------------- TAB 5: SOHBET ----------------
with tab5:
    st.subheader("💬 Canlı İletişim & Soru-Cevap Paneli")
    chat_container = st.container(height=400)
    with chat_container:
        if not st.session_state["chat_messages"]:
            st.info("Henüz mesaj yok.")
        else:
            for m in st.session_state["chat_messages"]:
                dosya_html = f"<br>📎 <a href='{m['dosya_linki']}' target='_blank'>Dosyayı Aç</a>" if m.get("dosya_linki") else ""
                st.markdown(f"**{m['gonderen']}** ({m['zaman']}): {m['mesaj']} {dosya_html}", unsafe_allow_html=True)
                
    with st.form("chat_form", clear_on_submit=True):
        yeni_mesaj = st.text_area("Mesajınızı yazın...")
        dosya_input_link = st.text_input("📎 Dosya / Belge Linki (Opsiyonel)")
        if st.form_submit_button("Gönder", use_container_width=True):
            if yeni_mesaj or dosya_input_link:
                st.session_state["chat_messages"].append({
                    "zaman": datetime.now().strftime("%d.%m.%Y %H:%M"),
                    "gonderen": user["name"],
                    "mesaj": yeni_mesaj or "Belge paylaşıldı.",
                    "dosya_linki": dosya_input_link
                })
                st.rerun()

    if user["role"] == "admin":
        if st.button("🗑️ Sohbeti Temizle", type="primary"):
            st.session_state["chat_messages"] = []
            st.rerun()

# ---------------- TAB 6: ÖDEMELER ----------------
with tab6:
    st.subheader("💰 Müşteri Ödemeleri & Tahsilat Takip Panosu (`odeme-tahsilat-takip`)")
    yetkili_mi = (user["role"] == "admin" or user["role"] == "accounting")
    
    odeme_df = pd.DataFrame(st.session_state["odeme_kayitlari"])
    for col in ODEME_SUTUNLAR:
        if col not in odeme_df.columns:
            odeme_df[col] = ""

    if odeme_df.empty:
        st.info("Henüz ödeme kaydı bulunmuyor.")
    else:
        if yetkili_mi:
            if "Seç" not in odeme_df.columns:
                odeme_df.insert(0, "Seç", False)
            
            edited_odeme_df = st.data_editor(
                odeme_df,
                column_config={
                    "Seç": st.column_config.CheckboxColumn("Seç", default=False),
                    "ID": st.column_config.NumberColumn("ID", disabled=True),
                },
                use_container_width=True,
                key="odeme_editor_yonetim"
            )
            
            if st.button("🔄 Ödeme Tablosu Değişikliklerini Google Sheets'e Kaydet", use_container_width=True):
                clean_odeme_df = edited_odeme_df.drop(columns=["Seç"], errors="ignore")
                liste_kayitlari = clean_odeme_df.to_dict(orient="records")
                if update_odeme_google_sheet(liste_kayitlari):
                    st.session_state["odeme_kayitlari"] = liste_kayitlari
                    st.success("Ödeme tablosu güncellemeleri Google Sheets'e kaydedildi!")
                    st.rerun()
        else:
            st.dataframe(odeme_df, use_container_width=True)
        
    if yetkili_mi:
        st.markdown("---")
        st.markdown("### ⚙️ Ödeme Kayıtları Silme / Yönetimi")
        
        col_odm_1, col_odm_2 = st.columns(2)
        with col_odm_1:
            if st.button("🗑️ İşaretlenen Ödemeleri Sil", use_container_width=True, type="primary"):
                secilen_odemeler = edited_odeme_df[edited_odeme_df["Seç"] == True]
                if secilen_odemeler.empty:
                    st.warning("Lütfen silmek istediğiniz ödeme satırının solundaki 'Seç' kutucuğunu işaretleyin!")
                else:
                    kalan_odemeler_df = edited_odeme_df[edited_odeme_df["Seç"] == False].drop(columns=["Seç"], errors="ignore")
                    yeni_liste = kalan_odemeler_df.to_dict(orient="records")
                    if update_odeme_google_sheet(yeni_liste):
                        st.session_state["odeme_kayitlari"] = yeni_liste
                        st.success("Seçilen ödeme kayıtları silindi!")
                        st.rerun()
                    
        with col_odm_2:
            if st.button("⚠️ Tüm Ödeme Kayıtlarını Temizle", type="secondary", use_container_width=True):
                if update_odeme_google_sheet([]):
                    st.session_state["odeme_kayitlari"] = []
                    st.success("Tüm ödeme kayıtları temizlendi!")
                    st.rerun()
                
        st.markdown("---")
        st.markdown("### 🔍 ID ile Hızlı Ödeme Silme")
        col_oid1, col_oid2 = st.columns([2, 1])
        with col_oid1:
            silinecek_odeme_id = st.number_input("Silmek İstediğiniz Ödeme ID Numarası", min_value=1, step=1, key="tekli_odeme_sil_id")
        with col_oid2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("❌ Bu ID'ye Sahip Ödemeyi Sil", type="primary", use_container_width=True):
                mevcut_odemeler = st.session_state["odeme_kayitlari"]
                yeni_odemeler = [item for item in mevcut_odemeler if item.get("ID") != silinecek_odeme_id]
                if len(yeni_odemeler) < len(mevcut_odemeler):
                    if update_odeme_google_sheet(yeni_odemeler):
                        st.session_state["odeme_kayitlari"] = yeni_odemeler
                        st.success(f"ID #{silinecek_odeme_id} numaralı ödeme kaydı silindi!")
                        st.rerun()
                else:
                    st.error(f"Sistemde #{silinecek_odeme_id} ID numarasına ait ödeme kaydı bulunamadı.")
    else:
        st.info("ℹ️ Ödeme kayıtlarını silme yetkisi yalnızca yetkili kullanıcılara özeldir.")
