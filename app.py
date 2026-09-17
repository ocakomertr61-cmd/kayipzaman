import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Page Configuration
st.set_page_config(page_title="Müşteri Kayıp Zaman Takip Sistemi", layout="wide", page_icon="⏱️")

st.title("⏱️ Müşteri Kayıp Zaman & Fatura Takip Sistemi")
st.markdown("---")

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

def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        # Sütun eksikse veya başlıklar eşleşmiyorsa düzelt
        for col in SUTUNLAR:
            if col not in df.columns:
                df[col] = None
        df = df[SUTUNLAR]
        # ID sütununu sayısal formata getir
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
        return df.dropna(how='all')
    except Exception:
        return pd.DataFrame(columns=SUTUNLAR)

DURUM_OPSIYONLARI = ["Mail Atıldı", "Onay Geldi", "Red Oldu", "Revize İstendi"]

DURUS_NEDENLERI = [
    "Rework / Yeniden İşleme", 
    "Malzeme Eksikliği / Bekleme", 
    "Kalite Problemi / Ayıklama", 
    "Ekipman / Line Arızası", 
    "Kalıp / Parça Uyumsuzluğu", 
    "Diğer"
]

tab1, tab2, tab3 = st.tabs(["➕ Yeni Kayıp Zaman Kaydı Ekle", "📊 Kayıt Yönetimi (Düzenle & Sil)", "📈 Analiz & Özet"])

# ---------------- TAB 1: FORM ----------------
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
                # Otomatik ID Atama
                yeni_id = 1 if mevcut_df.empty or mevcut_df['ID'].max() is None or pd.isna(mevcut_df['ID'].max()) else int(mevcut_df['ID'].max()) + 1
                
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
                st.success(f" ID #{yeni_id} (Referans: {referans_no}) başarıyla kaydedildi!")
                st.rerun()

# ---------------- TAB 2: EDIT & DELETE ----------------
with tab2:
    st.subheader("📊 Kayıt Listesi, Güncelleme ve Silme İşlemleri")
    df = load_data()
    
    if df.empty:
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
            num_rows="dynamic",
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
        
        id_listesi = df['ID'].dropna().astype(int).tolist()
        secilen_id = st.selectbox("İşlem Yapmak İstediğiniz Kaydın ID Numarasını Seçin:", options=id_listesi)
        
        if secilen_id:
            satir = df[df['ID'] == secilen_id].iloc[0]
            
            with st.expander(f"🔍 ID #{secilen_id} Detaylarını Düzenle / Sil", expanded=True):
                with st.form(f"form_guncelle_{secilen_id}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        g_musteri = st.text_input("Müşteri Adı", value=str(satir["Müşteri Adı"] or ""))
                        g_muhendis = st.text_input("Sorumlu Mühendis", value=str(satir["Sorumlu Mühendis"] or ""))
                        g_irsaliye = st.text_input("İrsaliye No", value=str(satir["İrsaliye No"] or ""))
                    with c2:
                        g_ref = st.text_input("Referans No", value=str(satir["Referans No"] or ""))
                        g_seri = st.text_input("Seri No", value=str(satir["Seri No"] or ""))
                        idx_neden = DURUS_NEDENLERI.index(satir["Duruş Nedeni"]) if satir["Duruş Nedeni"] in DURUS_NEDENLERI else 0
                        g_neden = st.selectbox("Duruş Nedeni", DURUS_NEDENLERI, index=idx_neden)
                    with c3:
                        g_miktar = st.number_input("Miktar", value=int(satir["Miktar"]) if pd.notna(satir["Miktar"]) else 1)
                        g_ph = st.number_input("P/H", value=float(satir["P/H"]) if pd.notna(satir["P/H"]) else 100.0)
                        g_kayip = st.number_input("Kayıp Zaman (Saat)", value=float(satir["Kayıp Zaman (Saat)"]) if pd.notna(satir["Kayıp Zaman (Saat)"]) else 1.0)
                    
                    idx_durum = DURUM_OPSIYONLARI.index(satir["Son Durum"]) if satir["Son Durum"] in DURUM_OPSIYONLARI else 0
                    g_durum = st.selectbox("Son Durum", DURUM_OPSIYONLARI, index=idx_durum)
                    g_aciklama = st.text_area("İşlem Açıklaması", value=str(satir["İşlem Açıklaması"] or ""))
                    
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

# ---------------- TAB 3: DASHBOARD ----------------
with tab3:
    st.subheader("Genel Durum & Analiz Panosu")
    df = load_data()
    
    if not df.empty:
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
