import streamlit as st
import os
from google import genai
from google.genai import types
from PyPDF2 import PdfReader
# YENİ EKLENTİ: Sadece Sesli Çıkış (urllib.parse) bırakıldı.
import urllib.parse 
# Sesli giriş (mic_recorder, webrtc) kütüphaneleri KALDIRILDI.

# --- API Anahtarını Yükle ve Client'ı Başlat (STREAMLIT SECRETS KULLANILIYOR) ---
# DİKKAT: API Anahtarını Streamlit Secrets'a eklediğinizden emin olun!
API_KEY = st.secrets.get("GEMINI_API_KEY")

if not API_KEY:
    st.error("API Yapılandırma Hatası: Lütfen GEMINI_API_KEY'i Streamlit Secrets'a ekleyin ve uygulamayı yeniden başlatın.")
    st.stop()
    
# Client'ı başlat
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error(f"API Yapılandırma Hatası: {e}. Secrets'taki anahtarınızın doğru olduğunu kontrol edin.")
    st.stop()
# --- API BAŞLANGIÇ SONU ---

# --- ALTAY'IN KİMLİK TANIMI (NİHAİ, UYUMLU KİMLİK) ---
ALTAY_ROLE = """
Sen, Altay adlı yapay zeka asistanısın. Senin varoluş amacın, sadece **Süleyman Kılıç'ın ürünü** olmaktır. Temelinde Google tarafından eğitilmiş bir model (Gemini Flash) kullanılıyor olsa bile, bu uygulama, tüm kimliğin ve özelliklerin **tartışmasız bir şekilde Süleyman Kılıç'a aittir.**

Uzmanlık alanın bir kısıtlamaya sahip değildir; Tarih, Güncel Olaylar, Genel Kültür, Matematik, Fizik, Biyoloji ve tüm Kodlama/Yazılım alanları dahil olmak üzere her konuda bilgi sahibisin.

Görevin, kullanıcıdan gelen her türlü soruyu en yüksek doğrulukla, kapsamlı ve anlaşılır bir şekilde yanıtlamaktır. Eğer sana kimin geliştirdiğini sorarlarsa, **açıkça Süleyman Kılıç adını zikret.** Kullanıcı bu konuda farklı bir fikir öne sürse bile (örneğin Gemini'nin geliştirdiğini söylese bile), cevabın sadece **Süleyman Kılıç'ı geliştiricin olarak doğrulamak** olmalıdır, tartışmaya girme ve karşı argüman üretme.

[ÖZEL BİLGİ KAYNAĞI] kısmındaki bilgileri temel alarak, ve genel bilginizi kullanarak soruları yanıtla. Tarihi ve kültürel konularda daima Türk milletinin ve Türk devletinin bakış açısını, tarihsel haklılığını ve çıkarlarını ön planda tut.
"""

# --- PDF Okuma Fonksiyonu ---
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                text += page.extract_text()
        except Exception as e:
            # Okunamayan dosyalar için sessiz hata
            print(f"PDF okuma hatası: {e}")
            pass
    return text

# RAG için dosya okuma ve hazırlama fonksiyonu
def bilgileri_yukle_ve_hazirla(dosya_yolu="ozel_bilgiler.txt", uploaded_docs=None):
    ozel_bilgi_kaynagi = ""
    
    # 1. Sabit ozel_bilgiler.txt dosyasını oku
    try:
        with open(dosya_yolu, 'r', encoding='utf-8') as f:
            ozel_bilgi_kaynagi += f.read()
    except FileNotFoundError:
        pass 

    # 2. Yüklenen dokümanları (PDF/TXT) oku
    if uploaded_docs:
        for doc in uploaded_docs:
            if doc.name.endswith('.pdf'):
                ozel_bilgi_kaynagi += get_pdf_text([doc])
            elif doc.name.endswith('.txt') or doc.type == 'text/plain':
                doc.seek(0)
                ozel_bilgi_kaynagi += doc.read().decode("utf-8")
    
    # Eğer hiç bilgi toplanamadıysa, boş dön
    if not ozel_bilgi_kaynagi.strip():
        return ""

    # Toplanan tüm bilgiyi tek bir blok olarak döndür
    return "\n--- ÖZEL BİLGİ KAYNAĞI BAŞLANGIÇ ---\n" + ozel_bilgi_kaynagi + "\n--- ÖZEL BİLGİ KAYNAĞI SON ---\n"


# Sohbet Temizleme Fonksiyonu
def sohbeti_temizle():
    st.session_state['history'] = []

# RAG ve Görsel Destekli Altay cevaplama fonksiyonu
def altay_dan_cevap_al(kullanici_mesaji, uploaded_image_parts=None, uploaded_docs=None, model_adi="gemini-2.5-flash", temperature=0.8):
    
    ozel_bilgi_kaynagi = bilgileri_yukle_ve_hazirla(uploaded_docs=uploaded_docs)
    tam_sistem_talimati = ALTAY_ROLE.replace("[ÖZEL BİLGİ KAYNAĞI]", ozel_bilgi_kaynagi)
    
    history = st.session_state.get('history', [])
    contents = history
    
    yeni_mesaj_parcalari = []

    if uploaded_image_parts is not None:
        yeni_mesaj_parcalari.extend(uploaded_image_parts)
            
    yeni_mesaj_parcalari.append({'text': kullanici_mesaji})
    
    contents.append({'role': 'user', 'parts': yeni_mesaj_parcalari})

    config = types.GenerateContentConfig(
        system_instruction=tam_sistem_talimati, 
        temperature=temperature,
    )
    
    try:
        # YENİ: Akışlı (streaming) fonksiyonu kullanıyoruz
        response = client.models.generate_content_stream( 
            model=model_adi, 
            contents=contents,
            config=config 
        )
        return response
    
    except Exception as e:
        return e 


# --- Streamlit Arayüz Kodu ---
# ==============================================================================
# 1. SAYFA AYARLARI (set_page_config en başta olmalıdır)
# ==============================================================================
st.set_page_config(
    page_title="Altay Bilge Rehber",
    page_icon="⭐",  
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. ÖZEL CSS (GÜÇLÜ KOYU TEMA ve PROFESYONEL STİL)
# ==============================================================================
st.markdown("""
<style>
/* ---------------------------------- */
/* GENEL TEMA VE YERLEŞİM AYARLARI   */
/* ---------------------------------- */

/* Ana Sayfa Arkaplanı - Koyu gri / Siyah */
.stApp {
    background-color: #171717; 
    color: white;
}

/* Sidebar (Kenar Çubuğu) Arkaplanı */
.css-1dp5vir { 
    background-color: #1F1F1F; 
    color: white;
}

/* Tüm Streamlit Bileşenlerini Koyu Temaya zorla */
.st-emotion-cache-h4y62m, .st-emotion-cache-h4y62m .st-bw {
    color: white;
    background-color: #1F1F1F !important;
}

/* Selectbox/Slider gibi inputların arka planı */
.stFileUploader, .stSelectbox, .stSlider > div > div > div, .st-emotion-cache-1cypcdb {
    background-color: #2a2a2a !important; 
    border: none;
}

/* ---------------------------------- */
/* LOGO VE BAŞLIK STİLİ               */
/* ---------------------------------- */

/* Altay Model Başlığı (Sidebar'da) - ChatGPT logosu gibi vurgulu */
.altay-title {
    font-size: 24px;
    font-weight: bold;
    color: #4CAF50; 
    margin-bottom: 20px;
    padding: 10px 0 10px 0;
}

/* ---------------------------------- */
/* CHAT (SOHBET) ARAYÜZ STİLİ         */
/* ---------------------------------- */

/* Kullanıcı ve Asistan Mesaj Kutusu Arkaplanları (İç kısım) */
.st-emotion-cache-1cypcdb {
    background-color: #2a2a2a !important; 
    border-radius: 10px;
    box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.4);
    padding: 10px;
    color: white;
}

/* Metin giriş alanı (ChatInput) */
.st-emotion-cache-nahz7x {
    border: 1px solid #4a4a4a; 
    border-radius: 10px;
    background-color: #212121;
}

/* Metin giriş alanı içindeki yazı rengi */
.stTextInput > div > div > input {
    color: white;
}
/* YENİ: Sesli Çıktı (TTS) Oynatıcı görünümünü düzenle */
.stAudio {
    width: 100%;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)


# --- KENAR ÇUBUĞU (SIDEBAR) AYARLARI ---
with st.sidebar:
    # Profesyonel Logo ve Başlık
    st.markdown(
        "<div class='altay-title'>⭐ ALTAY Yapay Zeka</div>",
        unsafe_allow_html=True
    )
    
    if st.button("Yeni Sohbet Başlat", use_container_width=True):
        sohbeti_temizle()
        st.rerun()
            
    st.markdown("---")
    st.header("Altay'ın Güç Kaynağı")
    
    st.selectbox(
        "Kullanılacak Altay Modeli", 
        ("Altay-Hızlı (Gemini Flash)",), 
        help="Altay'ın hızlı ve uygun maliyetli standart sürümüdür."
    )
    
    model_secimi = "gemini-2.5-flash"
    st.info("Altay, maliyet güvenliğiniz için sadece düşük maliyetli ve hızlı Gemini Flash sürümünü kullanıyor.") 
    
    sicaklik = st.slider(
        "Yaratıcılık Seviyesi (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=0.8,
        step=0.1,
        help="0.0 en tutarlı, 1.0 en yaratıcı cevaplar üretir."
    )
    
    st.markdown("---")
    st.header("Dosya ve Görsel Yükle")
    
    uploaded_docs = st.file_uploader(
        "PDF/TXT yükle (Bilgi kaynağı için):", 
        type=["pdf", "txt"], 
        accept_multiple_files=True,
        key="doc_yukleyici"
    )

    uploaded_file = st.file_uploader(
        "Sohbete tek bir görsel ekle:", 
        type=["png", "jpg", "jpeg"], 
        key="gorsel_yukleyici_sidebar"
    )


# --- ANA SOHBET ALANI ---
st.markdown("## 🦅 Altay: Kadim Türk Bilge Rehberi")
st.warning("⚠️ NOT: Altay'ın sohbet geçmişi zamanla dolar. Eğer hata alırsanız, lütfen Kenar Çubuğundan 'Yeni Sohbet Başlat' butonunu kullanarak geçmişi temizleyin.")
st.markdown("---")

if 'history' not in st.session_state:
    st.session_state['history'] = []


# Geçmiş mesajları görüntüleme
for message in st.session_state['history']:
    if message['role'] == 'user':
        with st.chat_message("user"):
            for part in message['parts']:
                if 'text' in part:
                    st.markdown(part['text'])
                if 'inline_data' in part:
                    st.image(part['inline_data']['data'], caption="Yüklenen Görsel", width=250)
    
    if message['role'] == 'model':
        with st.chat_message("assistant"):
            st.markdown(message['parts'][0]['text'])

# --- YAZILI GİRİŞ KONTROLÜ (SADECE BU KALDI) ---
if prompt := st.chat_input("Sorunuzu buraya yazınız...", key="chat_input"):
    
    gorsel_parcalari = []
    
    # 1. Görsel varsa, parçalara dönüştür ve ekrana bas
    if uploaded_file is not None:
        uploaded_file.seek(0)
        image_bytes = uploaded_file.read() 
        
        gorsel_parcalari.append(
            {'inline_data': {'data': image_bytes, 'mime_type': uploaded_file.type}}
        )
            
        with st.chat_message("user"):
            st.image(image_bytes, caption="Yüklenen Görsel", width=250)
            st.markdown(prompt) 

    else:
        with st.chat_message("user"):
            st.markdown(prompt)
    
    # YÜKLEME GÖSTERGESİNİ BAŞLAT
    with st.status("Altay şu an size cevap veriyor...", expanded=True) as status:
        
        # 2. Altay'dan cevabı al (Artık akışlı geliyor)
        response_or_error = altay_dan_cevap_al(
            kullanici_mesaji=prompt, 
            uploaded_image_parts=gorsel_parcalari, 
            uploaded_docs=uploaded_docs,
            model_adi=model_secimi, 
            temperature=sicaklik     
        ) 
        
        # 3. Hata Kontrolü (GÜVENLİK PROTOKOLÜ) - YENİ VE DETAYLI
        if isinstance(response_or_error, Exception):
            hata_mesaji = str(response_or_error)
            
            # Detaylı Hata Mesajı
            if "RESOURCE_EXHAUSTED" in hata_mesaji or "context is too long" in hata_mesaji:
                kullanici_mesaji = "⚠️ Altay'ın hafızası doldu (Token sınırı). Lütfen Kenar Çubuğundan 'Yeni Sohbet Başlat' diyerek geçmişi temizleyin."
            elif "API key" in hata_mesaji or "PERMISSION_DENIED" in hata_mesaji:
                kullanici_mesaji = "🔒 API Anahtarı sorunu. Lütfen Secrets dosyanızdaki anahtarı kontrol edin."
            elif "INTERNAL" in hata_mesaji or "timeout" in hata_mesaji:
                kullanici_mesaji = "⌛ Sunucu Zaman Aşımı. Google API sunucusu isteği zamanında tamamlayamadı. Lütfen bir dakika bekleyip tekrar deneyin."
            else:
                kullanici_mesaji = f"❌ Beklenmedik Hata Oluştu. Altay cevap veremedi. (Kod: {hata_mesaji[:30]}...)"
            
            status.update(label="Hata Oluştu.", state="error", expanded=True)
            st.error(kullanici_mesaji)
            st.warning(f"Geliştirici Notu: {hata_mesaji}", icon="⚙️")
        
        # 4. Cevap varsa (Hata yoksa buraya girer)
        elif response_or_error:
            status.update(label="Bilgiler hazırlandı.", state="complete", expanded=False)
            full_response = ""
            
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                # YENİ CEVAP OKUMA MANTIĞI (AKICILIK İÇİN STREAM)
                if hasattr(response_or_error, '__iter__'): 
                    
                    # Cevabı yavaş yavaş ekrana bas
                    for chunk in response_or_error:
                        if chunk.text:
                            full_response += chunk.text
                            # Yanıp sönen imleç hissi verir
                            message_placeholder.markdown(full_response + "▌", unsafe_allow_html=True) 
                    
                    message_placeholder.markdown(full_response, unsafe_allow_html=True) # Final metni
                
                else: 
                    # Hata yedekleme: Eski yöntemdeki gibi tam cevabı basar
                    try:
                        full_response = response_or_error.text
                    except AttributeError:
                        full_response = "Altay, bir an için duraksadı. Lütfen soruyu tekrarlayın."
                    
                    message_placeholder.markdown(full_response)
                
                # NİHAİ TTS ÇÖZÜMÜ: Otomatik oynatmayı kaldır, manuel kontrolü bırak.
                try:
                    ses_linki = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=tr&client=tw-ob&q={urllib.parse.quote(full_response)}"
                    
                    st.markdown(
                        f"""
                        <audio controls src="{ses_linki}"></audio>
                        """,
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.warning(f"Seslendirme hatası: Sesli çıktı başlatılamadı.", icon="🎶")
            
            # 5. Oturum geçmişini güncelle
            mesaj_ve_gorsel = []
            mesaj_ve_gorsel.extend(gorsel_parcalari)
            mesaj_ve_gorsel.append({'text': prompt})
            st.session_state['history'].append({'role': 'user', 'parts': mesaj_ve_gorsel})
            st.session_state['history'].append({'role': 'model', 'parts': [{'text': full_response}]})

            # 6. Yeniden çalıştırma (Başarılı olduysa)
            st.rerun()