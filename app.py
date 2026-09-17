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
    "Gelen Parti Miktarı", "Hata Oranı (%)", "P/H", 
    "Hesaplanan Zaman (Saat)", "Kayıp Zaman (Saat)", "Son Durum", 
    "Hata Görseli Linki", "Onay Belgesi Linki"
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

if user["role"] == "admin":
    tab1, tab2, tab3 = st.tabs(["➕ Yeni Kayıp Zaman Kaydı Ekle", "📊 Kayıt Yönetimi (Düzenle & Sil)", "📈 Analiz & Özet"])
else:
    tab2, tab3 = st.tabs(["📊 Kayıt Listesi (Salt Okunur)", "📈 Analiz & Özet"])

# ---------------- TAB 1: FORM (Yalnızca Admin) ----------------
if user["role"] == "admin":
    with tab1:
        st.subheader("Referans Bazlı Kayıp Zaman Kayıt Formu")
        
        col1, col2 = st.columns(2)
        
        with col1:
            musteri_adi = st.text_input("Müşteri Adı *", key="f_musteri")
            sorumlu_muhendis = st.text_input("Müşteri Sorumlu Mühendis Adı", key="f_muhendis")
            irsaliye_no = st.text_input("İrsaliye No", key="f_irsaliye")
            referans_no = st.text_input("Referans No *", key="f_ref")
            seri_no = st.text_input("Seri No", key="f_seri")
            durus_nedeni = st.selectbox("Duruş / Zaman Kaybı Nedeni *", DURUS_NEDENLERI, key="f_neden")
            
        with col2:
            gelen_parti = st.number_input("Gelen Parti / Stok Miktarı (Adet)", min_value=1, value=1000, step=10, key="f_parti")
            hata_orani = st.number_input("Hata Oranı (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5, key="f_hata")
            ph = st.number_input("P/H (Parça / Saat)", min_value=0.1, value=100.0, step=1.0, key="f_ph")
            
            # Canlı Arka Plan Formülü: (Gelen Parti * (Hata Oranı / 100)) / P/H
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
                    key="f_hesaplanan_manuel"
                )
            else:
                hesaplanan_zaman = canli_hesaplanan_saat
                st.success(f"⏱️ **Hesaplanan Zaman: {hesaplanan_zaman} Saat**  \n*(Detay: {int(canli_islem_adet)} Adet Hatalı Parça / {ph} P/H)*")
                
            st.markdown("---")
            kayip_zaman_saat = st.number_input("Kayıp Zaman / Fiili Duruş (Saat) *", min_value=0.0, value=1.0, step=0.1, key="f_kayip")
            son_durum = st.selectbox("Son Durum *", DURUM_OPSIYONLARI, key="f_durum")

        islem_aciklamasi = st.text_area("İşlem Açıklaması", placeholder="Yapılan işlem, duruş gerekçesi ve detaylar...", key="f_aciklama")
        
        c_link1, c_link2 = st.columns(2)
        with c_link1:
            hata_gorseli_link = st.text_input("Hata Görseli Linki (Google Drive / OneDrive vb.)", key="f_gorsel")
        with c_link2:
            onay_belgesi_link = st.text_input("Gelen Onay Belgesi Linki (Google Drive / OneDrive vb.)", key="f_onay")
            
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
                    "Müşteri Adı": musteri_adi,
                    "Sorumlu Mühendis": sorumlu_muhendis,
                    "İrsaliye No": irsaliye_no,
                    "Referans No": referans_no,
                    "Seri No": seri_no,
                    "Duruş Nedeni": durus_nedeni,
                    "İşlem Açıklaması": islem_aciklamasi,
                    "Gelen Parti Miktarı": gelen_parti,
                    "Hata Oranı (%)": hata_orani,
                    "P/H": ph,
                    "Hesaplanan Zaman (Saat)": hesaplanan_zaman,
                    "Kayıp Zaman (Saat)": kayip_zaman_saat,
                    "Son Durum": son_durum,
                    "Hata Görseli Linki": hata_gorseli_link,
                    "Onay Belgesi Linki": onay_belgesi_link
                }])
                
                guncel_df = pd.concat([mevcut_df, yeni_kayit], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=guncel_df)
                st.success(f"ID #{yeni_id} (Referans: {referans_no}) başarıyla kaydedildi! Tabloya Yazılan Saat: {hesaplanan_zaman} Saat")
                st.rerun()

# ---------------- TAB 2: GÖRÜNTÜLEME VE YÖNETİM ----------------
with tab2:
    df = load_data()
    
    if user["role"] == "admin":
        st.subheader("📊 Kayıt Yönetimi (Düzenle & Toplu/Tekli Sil)")
        
        if df.empty or df.dropna(how='all').empty:
            st.info("Henüz kayıtlı bir veri bulunmuyor.")
        else:
            if "Seç" not in df.columns:
                df.insert(0, "Seç", False)
            
            st.markdown("### 📝 Tablo Düzenleme & Seçerek Toplu Silme")
            
            edited_df = st.data_editor(
                df,
                column_config={
                    "Seç": st.column_config.CheckboxColumn("Seç", default=False),
                    "ID": st.column_config.NumberColumn("ID", disabled=True),
                    "Hata Oranı (%)": st.column_config.NumberColumn("Hata Oranı (%)", min_value=0, max_value=100, format="%.1f%%"),
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
                    conn.update(spreadsheet=SHEET_URL, data=clean_df)
                    st.success("Tablo değişiklikleri başarıyla kaydedildi!")
                    st.rerun()
                    
            with c_toplu_sil:
                if st.button("🔴 Seçili Kayıtları Toplu Sil", use_container_width=True, type="primary"):
                    secilenler = edited_df[edited_df["Seç"] == True]
                    if secilenler.empty:
                        st.warning("Lütfen silmek istediğiniz satırların solundaki 'Seç' kutucuğunu işaretleyin!")
                    else:
                        silinecek_id_listesi = secilenler["ID"].tolist()
                        kalan_df = edited_df[edited_df["Seç"] == False].drop(columns=["Seç"], errors="ignore")
                        conn.update(spreadsheet=SHEET_URL, data=kalan_df)
                        st.success(f"Seçilen {len(silinecek_id_listesi)} adet kayıt başarıyla silindi!")
                        st.rerun()
                        
            with c_indir:
                download_df = df.drop(columns=["Seç"], errors="ignore")
                csv_data = download_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Excel / CSV İndir",
                    data=csv_data,
                    file_name=f"kayip_zaman_takip_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.markdown("---")
            
            # TEK TEK İLGİLİ SATIRI İNCELEME, GÜNCELLEME VE BİREYSEL SİLME
            col_bireysel, col_tumunu_sil = st.columns([2, 1])
            
            with col_bireysel:
                st.markdown("### 🎯 Bireysel Satır Düzenleme / Tekil Silme")
                id_listesi = df['ID'].dropna().astype(int).unique().tolist()
                secilen_id = st.selectbox("İşlem Yapmak İstediğiniz Kaydın ID Numarasını Seçin:", options=id_listesi)
                
                if secilen_id:
                    satir = df[df['ID'] == secilen_id].iloc[0]
                    
                    with st.expander(f"🔍 ID #{secilen_id} Detaylarını Düzenle veya Bireysel Sil", expanded=False):
                        with st.form(f"form_guncelle_{secilen_id}"):
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                g_musteri = st.text_input("Müşteri Adı", value=str(satir["Müşteri Adı"] if pd.notna(satir["Müşteri Adı"]) else ""))
                                g_muhendis = st.text_input("Sorumlu Mühendis", value=str(satir["Sorumlu Mühendis"] if pd.notna(satir["Sorumlu Mühendis"]) else ""))
                                g_irsaliye = st.text_input("İrsaliye No", value=str(satir["İrsaliye No"] if pd.notna(satir["İrsaliye No"]) else ""))
                                g_ref = st.text_input("Referans No", value=str(satir["Referans No"] if pd.notna(satir["Referans No"]) else ""))
                                g_seri = st.text_input("Seri No", value=str(satir["Seri No"] if pd.notna(satir["Seri No"]) else ""))
                            
                            with c2:
                                idx_neden = DURUS_NEDENLERI.index(satir["Duruş Nedeni"]) if satir["Duruş Nedeni"] in DURUS_NEDENLERI else 0
                                g_neden = st.selectbox("Duruş Nedeni", DURUS_NEDENLERI, index=idx_neden)
                                g_parti = st.number_input("Gelen Parti Miktarı", value=int(satir["Gelen Parti Miktarı"]) if pd.notna(satir["Gelen Parti Miktarı"]) else 1000)
                                g_hata = st.number_input("Hata Oranı (%)", value=float(satir["Hata Oranı (%)"]) if pd.notna(satir["Hata Oranı (%)"]) else 10.0)
                                g_ph = st.number_input("P/H", value=float(satir["P/H"]) if pd.notna(satir["P/H"]) else 100.0)
                            
                            with c3:
                                g_hesaplanan = st.number_input("Hesaplanan Zaman (Saat)", value=float(satir["Hesaplanan Zaman (Saat)"]) if pd.notna(satir["Hesaplanan Zaman (Saat)"]) else 1.0)
                                g_kayip = st.number_input("Kayıp Zaman (Saat)", value=float(satir["Kayıp Zaman (Saat)"]) if pd.notna(satir["Kayıp Zaman (Saat)"]) else 1.0)
                                idx_durum = DURUM_OPSIYONLARI.index(satir["Son Durum"]) if satir["Son Durum"] in DURUM_OPSIYONLARI else 0
                                g_durum = st.selectbox("Son Durum", DURUM_OPSIYONLARI, index=idx_durum)
                            
                            g_aciklama = st.text_area("İşlem Açıklaması", value=str(satir["İşlem Açıklaması"] if pd.notna(satir["İşlem Açıklaması"]) else ""))
                            
                            col_update, col_delete = st.columns(2)
                            with col_update:
                                btn_update = st.form_submit_button("✏️ Bu Kaydı Güncelle", use_container_width=True)
                            with col_delete:
                                btn_delete = st.form_submit_button("🗑️ Bu Tek Kaydı Sil", use_container_width=True)
                                
                            if btn_update:
                                clean_df = df.drop(columns=["Seç"], errors="ignore")
                                clean_df.loc[clean_df['ID'] == secilen_id, "Müşteri Adı"] = g_musteri
                                clean_df.loc[clean_df['ID'] == secilen_id, "Sorumlu Mühendis"] = g_muhendis
                                clean_df.loc[clean_df['ID'] == secilen_id, "İrsaliye No"] = g_irsaliye
                                clean_df.loc[clean_df['ID'] == secilen_id, "Referans No"] = g_ref
                                clean_df.loc[clean_df['ID'] == secilen_id, "Seri No"] = g_seri
                                clean_df.loc[clean_df['ID'] == secilen_id, "Duruş Nedeni"] = g_neden
                                clean_df.loc[clean_df['ID'] == secilen_id, "Gelen Parti Miktarı"] = g_parti
                                clean_df.loc[clean_df['ID'] == secilen_id, "Hata Oranı (%)"] = g_hata
                                clean_df.loc[clean_df['ID'] == secilen_id, "P/H"] = g_ph
                                clean_df.loc[clean_df['ID'] == secilen_id, "Hesaplanan Zaman (Saat)"] = g_hesaplanan
                                clean_df.loc[clean_df['ID'] == secilen_id, "Kayıp Zaman (Saat)"] = g_kayip
                                clean_df.loc[clean_df['ID'] == secilen_id, "Son Durum"] = g_durum
                                clean_df.loc[clean_df['ID'] == secilen_id, "İşlem Açıklaması"] = g_aciklama
                                
                                conn.update(spreadsheet=SHEET_URL, data=clean_df)
                                st.success(f"ID #{secilen_id} kaydı başarıyla güncellendi!")
                                st.rerun()
                                
                            if btn_delete:
                                clean_df = df.drop(columns=["Seç"], errors="ignore")
                                guncel_df = clean_df[clean_df['ID'] != secilen_id]
                                conn.update(spreadsheet=SHEET_URL, data=guncel_df)
                                st.warning(f"ID #{secilen_id} kaydı silindi!")
                                st.rerun()

            with col_tumunu_sil:
                st.markdown("### ⚠️ Tüm Tabloyu Temizle")
                with st.expander("🚨 Tüm Verileri Sıfırla"):
                    st.error("Bu işlem Google Tablo'daki TÜM KAYITLARI kalıcı olarak siler!")
                    onay = st.checkbox("Evet, tüm kayıtları silmek istiyorum.")
                    if st.button("⚠️ Tüm Tabloyu Kalıcı Olarak Sil", type="primary") and onay:
                        bos_df = pd.DataFrame(columns=SUTUNLAR)
                        conn.update(spreadsheet=SHEET_URL, data=bos_df)
                        st.success("Tüm veriler başarıyla sıfırlandı!")
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
