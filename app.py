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

SUTUNLAR = [
    "ID", "Tarih", "Kayıp Zaman Türü", "Dönem (Ay/Yıl)", "Müşteri Adı", "Sorumlu Mühendis", "İrsaliye No", 
    "Referans No", "Seri No", "Duruş Nedeni", "İşlem Açıklaması", 
    "Gelen Parti Miktarı", "Hata Oranı (%)", "P/H", 
    "Hesaplanan Zaman (Saat)", "Kayıp Zaman (Saat)", "Son Durum", 
    "İrsaliye Görseli Linki", "Etiket Görseli Linki", "Hata Görseli Linki", "Onay Belgesi Linki"
]

DURUM_OPSIYONLARI = ["Mail Atıldı", "Onay Geldi", "Red Oldu", "Revize İstendi"]
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

@st.cache_data(ttl=600, show_spinner="Google Sheets'ten veriler yükleniyor...")
def load_data_cached():
    return _fetch_data_from_sheet()

def _fetch_data_from_sheet():
    try:
        client = get_gspread_client()
        if client:
            spreadsheet = client.open_by_url(SHEET_URL)
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
        
        for num_col in ['Kayıp Zaman (Saat)', 'Hesaplanan Zaman (Saat)', 'Hata Oranı (%)', 'P/H']:
            if num_col in df.columns:
                s = df[num_col].astype(str).str.strip().str.replace(',', '', regex=False).str.replace('.', '', regex=False)
                numeric_vals = pd.to_numeric(s, errors='coerce').fillna(0.0) / 100.0
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
        worksheet = spreadsheet.get_worksheet(0)
        
        df_to_write = df.copy()
        for col in ['Hesaplanan Zaman (Saat)', 'Kayıp Zaman (Saat)', 'Hata Oranı (%)', 'P/H']:
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

# --- KULLANICI / YETKİLENDİRME VERİ TABANI ---
if "users" not in st.session_state:
    st.session_state["users"] = {
        "omer.ocak": {
            "password": "OCK6161",
            "name": "Ömer OCAK",
            "role": "admin",
            "group": "Yönetim Kadrosu"
        },
        "mehmet.alasar": {
            "password": "malasar34.",
            "name": "Mehmet ALAŞAR",
            "role": "viewer",
            "group": "Yönetim Kadrosu"
        },
        "dilber.alasar": {
            "password": "dalasar34.",
            "name": "Dilber ALAŞAR",
            "role": "viewer",
            "group": "Yönetim Kadrosu"
        },
        "hakan.alasar": {
            "password": "halasar34.",
            "name": "Hakan ALAŞAR",
            "role": "viewer",
            "group": "Yönetim Kadrosu"
        },
        "uretim": {
            "password": "uretim34.",
            "name": "Üretim Birimi",
            "role": "user",
            "group": "Kullanıcı"
        },
        "muhasebe": {
            "password": "mhalasar34.",
            "name": "Muhasebe Birimi",
            "role": "accounting",
            "group": "Kullanıcı"
        },
        "turgay.yigit": {
            "password": "talasar34.",
            "name": "Turgay YİĞİT",
            "role": "user",
            "group": "Kullanıcı"
        }
    }

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

# --- ORTAK CHAT / MESAJLAŞMA HAFIZASI ---
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = [
        {"zaman": "19.09.2026 10:30", "gonderen": "Mehmet ALAŞAR", "mesaj": "Ömer Bey, eylül ayı raporunu kontrol edebilir misiniz?", "dosya_linki": ""},
        {"zaman": "19.09.2026 10:35", "gonderen": "Ömer OCAK", "mesaj": "Tabii ki Mehmet Bey, hemen inceliyorum.", "dosya_linki": ""}
    ]

# --- ORTAK MUHASEBE ÖDEME / TAHSİLAT HAFIZASI (GEÇMİŞTEN GELENLER DAHİL) ---
if "odeme_kayitlari" not in st.session_state:
    st.session_state["odeme_kayitlari"] = [
        {
            "İşlem Tarihi": "15.02.2026",
            "Dönem": "Şubat 2026",
            "Müşteri Adı": "Legrand (Geçmiş Devir)",
            "Tutar": 120000.00,
            "Para Birimi": "TL (₺)",
            "Kur": 1.0,
            "TL Karşılığı": 120000.00,
            "Gösterim": "120.000,00 TL (₺)",
            "Açıklama": "Şubat dönemi geçmiş devir ödemesi.",
            "Kaydeden": "Ömer OCAK",
            "Durum": "Gelen Ödeme"
        },
        {
            "İşlem Tarihi": "19.09.2026",
            "Dönem": "Eylül 2026",
            "Müşteri Adı": "Legrand",
            "Tutar": 155252.00,
            "Para Birimi": "TL (₺)",
            "Kur": 1.0,
            "TL Karşılığı": 155252.00,
            "Gösterim": "155.252,00 TL (₺)",
            "Açıklama": "Eylül ayı fatura tahsilatı alındı.",
            "Kaydeden": "Muhasebe Birimi",
            "Durum": "Gelen Ödeme"
        }
    ]

# --- GEÇMİŞ 7 AY MANUEL ÖZET VERİLERİ ---
if "gecmis_ozetler" not in st.session_state:
    st.session_state["gecmis_ozetler"] = [
        {"Dönem": "Şubat 2026", "Talep Edilen Kayıp Zaman (Saat)": 0.0, "Onaylanan Kayıp Zaman (Saat)": 0.0, "Açıklama": "Süreç başlangıcı"},
        {"Dönem": "Mart 2026", "Talep Edilen Kayıp Zaman (Saat)": 0.0, "Onaylanan Kayıp Zaman (Saat)": 0.0, "Açıklama": "Veri bekleniyor"},
        {"Dönem": "Nisan 2026", "Talep Edilen Kayıp Zaman (Saat)": 0.0, "Onaylanan Kayıp Zaman (Saat)": 0.0, "Açıklama": "Veri bekleniyor"},
        {"Dönem": "Mayıs 2026", "Talep Edilen Kayıp Zaman (Saat)": 0.0, "Onaylanan Kayıp Zaman (Saat)": 0.0, "Açıklama": "Veri bekleniyor"},
        {"Dönem": "Haziran 2026", "Talep Edilen Kayıp Zaman (Saat)": 0.0, "Onaylanan Kayıp Zaman (Saat)": 0.0, "Açıklama": "Veri bekleniyor"},
        {"Dönem": "Temmuz 2026", "Talep Edilen Kayıp Zaman (Saat)": 0.0, "Onaylanan Kayıp Zaman (Saat)": 0.0, "Açıklama": "Veri bekleniyor"},
        {"Dönem": "Ağustos 2026", "Talep Edilen Kayıp Zaman (Saat)": 0.0, "Onaylanan Kayıp Zaman (Saat)": 0.0, "Açıklama": "Veri bekleniyor"}
    ]

def format_para(tutar, birim):
    try:
        tutar_val = float(tutar)
        formatted = f"{tutar_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} {birim}"
    except:
        return f"{tutar} {birim}"

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
            son_durum = st.selectbox("Son Durum *", DURUM_OPSIYONLARI, key="f_durum")

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
                    "Son Durum": son_durum,
                    "İrsaliye Görseli Linki": irsaliye_gorseli_link,
                    "Etiket Görseli Linki": etiket_gorseli_link,
                    "Hata Görseli Linki": hata_gorseli_link,
                    "Onay Belgesi Linki": onay_belgesi_link
                }])
                
                guncel_df = pd.concat([mevcut_df, yeni_kayit], ignore_index=True)
                if update_google_sheet(guncel_df):
                    st.success(f"ID #{yeni_id} ({secilen_donem_form} - {musteri_adi}) başarıyla kaydedildi!")
                    st.rerun()

    elif user["role"] == "accounting":
        st.subheader("💰 Müşteri Ödemesi / Tahsilat Girişi (Geçmiş veya Güncel Dönem)")
        with st.form("muhasebe_odeme_form", clear_on_submit=True):
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                muh_donem = st.selectbox("Dönem Seçin (Ay / Yıl) *", options=DONEM_LISTESI, index=0, key="muh_donem_sec")
                muh_musteri = st.text_input("Müşteri Adı *", placeholder="Örn: Legrand", key="muh_musteri_adi")
            with col_m2:
                muh_tutar = st.number_input("Tutar *", min_value=0.0, value=155252.00, step=100.0, format="%.2f", key="muh_tutar_val")
                muh_para_birimi = st.selectbox("Para Birimi", options=["TL (₺)", "USD ($)", "EUR (€)"], key="muh_pb")
            with col_m3:
                muh_kur = st.number_input("TCMB Kur / Çevrim Çarpanı", min_value=0.0001, value=1.0 if "TL" in muh_para_birimi else 35.0, step=0.01, format="%.4f", key="muh_kur_val")
                muh_tarih = st.text_input("Ödeme / İşlem Tarihi", value=datetime.now().strftime("%d.%m.%Y"), key="muh_tarih_val")
                
            muh_durum_tipi = st.selectbox("Ödeme Durumu", options=["Gelen Ödeme", "Bekleyen Ödeme"], key="muh_durum_tipi")
            hesaplanan_tl = muh_tutar if "TL" in muh_para_birimi else muh_tutar * muh_kur
            
            muh_aciklama = st.text_area("Açıklama / Notlar", placeholder="Geçmiş dönem devri veya fatura no...", key="muh_aciklama_val")
            btn_odeme_kaydet = st.form_submit_button("💾 Ödeme / Tahsilat Kaydet", use_container_width=True, type="primary")
            
            if btn_odeme_kaydet:
                if not muh_musteri.strip() or muh_tutar <= 0:
                    st.error("Lütfen geçerli bir Müşteri Adı ve Tutar giriniz!")
                else:
                    gosterim_str = format_para(muh_tutar, muh_para_birimi)
                    st.session_state["odeme_kayitlari"].insert(0, {
                        "İşlem Tarihi": muh_tarih,
                        "Dönem": muh_donem,
                        "Müşteri Adı": muh_musteri.strip(),
                        "Tutar": muh_tutar,
                        "Para Birimi": muh_para_birimi,
                        "Kur": muh_kur,
                        "TL Karşılığı": hesaplanan_tl,
                        "Gösterim": gosterim_str,
                        "Açıklama": muh_aciklama.strip() if muh_aciklama.strip() else "Açıklama yok.",
                        "Kaydeden": user["name"],
                        "Durum": muh_durum_tipi
                    })
                    st.success("Ödeme kaydı sisteme başarıyla işlendi ve otomatik güncellendi!")
                    st.rerun()
    else:
        st.subheader("📊 Kayıt Listesi (Salt Okunur)")
        st.dataframe(df, use_container_width=True)

# ---------------- TAB 2: YÖNETİM ----------------
with tab2:
    df = load_data()
    if user["role"] == "admin":
        st.subheader("📊 Kayıt Yönetimi (Düzenle & Toplu/Tekli Sil)")
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
                    "Son Durum": st.column_config.SelectboxColumn("Son Durum", options=DURUM_OPSIYONLARI, required=True),
                    "Duruş Nedeni": st.column_config.SelectboxColumn("Duruş Nedeni", options=DURUS_NEDENLERI, required=True),
                },
                use_container_width=True,
                key="editor"
            )
            
            c_kaydet, c_toplu_sil, c_indir = st.columns([1.2, 1.2, 1])
            with c_kaydet:
                if st.button("🔄 Tablo Değişikliklerini Kaydet", use_container_width=True):
                    clean_df = edited_df.drop(columns=["Seç"], errors="ignore")
                    if update_google_sheet(clean_df):
                        st.success("Tablo değişiklikleri kaydedildi!")
                        st.rerun()
            with c_toplu_sil:
                if st.button("🔴 Seçili Kayıtları Toplu Sil", use_container_width=True, type="primary"):
                    secilenler = edited_df[edited_df["Seç"] == True]
                    if secilenler.empty:
                        st.warning("Seçim yapmadınız!")
                    else:
                        kalan_df = edited_df[edited_df["Seç"] == False].drop(columns=["Seç"], errors="ignore")
                        if update_google_sheet(kalan_df):
                            st.success("Seçilen kayıtlar silindi!")
                            st.rerun()
            with c_indir:
                download_df = df.drop(columns=["Seç"], errors="ignore")
                csv_data = download_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 CSV İndir", data=csv_data, file_name="kayip_zaman.csv", mime="text/csv", use_container_width=True)
    else:
        st.subheader("📊 Kayıt Listesi")
        st.dataframe(df, use_container_width=True)

# ---------------- TAB 3: ANALİZ, GRAFİK & ÖDEMELER ----------------
with tab3:
    st.subheader("📈 Gelişmiş Analitik Grafikler & Ödeme Durumları")
    df = load_data()
    manuel_df = pd.DataFrame(st.session_state["gecmis_ozetler"])
    odeme_analiz_df = pd.DataFrame(st.session_state["odeme_kayitlari"])
    
    aktif_talep = pd.to_numeric(df['Hesaplanan Zaman (Saat)'], errors='coerce').sum() if not df.empty else 0.0
    aktif_onay = pd.to_numeric(df.loc[df['Son Durum'] == 'Onay Geldi', 'Hesaplanan Zaman (Saat)'], errors='coerce').sum() if not df.empty else 0.0
    
    m_talep = pd.to_numeric(manuel_df['Talep Edilen Kayıp Zaman (Saat)'], errors='coerce').sum()
    m_onay = pd.to_numeric(manuel_df['Onaylanan Kayıp Zaman (Saat)'], errors='coerce').sum()
    
    st.markdown("### 🌐 Kümülatif Zaman Özeti")
    tz1, tz2 = st.columns(2)
    tz1.metric("Toplam Talep Edilen Kayıp Zaman", f"{aktif_talep + m_talep:.2f} Saat")
    tz2.metric("Toplam Onaylanan Kayıp Zaman", f"{aktif_onay + m_onay:.2f} Saat")
    
    st.markdown("---")
    st.markdown("### 💰 Finansal Ödeme Analizi (Geçmiş Devirler Dahil Otomatik Güncellenen)")
    
    if not odeme_analiz_df.empty:
        if "Durum" not in odeme_analiz_df.columns:
            odeme_analiz_df["Durum"] = "Gelen Ödeme"
            
        gelen_toplam = odeme_analiz_df[odeme_analiz_df["Durum"] == "Gelen Ödeme"]["TL Karşılığı"].sum()
        bekleyen_toplam = odeme_analiz_df[odeme_analiz_df["Durum"] == "Bekleyen Ödeme"]["TL Karşılığı"].sum()
        tum_toplam = odeme_analiz_df["TL Karşılığı"].sum()
        
        od_col1, od_col2, od_col3 = st.columns(3)
        od_col1.metric("📥 Gelen Ödemeler Toplamı", f"{gelen_toplam:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
        od_col2.metric("⏳ Bekleyen Ödemeler Toplamı", f"{bekleyen_toplam:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
        od_col3.metric("📊 Tüm Ödemeler Kümülatif", f"{tum_toplam:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."))
        
        odeme_filtre_secim = st.radio(
            "Görüntülenecek Ödeme Kategorisi:",
            ["Tüm Ödemeler", "Gelen Ödemeler", "Bekleyen Ödemeler"],
            horizontal=True
        )
        
        if odeme_filtre_secim == "Gelen Ödemeler":
            gosterilecek_odeme_df = odeme_analiz_df[odeme_analiz_df["Durum"] == "Gelen Ödeme"]
        elif odeme_filtre_secim == "Bekleyen Ödemeler":
            gosterilecek_odeme_df = odeme_analiz_df[odeme_analiz_df["Durum"] == "Bekleyen Ödeme"]
        else:
            gosterilecek_odeme_df = odeme_analiz_df
            
        st.dataframe(gosterilecek_odeme_df, use_container_width=True)
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
    st.subheader("📁 Geçmiş 7 Ay Manuel Özet Veri Yönetimi")
    gecmis_df_editable = st.data_editor(
        pd.DataFrame(st.session_state["gecmis_ozetler"]),
        column_config={
            "Dönem": st.column_config.TextColumn("Dönem", disabled=True),
            "Talep Edilen Kayıp Zaman (Saat)": st.column_config.NumberColumn("Talep Edilen", format="%.2f"),
            "Onaylanan Kayıp Zaman (Saat)": st.column_config.NumberColumn("Onaylanan", format="%.2f"),
            "Açıklama": st.column_config.TextColumn("Açıklama")
        },
        use_container_width=True,
        key="gecmis_editor_final"
    )
    if st.button("🔄 Geçmiş Dönem Verilerini Kaydet", use_container_width=True, type="primary"):
        st.session_state["gecmis_ozetler"] = gecmis_df_editable.to_dict(orient="records")
        st.success("Geçmiş dönem verileri güncellendi!")
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
    st.subheader("💰 Müşteri Ödemeleri & Tahsilat Takip Panosu (Geçmiş Dönemler Dahil)")
    odeme_df = pd.DataFrame(st.session_state["odeme_kayitlari"])
    if odeme_df.empty:
        st.info("Henüz ödeme kaydı bulunmuyor.")
    else:
        st.dataframe(odeme_df, use_container_width=True)
        
    if user["role"] == "admin":
        if st.button("🗑️ Ödemeleri Temizle", type="primary"):
            st.session_state["odeme_kayitlari"] = []
            st.rerun()
