import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Page Configuration
st.set_page_config(page_title="Müşteri Kayıp Zaman Takip Sistemi", layout="wide", page_icon="⏱️")

# Google Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UsGlWxzRmiriAufzk14D0oiS3CyHMAjENyFhIbw9VG4/edit?pli=1&gid=0#gid=0"

# Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

SUTUNLAR = [
    "ID", "Tarih", "Müşteri Adı", "Sorumlu Mühendis", "İrsaliye No", 
    "Referans No", "Seri No", "Duruş Nedeni", "İşlem Açıklaması", 
    "Miktar", "P/H", "Hesaplanan Zaman (Saat)", "Kayıp Zaman (Saat)", 
    "Son Durum", "Hata Görseli Linki", "Onay Belgesi Linki"
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

# --- KULLANICI / YETKİLENDİRME VERİ TABANI ---
if "users" not in st.session_state:
    st.session_state["users"] = {
        "omer.ocak": {
            "password": "OCK6161",
            "name": "Ömer OCAK",
            "role": "admin"  # Tam yetkili
        },
        "mehmet.alasar": {
            "password": "MHMT3434",
            "name": "Mehmet ALAŞAR",
            "role": "viewer" # Sadece okuma / görüntüleme
        }
    }

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        for col in SUTUNLAR:
            if col not in df.columns:
                df[col] = None
        df = df[SUTUNLAR]
        # ID Sütununu temizle ve tam sayıya çevir
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
        return df
    except Exception:
        return pd.DataFrame(columns=SUTUNLAR)

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

# --- GİRİŞ YAPILDIKTAN SONRA SİDEBAR ---
user = st.session_state["user_info"]
st.sidebar.title(f"👤 {user['name']}")
st.sidebar.caption(f"Rol: {'Yönetici (Tam Yetki)' if user['role'] == 'admin' else 'Görüntüleyici (Okuma Yetkisi)'}")

# Şifre Değiştirme Alanı
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

if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None
    st.rerun()

# --- ANA UYGULAMA ---
st.title("⏱️ Müşteri Kayıp Zaman & Fatura Takip Sistemi")
st.markdown("---")

# Sekme yetkilendirmesi
if user["role"] == "admin":
    tab1, tab2, tab3 = st.tabs(["➕ Yeni Kayıp Zaman Kaydı Ekle", "📊 Kayıt Yönetimi (Düzenle & Sil)", "📈 Analiz & Özet"])
else:
    tab2, tab3 = st.tabs(["📊 Kayıt Listesi (Salt Okunur)", "📈 Analiz & Özet"])

# ---------------- TAB 1: FORM (Yalnızca Admin) ----------------
if user["role"] == "admin":
    with tab1:
        st.subheader("Referans Bazlı Kayıp Zaman Kayıt Formu")
        
        with st.form("kayip_zaman_formu", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                musteri_adi = st.text_input("Müşteri Adı *")
                sorumlu_muhendis = st.text_input("Müşteri Sorumlu Mühendis Adı")
                irsaliye_no = st.text_input("İrsaliye No")
                
            with col2:
                referans_no = st.text_input("Referans No *")
                seri_no = st.text_input("Seri No")
                durus_nedeni = st.selectbox("Duruş / Zaman Kaybı Nedeni *", DURUS_NEDENLERI)
                
            with col3:
                miktar = st.number_input("Miktar (Adet)", min_value=1, value=1, step=1)
                ph = st.number_input("P/H (Parça / Saat)", min_value=0.1, value=100.0, step=1.0)
                kayip_zaman_saat = st.number_input("Kayıp Zaman / Fiili Duruş (Saat) *", min_value=0.0, value=1.0, step=0.1)
                
            c_durum, c_bos = st.columns([1, 2])
            with c_durum:
                son_durum = st.selectbox("Son Durum *", DURUM_OPSIYONLARI)
                
            islem_aciklamasi = st.text_area("İşlem Açıklaması", placeholder="Yapılan işlem, duruş gerekçesi ve detaylar...")
            
            c_link1, c_link2 = st.columns(2)
            with c_link1:
                hata_gorseli_link = st.text_input("Hata Görseli Linki (Google Drive / OneDrive vb.)")
            with c_link2:
                onay_belgesi_link = st.text_input("Gelen Onay Belgesi Linki (Google Drive / OneDrive vb.)")
                
            submit_btn = st.form_submit_button("💾 Kaydı Google Tabloya Kaydet", use_container_width=True)
            
            if submit_btn:
                if not musteri_adi or not referans_no:
                    st.error("Lütfen Müşteri Adı ve Referans No alanlarını doldurunuz!")
                else:
                    mevcut_df = load_data()
                    
                    # Güvenli Otomatik Artan ID Hesabı
                    valid_ids = mevcut_df['ID'].dropna()
                    valid_ids = valid_ids[pd.to_numeric(valid_ids, errors='coerce').notnull()]
                    yeni_id = int(valid_ids.max()) + 1 if not valid_ids.empty else 1
                    
                    hesaplanan_zaman = round(miktar / ph, 2) if ph > 0 else 0.0
                    bugun = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    yeni_kayit = pd.DataFrame([{
                        "ID": yeni_id,
                        "Tarih": bugun,
                        "Müşteri Adı": musteri_adi,
                        "Sorumlu Mühendis": sorumlu_muhendis,
                        "İrsaliye No": irsaliye_no,
                        "Referans No": referans_no,
                        "Seri No": seri_no,
                        "Duruş Nedeni": durus_nedeni,
                        "İşlem Açıklaması": islem_aciklamasi,
                        "Miktar": miktar,
                        "P/H": ph,
                        "Hesaplanan Zaman (Saat)": hesaplanan_zaman,
                        "Kayıp Zaman (Saat)": kayip_zaman_saat,
                        "Son Durum": son_durum,
                        "Hata Görseli Linki": hata_gorseli_link,
                        "Onay Belgesi Linki": onay_belgesi_link
                    }])
                    
                    guncel_df = pd.concat([mevcut_df, yeni_kayit], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, data=guncel_df)
                    st.success(f"ID #{yeni_id} (Referans: {referans_no}) başarıyla kaydedildi!")
                    st.rerun()

# ---------------- TAB 2: GÖRÜNTÜLEME VEYA DÜZENLEME ----------------
with tab2:
    df = load_data()
    
    if user["role"] == "admin":
        st.subheader("📊 Kayıt Listesi, Güncelleme ve Silme İşlemleri")
        
        if df.empty or df.dropna(how='all').empty:
            st.info("Henüz kayıtlı bir veri bulunmuyor.")
        else:
            # 1. HIZLI TABLO DÜZENLEME (Data Editor)
            st.markdown("### 📝 Tablo Üzerinde Doğrudan Düzenleme")
            st.caption("Aşağıdaki tablodan hücrelere çift tıklayarak verileri değiştirebilir, ardından 'Tüm Değişiklikleri Kaydet' butonuna basabilirsiniz.")
            
            edited_df = st.data_editor(
                df,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", disabled=True),
                    "Son Durum": st.column_config.SelectboxColumn("Son Durum", options=DURUM_OPSIYONLARI, required=True),
                    "Duruş Nedeni": st.column_config.SelectboxColumn("Duruş Nedeni", options=DURUS_NEDENLERI, required=True),
                },
                use_container_width=True,
                key="editor"
            )
            
            col_kaydet, col_indir = st.columns([1, 1])
            with col_kaydet:
                if st.button("🔄 Tablodaki Tüm Değişiklikleri Kaydet", use_container_width=True):
                    conn.update(spreadsheet=SHEET_URL, data=edited_df)
                    st.success("Tablodaki güncellemeler Google Sheets'e başarıyla kaydedildi!")
                    st.rerun()
                    
            with col_indir:
                csv_data = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Tüm Kayıtları Excel / CSV Olarak İndir",
                    data=csv_data,
                    file_name=f"kayip_zaman_takip_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.markdown("---")
            
            # 2. TEK TEK İLGİLİ SATIRI İNCELEME, GÜNCELLEME VE SİLME
            st.markdown("### 🎯 ID Seçerek Satır Güncelleme veya Silme")
            
            id_listesi = df['ID'].dropna().astype(int).unique().tolist()
            secilen_id = st.selectbox("İşlem Yapmak İstediğiniz Kaydın ID Numarasını Seçin:", options=id_listesi)
            
            if secilen_id:
                satir = df[df['ID'] == secilen_id].iloc[0]
                
                with st.expander(f"🔍 ID #{secilen_id} Detaylarını Düzenle / Sil", expanded=True):
                    with st.form(f"form_guncelle_{secilen_id}"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            g_musteri = st.text_input("Müşteri Adı", value=str(satir["Müşteri Adı"] if pd.notna(satir["Müşteri Adı"]) else ""))
                            g_muhendis = st.text_input("Sorumlu Mühendis", value=str(satir["Sorumlu Mühendis"] if pd.notna(satir["Sorumlu Mühendis"]) else ""))
                            g_irsaliye = st.text_input("İrsaliye No", value=str(satir["İrsaliye No"] if pd.notna(satir["İrsaliye No"]) else ""))
                        with c2:
                            g_ref = st.text_input("Referans No", value=str(satir["Referans No"] if pd.notna(satir["Referans No"]) else ""))
                            g_seri = st.text_input("Seri No", value=str(satir["Seri No"] if pd.notna(satir["Seri No"]) else ""))
                            idx_neden = DURUS_NEDENLERI.index(satir["Duruş Nedeni"]) if satir["Duruş Nedeni"] in DURUS_NEDENLERI else 0
                            g_neden = st.selectbox("Duruş Nedeni", DURUS_NEDENLERI, index=idx_neden)
                        with c3:
                            g_miktar = st.number_input("Miktar", value=int(satir["Miktar"]) if pd.notna(satir["Miktar"]) else 1)
                            g_ph = st.number_input("P/H", value=float(satir["P/H"]) if pd.notna(satir["P/H"]) else 100.0)
                            g_kayip = st.number_input("Kayıp Zaman (Saat)", value=float(satir["Kayıp Zaman (Saat)"]) if pd.notna(satir["Kayıp Zaman (Saat)"]) else 1.0)
                        
                        idx_durum = DURUM_OPSIYONLARI.index(satir["Son Durum"]) if satir["Son Durum"] in DURUM_OPSIYONLARI else 0
                        g_durum = st.selectbox("Son Durum", DURUM_OPSIYONLARI, index=idx_durum)
                        g_aciklama = st.text_area("İşlem Açıklaması", value=str(satir["İşlem Açıklaması"] if pd.notna(satir["İşlem Açıklaması"]) else ""))
                        
                        col_update, col_delete = st.columns(2)
                        with col_update:
                            btn_update = st.form_submit_button("✏️ Bu Kaydı Güncelle", use_container_width=True)
                        with col_delete:
                            btn_delete = st.form_submit_button("🗑️ Bu Kaydı Sil", use_container_width=True)
                            
                        if btn_update:
                            df.loc[df['ID'] == secilen_id, "Müşteri Adı"] = g_musteri
                            df.loc[df['ID'] == secilen_id, "Sorumlu Mühendis"] = g_muhendis
                            df.loc[df['ID'] == secilen_id, "İrsaliye No"] = g_irsaliye
                            df.loc[df['ID'] == secilen_id, "Referans No"] = g_ref
                            df.loc[df['ID'] == secilen_id, "Seri No"] = g_seri
                            df.loc[df['ID'] == secilen_id, "Duruş Nedeni"] = g_neden
                            df.loc[df['ID'] == secilen_id, "Miktar"] = g_miktar
                            df.loc[df['ID'] == secilen_id, "P/H"] = g_ph
                            df.loc[df['ID'] == secilen_id, "Hesaplanan Zaman (Saat)"] = round(g_miktar / g_ph, 2) if g_ph > 0 else 0.0
                            df.loc[df['ID'] == secilen_id, "Kayıp Zaman (Saat)"] = g_kayip
                            df.loc[df['ID'] == secilen_id, "Son Durum"] = g_durum
                            df.loc[df['ID'] == secilen_id, "İşlem Açıklaması"] = g_aciklama
                            
                            conn.update(spreadsheet=SHEET_URL, data=df)
                            st.success(f"ID #{secilen_id} kaydı başarıyla güncellendi!")
                            st.rerun()
                            
                        if btn_delete:
                            guncel_df = df[df['ID'] != secilen_id]
                            conn.update(spreadsheet=SHEET_URL, data=guncel_df)
                            st.warning(f"ID #{secilen_id} kaydı silindi!")
                            st.rerun()
    else:
        # Viewer (Mehmet Alaşar için salt okunur görünüm)
        st.subheader("📊 Kayıt Listesi (Salt Okunur)")
        st.dataframe(df, use_container_width=True)
        
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Tüm Kayıtları Excel / CSV Olarak İndir",
            data=csv_data,
            file_name=f"kayip_zaman_takip_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ---------------- TAB 3: DASHBOARD ----------------
with tab3:
    st.subheader("Genel Durum & Analiz Panosu")
    df = load_data()
    
    if not df.empty and not df.dropna(how='all').empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Kayıt", f"{len(df)} Adet")
        
        toplam_kayip = pd.to_numeric(df['Kayıp Zaman (Saat)'], errors='coerce').sum()
        m2.metric("Toplam Kayıp Zaman", f"{toplam_kayip:.1f} Saat")
        
        onaylanan = pd.to_numeric(df[df['Son Durum'] == "Onay Geldi"]['Kayıp Zaman (Saat)'], errors='coerce').sum()
        m3.metric("Onaylanan Süre", f"{onaylanan:.1f} Saat")
        
        bekleyen = pd.to_numeric(df[df['Son Durum'] == "Mail Atıldı"]['Kayıp Zaman (Saat)'], errors='coerce').sum()
        m4.metric("Onay Bekleyen Süre", f"{bekleyen:.1f} Saat")
        
        st.markdown("---")
        
        c_grafik1, c_grafik2 = st.columns(2)
        with c_grafik1:
            st.write("### Müşteri Bazlı Toplam Kayıp Zamanlar (Saat)")
            musteri_ozet = df.groupby('Müşteri Adı')['Kayıp Zaman (Saat)'].sum()
            st.bar_chart(musteri_ozet)
            
        with c_grafik2:
            st.write("### Duruş Nedenlerine Göre Dağılım")
            neden_ozet = df.groupby('Duruş Nedeni')['Kayıp Zaman (Saat)'].sum()
            st.bar_chart(neden_ozet)
