import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import gspread

# Page Configuration
st.set_page_config(page_title="Müşteri Kayıp Zaman Takip Sistemi", layout="wide", page_icon="⏱️")

# Google Sheet URL (Orijinal Kararlı Bağlantı)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UsGlWxzRmiriAufzk14D0oiS3CyHMAjENyFhIbw9VG4/edit?pli=1&gid=0#gid=0"

# Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

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

# --- GSPREAD İLE GÜVENLİ GOOGLE SHEETS YAZMA YARDIMCISI ---
def update_google_sheet(df):
    try:
        # Streamlit secrets üzerinden gspread kimlik doğrulaması
        gc = gspread.service_account_from_dict(st.secrets["connections"]["gsheets"])
        spreadsheet = gc.open_by_url(SHEET_URL)
        worksheet = spreadsheet.get_worksheet(0) # İlk sayfa
        
        # DataFrame'i temizle ve NaN değerleri boş string yap
        df_to_write = df.fillna("")
        
        # Tabloyu tamamen temizle ve yeniden yaz
        worksheet.clear()
        worksheet.update([df_to_write.columns.values.tolist()] + df_to_write.values.tolist())
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

# --- ÖZELLEŞTİRİLMİŞ SÜTUN SEÇMELİ MÜŞTERİ RAPORU ---
def generate_customer_report(dataframe, filtered_customer, selected_columns):
    filtered_df = dataframe[selected_columns] if selected_columns else dataframe
    
    toplam_kayit = len(dataframe)
    toplam_kayip = pd.to_numeric(dataframe['Kayıp Zaman (Saat)'], errors='coerce').sum()
    onaylanan = pd.to_numeric(dataframe[dataframe['Son Durum'] == "Onay Geldi"]['Kayıp Zaman (Saat)'], errors='coerce').sum()
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="utf-8">
        <title>Müşteri Kayıp Zaman & Duruş Raporu</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 30px; color: #222; }}
            .header {{ text-align: center; border-bottom: 2px solid #1f77b4; padding-bottom: 10px; margin-bottom: 20px; }}
            .header h2 {{ color: #1f77b4; margin: 0; }}
            .info {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #dee2e6; }}
            .info p {{ margin: 5px 0; font-size: 14px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }}
            th, td {{ border: 1px solid #ced4da; padding: 8px; text-align: left; }}
            th {{ background-color: #1f77b4; color: white; }}
            tr:nth-child(even) {{ background-color: #f8f9fa; }}
            .footer {{ margin-top: 30px; text-align: center; font-size: 12px; color: #6c757d; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>ALAŞAR GRUP - MÜŞTERİ KAYIP ZAMAN & DURUŞ RAPORU</h2>
        </div>
        <div class="info">
            <p><strong>Rapor Tarihi:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
            <p><strong>Raporlanan Müşteri / Kriter:</strong> {filtered_customer}</p>
            <p><strong>Toplam Kayıt:</strong> {toplam_kayit} Adet &nbsp;|&nbsp; <strong>Toplam Kayıp Zaman:</strong> {toplam_kayip:.1f} Saat &nbsp;|&nbsp; <strong>Onaylanan Süre:</strong> {onaylanan:.1f} Saat</p>
        </div>
        {filtered_df.to_html(index=False, escape=False)}
        <div class="footer">
            <p>Bu rapor Müşteri Kayıp Zaman & Fatura Takip Sistemi üzerinden otomatik olarak üretilmiştir.</p>
        </div>
    </body>
    </html>
    """
    return html_content

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
    tab1, tab2, tab3 = st.tabs(["➕ Yeni Kayıp Zaman Kaydı Ekle", "📊 Kayıt Yönetimi (Düzenle & Sil)", "📈 Analiz & Rapor"])
else:
    tab2, tab3 = st.tabs(["📊 Kayıt Listesi (Salt Okunur)", "📈 Analiz & Rapor"])

# ---------------- TAB 1: FORM ----------------
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
        
        c_link1, c_link2, c_link3 = st.columns(3)
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
                    "Etiket Görseli Linki": etiket_gorseli_link,
                    "Hata Görseli Linki": hata_gorseli_link,
                    "Onay Belgesi Linki": onay_belgesi_link
                }])
                
                guncel_df = pd.concat([mevcut_df, yeni_kayit], ignore_index=True)
                if update_google_sheet(guncel_df):
                    st.success(f"ID #{yeni_id} (Referans: {referans_no}) başarıyla kaydedildi!")
                    st.rerun()

# ---------------- TAB 2: YÖNETİM ----------------
with tab2:
    df = load_data()
    
    if user["role"] == "admin":
        st.subheader("📊 Kayıt Yönetimi (Düzenle & Toplu/Tekli Sil)")
        
        if df.empty or df.dropna(how='all').empty:
            st.info("Henüz kayıtlı bir veri bulunmuyor.")
        else:
            if "Seç" not in df.columns:
                df.insert(0, "Seç", False)
            
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
                    if update_google_sheet(clean_df):
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
                        if update_google_sheet(kalan_df):
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
            
            col_bireysel, col_tumunu_sil = st.columns([2, 1])
            
            with col_bireysel:
                st.subheader("🎯 Bireysel Satır Düzenleme / Tekil Silme")
                id_listesi = df['ID'].dropna().astype(int).unique().tolist()
                secilen_id = st.selectbox("ID Numarası Seçin:", options=id_listesi)
                
                if secilen_id:
                    satir = df[df['ID'] == secilen_id].iloc[0]
                    
                    with st.expander(f"🔍 ID #{secilen_id} Detayları", expanded=False):
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
                                g_parti = st.number_input("Gelen Parti", value=int(satir["Gelen Parti Miktarı"]) if pd.notna(satir["Gelen Parti Miktarı"]) else 1000)
                                g_hata = st.number_input("Hata Oranı (%)", value=float(satir["Hata Oranı (%)"]) if pd.notna(satir["Hata Oranı (%)"]) else 10.0)
                                g_ph = st.number_input("P/H", value=float(satir["P/H"]) if pd.notna(satir["P/H"]) else 100.0)
                            
                            with c3:
                                g_hesaplanan = st.number_input("Hesaplanan Zaman", value=float(satir["Hesaplanan Zaman (Saat)"]) if pd.notna(satir["Hesaplanan Zaman (Saat)"]) else 1.0)
                                g_kayip = st.number_input("Kayıp Zaman", value=float(satir["Kayıp Zaman (Saat)"]) if pd.notna(satir["Kayıp Zaman (Saat)"]) else 1.0)
                                idx_durum = DURUM_OPSIYONLARI.index(satir["Son Durum"]) if satir["Son Durum"] in DURUM_OPSIYONLARI else 0
                                g_durum = st.selectbox("Son Durum", DURUM_OPSIYONLARI, index=idx_durum)
                            
                            g_aciklama = st.text_area("İşlem Açıklaması", value=str(satir["İşlem Açıklaması"] if pd.notna(satir["İşlem Açıklaması"]) else ""))
                            
                            g_etiket = st.text_input("Etiket Görseli Linki", value=str(satir["Etiket Görseli Linki"] if pd.notna(satir["Etiket Görseli Linki"]) else ""))
                            g_gorsel = st.text_input("Hata Görseli Linki", value=str(satir["Hata Görseli Linki"] if pd.notna(satir["Hata Görseli Linki"]) else ""))
                            g_onay = st.text_input("Onay Belgesi Linki", value=str(satir["Onay Belgesi Linki"] if pd.notna(satir["Onay Belgesi Linki"]) else ""))
                            
                            col_update, col_delete = st.columns(2)
                            with col_update:
                                btn_update = st.form_submit_button("✏️ Güncelle", use_container_width=True)
                            with col_delete:
                                btn_delete = st.form_submit_button("🗑️ Sil", use_container_width=True)
                                
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
                                clean_df.loc[clean_df['ID'] == secilen_id, "Etiket Görseli Linki"] = g_etiket
                                clean_df.loc[clean_df['ID'] == secilen_id, "Hata Görseli Linki"] = g_gorsel
                                clean_df.loc[clean_df['ID'] == secilen_id, "Onay Belgesi Linki"] = g_onay
                                
                                if update_google_sheet(clean_df):
                                    st.success("Güncellendi!")
                                    st.rerun()
                                
                            if btn_delete:
                                clean_df = df.drop(columns=["Seç"], errors="ignore")
                                guncel_df = clean_df[clean_df['ID'] != secilen_id]
                                if update_google_sheet(guncel_df):
                                    st.warning("Silindi!")
                                    st.rerun()

            with col_tumunu_sil:
                st.subheader("⚠️ Tabloyu Temizle")
                with st.expander("🚨 Tüm Verileri Sıfırla"):
                    onay = st.checkbox("Evet, tüm kayıtları sil.")
                    if st.button("⚠️ Tüm Tabloyu Sil", type="primary") and onay:
                        bos_df = pd.DataFrame(columns=SUTUNLAR)
                        if update_google_sheet(bos_df):
                            st.success("Sıfırlandı!")
                            st.rerun()
    else:
        st.dataframe(df, use_container_width=True)

# ---------------- TAB 3: ANALİZ & RAPOR ----------------
with tab3:
    st.subheader("Analiz Panosu & Müşteri Raporu")
    df = load_data()
    
    if not df.empty and not df.dropna(how='all').empty:
        st.markdown("### 📄 Özelleştirilmiş Müşteri Raporu İndir")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            musteri_listesi = ["Tüm Müşteriler"] + df['Müşteri Adı'].dropna().unique().tolist()
            secilen_musteri = st.selectbox("Raporlanacak Müşteriyi Seçin:", options=musteri_listesi)
            
        with col_r2:
            varsayilan_sutunlar = [c for c in ["Tarih", "Müşteri Adı", "Referans No", "Duruş Nedeni", "Kayıp Zaman (Saat)", "Son Durum"] if c in df.columns]
            secilen_sutunlar = st.multiselect(
                "Raporda Görünmesini İstediğiniz Sütunlar:",
                options=df.columns.tolist(),
                default=varsayilan_sutunlar
            )
        
        rapor_df = df if secilen_musteri == "Tüm Müşteriler" else df[df['Müşteri Adı'] == secilen_musteri]
        
        if not secilen_sutunlar:
            st.warning("⚠️ Lütfen raporda görünmesi için en az bir sütun seçin!")
        else:
            html_report = generate_customer_report(rapor_df, secilen_musteri, secilen_sutunlar)
            
            st.download_button(
                label=f"📥 Seçilen Sütunlarla Raporu İndir (HTML / Tarayıcıda Aç)",
                data=html_report,
                file_name=f"Rapor_{secilen_musteri}_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )
            st.caption("ℹ️ İndirdiğiniz rapora çift tıklayarak tarayıcınızda açabilir, klavyeden **Ctrl+P** tuşlarına basarak doğrudan **PDF olarak kaydedebilirsiniz**.")
        
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Kayıt", len(df))
        m2.metric("Toplam Kayıp Zaman", f"{pd.to_numeric(df['Kayıp Zaman (Saat)'], errors='coerce').sum():.1f} Saat")
        m3.metric("Onaylanan Süre", f"{pd.to_numeric(df[df['Son Durum'] == 'Onay Geldi']['Kayıp Zaman (Saat)'], errors='coerce').sum():.1f} Saat")
        m4.metric("Bekleyen Süre", f"{pd.to_numeric(df[df['Son Durum'] == 'Mail Atıldı']['Kayıp Zaman (Saat)'], errors='coerce').sum():.1f} Saat")
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Müşteri Bazlı Toplam Kayıp Zamanlar")
            st.bar_chart(df.groupby('Müşteri Adı')['Kayıp Zaman (Saat)'].sum())
        with c2:
            st.write("### Duruş Nedenlerine Göre Dağılım")
            st.bar_chart(df.groupby('Duruş Nedeni')['Kayıp Zaman (Saat)'].sum())
