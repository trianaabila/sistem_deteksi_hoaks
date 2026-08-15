import streamlit as st
import pickle
import re
import numpy as np
import time
from datetime import datetime

# Import Library Sastrawi untuk Pemrosesan Bahasa Alami
try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
    SASTRAWI_AVAILABLE = True
except ImportError:
    SASTRAWI_AVAILABLE = False

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="SinyalHoaks - Early Warning System",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CUSTOM CSS UNTUK TAMPILAN PREMIUM ---
st.markdown("""
<style>
    .stApp {
        background-color: var(--background-color);
    }
    
    div.stButton > button {
        border-radius: 10px;
        font-weight: 800 !important;
        transition: all 0.3s ease;
    }

    .hero-container {
        background: rgba(255, 255, 255, 0.05);
        padding: 2.5rem 2rem;
        border-bottom: 1px solid rgba(96, 165, 250, 0.3);
        margin-bottom: 2rem;
        text-align: center;
        border-radius: 12px;
    }
    
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ef4444, #f97316, #facc15);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .hero-subtitle {
        color: var(--text-color) !important;
        font-size: 1rem;
        font-weight: 400;
        max-width: 800px;
        margin: 0 auto;
        opacity: 0.9;
    }
    
    .warning-badge {
        background-color: rgba(255, 255, 255, 0.1);
        color: var(--text-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.4);
        padding: 0.25rem 0.75rem;
        border-radius: 0.5rem;
        font-size: 0.9rem;
        font-weight: 500;
        display: inline-block;
        margin-bottom: 1rem;
    }
    
    .report-card {
        background-color: var(--secondary-background-color) !important;
        border-radius: 1rem;
        border-left: 8px solid #10b981;
        padding: 1.5rem;
        margin-top: 1.5rem;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        border-right: 1px solid rgba(128, 128, 128, 0.2);
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        color: var(--text-color) !important;
    }
    
    .report-card-danger { border-left-color: #ef4444; }
    .report-card-warning { border-left-color: #f59e0b; }
    
    .flagged-tag {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 0.2rem 0.6rem;
        border-radius: 0.375rem;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.2rem;
    }

    .guide-panel {
        background: var(--secondary-background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 15px;
        color: var(--text-color) !important;
        padding: 25px;
        margin-bottom: 20px;
    }

    .guide-step {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.65rem 0;
        font-size: 1.1rem;
        color: var(--text-color) !important;
    }

    div[data-testid="stWidgetLabel"] p {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        color: var(--text-color) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. MEMUAT RESOURCES (CACHED) ---
@st.cache_resource
def load_saved_objects():
    model_loaded = False
    loaded_model, loaded_tfidf = None, None

    try:
        with open('model.pkl', 'rb') as f_model:
            loaded_model = pickle.load(f_model)

        with open('tfidf.pkl', 'rb') as f_tfidf:
            loaded_tfidf = pickle.load(f_tfidf)

        model_loaded = True

    except FileNotFoundError:
        st.error("File model.pkl atau tfidf.pkl tidak ditemukan.")

    except Exception as e:
        st.error(f"Error saat memuat model: {type(e).__name__}: {e}")
        
    return loaded_model, loaded_tfidf, model_loaded

model, tfidf, is_model_ready = load_saved_objects()

@st.cache_resource
def init_sastrawi():
    if SASTRAWI_AVAILABLE:
        stem_factory = StemmerFactory()
        stop_factory = StopWordRemoverFactory()
        return stem_factory.create_stemmer(), stop_factory.create_stop_word_remover()
    return None, None

stemmer, stopword = init_sastrawi()

# --- 4. FUNGSI PRAPROSES TEKS ---
def hitung_praproses(text):
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    
    tokens = text.split()
    text = " ".join(tokens)
    
    if SASTRAWI_AVAILABLE and stopword and stemmer:
        text = stopword.remove(text)
        text = stemmer.stem(text)
    
    return text

# --- 5. EKSTRAKSI ANOMALI KEBAHASAAN ---
def ekstrak_fitur_tambahan_heuristik(title, content):
    signals = []
    detected_words = []
    full_text = f"{title} {content}".lower()
    
    psychological_patterns = [
        (r"viralkan", "viralkan", "Desakan menyebarkan informasi secara paksa ('viralkan')."),
        (r"sebarkan", "sebarkan", "Instruksi persuasif menyebarkan pesan ('sebarkan')."),
        (r"jangan berhenti di anda", "jangan berhenti di anda", "Pola rantai informasi paksaan."),
        (r"bagikan segera", "bagikan segera", "Pemicu urgensi waktu buatan ('bagikan segera')."),
        (r"dokter menyembunyikan", "dokter menyembunyikan", "Narasi konspirasi medis fiktif."),
        (r"rahasia terungkap", "rahasia terungkap", "Pemikat asumsi konspirasi seketika."),
        (r"sebelum dihapus", "sebelum dihapus", "Ancaman psikologis sensor media."),
        (r"gratis", "gratis", "Iming-iming gratis yang mencurigakan.")
    ]
    
    for pattern, term, msg in psychological_patterns:
        if re.search(pattern, full_text):
            detected_words.append(term)
            signals.append({"type": "danger", "msg": msg})
            
    exclamation_count = full_text.count('!')
    if exclamation_count > 2:
        signals.append({"type": "warning", "msg": f"Terdeteksi {exclamation_count} tanda seru berlebih (kesan mendesak/provokatif)."})
        
    tokens = re.findall(r'\b[A-Za-z]+\b', f"{title} {content}")
    extreme_caps = [word for word in tokens if len(word) >= 4 and word.isupper()]
    if len(extreme_caps) > 2:
        signals.append({"type": "warning", "msg": f"Terdeteksi {len(extreme_caps)} kata berhuruf kapital penuh (kesan teriakan digital)."})
        for word in extreme_caps:
            detected_words.append(word.lower())
            
    return signals, list(set(detected_words))

# --- 6. INISIALISASI LOG RIWAYAT & RESET COUNTER ---
if "logs" not in st.session_state:
    st.session_state.logs = [
        {
            "timestamp": "Baru saja mulai",
            "title": "Bantuan Tunai Sosial Rp 15 Juta Terbuka",
            "content": "Bagikan segera pesan ini agar Anda memperoleh bantuan tunai langsung sebesar 15 juta dari bank indonesia! Tautan ada di bawah ini, segera sebarkan ke seluruh keluarga Anda sebelum hangus!!!",
            "score": 12.50,
            "status": "Terindikasi HOAKS"
        }
    ]

# Counter unik agar widget input dipaksa bersih saat reset
if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0

# --- 7. SIDEBAR LOG RIWAYAT ---
with st.sidebar:
    st.title("🚨 SinyalHoaks")
    st.markdown("`EARLY WARNING SYSTEM`  \n*Skrining Berita*")
    st.divider()
    
    st.subheader("📋 Log Pemeriksaan Sesi Ini")
    if len(st.session_state.logs) == 0:
        st.caption("Belum ada riwayat pemeriksaan.")
    else:
        for log in st.session_state.logs:
            score_color = "#ef4444" if log["score"] < 50 else "#10b981"
            st.markdown(f"""
            <div style="background-color: rgba(255,255,255,0.05); padding: 0.75rem; border-radius: 0.5rem; margin-bottom: 0.5rem; border-left: 4px solid {score_color}">
                <strong style="font-size: 0.85rem; color: #f1f5f9;">{log['title']}</strong><br>
                <span style="font-size: 0.75rem; color: #94a3b8;">Kepercayaan: <strong>{log['score']:.2f}%</strong></span> | 
                <span style="font-size: 0.7rem; color: #64748b;">{log['timestamp']}</span>
            </div>
            """, unsafe_allow_html=True)
            
    if st.button("🗑️ Kosongkan Seluruh Log", use_container_width=True):
        st.session_state.logs = []
        st.rerun()

# --- 8. HEADER UTAMA ---
st.markdown("""
<div class="hero-container">
    <div class="warning-badge">🚨 INTEGRATED MACHINE LEARNING PREDICTOR</div>
    <div class="hero-title">Sistem Deteksi Indikasi Awal Berita</div>
    <div class="hero-subtitle">
        Asisten deteksi dini yang membantu mengidentifikasi indikasi berita hoaks berdasarkan analisis teks dan hasil klasifikasi model.
    </div>
</div>
""", unsafe_allow_html=True)

if not is_model_ready:
    st.warning("⚠️ **Berkas Model Belum Diunggah:** File 'model.pkl' atau 'tfidf.pkl' tidak ditemukan di folder proyek ini. Sistem saat ini berjalan dalam mode simulasi heuristik.")
if not SASTRAWI_AVAILABLE:
    st.info("ℹ️ **Info Modul:** Pustaka `Sastrawi` belum terpasang di environment Anda. Proses stemming dan stopword removal akan dilewati sementara waktu.")

col_input, col_info = st.columns([8, 4])

with col_input:
    with st.container(border=True):
        st.markdown("### 📖 Panduan Penggunaan")
        st.caption("Ikuti langkah berikut untuk melakukan analisis berita.")
        st.markdown("""
        <div class="guide-panel">
            <div class="guide-step">1. Masukkan judul berita jika tersedia.</div>
            <div class="guide-step">2. Tempel isi atau narasi berita pada kolom yang tersedia.</div>
            <div class="guide-step">3. Klik tombol <b>🔍 Analisis Berita.</b></div>
            <div class="guide-step">4. Periksa hasil prediksi dan tingkat kepercayaan sistem.</div>
        </div>
        """, unsafe_allow_html=True)

with col_info:
    with st.container(border=True):
        st.markdown("#### 🚨 Pemberitahuan Sistem")
        st.markdown("Sistem memberikan indikasi awal berdasarkan hasil klasifikasi model dan bukan merupakan penentu kebenaran suatu berita.")
        st.warning(
            "Aplikasi ini menggunakan **TF-IDF** untuk merepresentasikan teks berita "
            "dalam bentuk numerik dan **algoritma Naïve Bayes** untuk melakukan klasifikasi "
            "serta menghasilkan tingkat kepercayaan prediksi."
        )

st.markdown("### 📰 Pemeriksaan Indikasi Hoaks")

# Ambil ID versi saat ini
curr_id = st.session_state.reset_count

title_input = st.text_input(
    "Judul Berita (Opsional):",
    key=f"judul_{curr_id}",
    max_chars=150,
    placeholder="Masukkan judul berita di sini jika ada..."
)

content_input = st.text_area(
    "Isi Teks Berita / Narasi Informasi lengkap (Wajib):",
    key=f"isi_{curr_id}",
    height=250,
    placeholder="Tempel atau ketik seluruh isi teks informasi di sini..."
)

col_btn1, col_btn2 = st.columns([4, 1])

with col_btn1:
    submit_btn = st.button(
        "🔍 Analisis Berita",
        type="primary",
        use_container_width=True
    )

with col_btn2:
    reset_btn = st.button(
        "🧹 Reset",
        use_container_width=True
    )

# Saat Reset diklik: naikkan counter lalu reload
if reset_btn:
    st.session_state.reset_count += 1
    st.rerun()

# --- 9. LOGIKA PEMROSESAN & PREDIKSI ---
if submit_btn:
    if not content_input.strip() or len(content_input.strip()) < 15:
        st.error("⚠️ Teks masukan terlalu pendek! Masukkan minimal 15 karakter untuk memulai analisis.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        stages = [
            ("Menganalisis Gaya Penulisan...", "Menghitung pemakaian huruf kapital dan tanda baca dramatis...", 33),
            ("Memproses Tokenisasi & Stemming...", "Menghilangkan kata hubung non-esensial dan mengubah ke kata dasar...", 66),
            ("Mengkalkulasi Probabilitas Model...", "Membandingkan fitur dengan Naïve Bayes Classifier...", 100)
        ]
        
        for text_stage, desc_stage, pct in stages:
            status_text.markdown(f"**{text_stage}** *({desc_stage})*")
            progress_bar.progress(pct)
            time.sleep(0.4)
            
        status_text.empty()
        progress_bar.empty()
        
        combined_text = f"{title_input} {content_input}"
        
        if is_model_ready:
            cleaned_text = hitung_praproses(combined_text)
            vectorized_text = tfidf.transform([cleaned_text])
            hasil_prediksi = model.predict(vectorized_text)[0]
            probabilitas = model.predict_proba(vectorized_text)[0]
            
            try:
                idx_non_hoaks = np.where(model.classes_ == '0')[0][0]
            except IndexError:
                try:
                    idx_non_hoaks = np.where(model.classes_ == 0)[0][0]
                except IndexError:
                    idx_non_hoaks = 0
            
            trust_score = float(probabilitas[idx_non_hoaks] * 100)
            is_hoax = str(hasil_prediksi) == '1'
        else:
            detected_signals, flagged_terms = ekstrak_fitur_tambahan_heuristik(title_input, content_input)
            caps_ratio = len([w for w in combined_text.split() if w.isupper()])
            exclamation_ratio = combined_text.count("!")
            
            penalty = (caps_ratio * 3) + (exclamation_ratio * 5) + (len(flagged_terms) * 15)
            trust_score = max(5.0, min(100.0 - penalty, 98.5))
            is_hoax = trust_score < 50.0

        trust_score = round(max(2.0, min(trust_score, 99.8)), 2)
        
        if trust_score >= 75:
            status_label = "TERINDIKASI NON-HOAKS (VALID)"
            border_style = ""
            card_color = "#10b981"
            title_summary = "Sinyal Kebahasaan Normal (Aman)"
            text_summary = "Model Machine Learning menyimpulkan bahwa gaya bahasa, intonasi tulisan, dan kepadatan informasi pada teks ini sangat konsisten dengan karakteristik artikel berita kredibel/resmi."
        elif 45 <= trust_score < 75:
            status_label = "PERLU KONFIRMASI (WASPADA)"
            border_style = "report-card-warning"
            card_color = "#f59e0b"
            title_summary = "Terdeteksi Sinyal Kecurigaan Ringan"
            text_summary = "Teks memiliki struktur kalimat yang netral namun memuat beberapa kata provokatif atau gaya tanda baca yang tidak standar. Lakukan cek silang secara berkala."
        else:
            status_label = "TERINDIKASI HOAKS (BAHAYA)"
            border_style = "report-card-danger"
            card_color = "#ef4444"
            title_summary = "Terdeteksi Kuat Pola Manipulasi Teks!"
            text_summary = "Dilarang membagikan kembali pesan ini! Algoritma mendeteksi tanda-tanda manipulasi berita yang signifikan seperti desakan sebar masif, gaya teriak kapital, serta provokasi kepanikan."

        # Simpan log riwayat
        st.session_state.logs.insert(0, {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "title": title_input if title_input.strip() else "Pemeriksaan Teks Mandiri",
            "content": content_input,
            "score": trust_score,
            "status": status_label
        })
        
        detected_signals, flagged_terms = ekstrak_fitur_tambahan_heuristik(title_input, content_input)

        # --- TAMPILAN DASHBOARD LAPORAN ---
        st.markdown("---")
        st.subheader("📊 Laporan Deteksi Indikasi Awal")
        
        st.markdown(f"""
        <div class="report-card {border_style}">
            <span style="background-color: {card_color}; color: #ffffff !important; padding: 0.35rem 0.75rem; border-radius: 0.5rem; font-size: 0.8rem; font-weight: 800; text-transform: uppercase; display: inline-block;">
                {status_label}
            </span>
            <h4 style="margin-top: 1rem; color: var(--text-color) !important; font-size: 1.25rem; font-weight: 700;">{title_summary}</h4>
            <p style="color: var(--text-color) !important; opacity: 0.9; font-size: 0.95rem; font-weight: 400; line-height: 1.6; margin-bottom: 0;">{text_summary}</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_gauge, col_bars = st.columns([4, 8])
        
        with col_gauge:
            st.markdown("<br>", unsafe_allow_html=True)
            st.metric(
                label="Tingkat Kepercayaan Hasil Prediksi", 
                value=f"{trust_score:.2f}%", 
                delta="Sangat Kredibel" if trust_score >= 75 else ("Kurang Terpercaya" if trust_score >= 45 else "Risiko Tinggi"),
                delta_color="normal" if trust_score >= 75 else "inverse"
            )
            st.progress(trust_score / 100)
            
        with col_bars:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Nilai Parameter Probabilitas Kelas:**")
            
            st.markdown(f"Probabilitas Teks Asli (Valid): **{trust_score:.2f}%**")
            st.progress(trust_score / 100)
            
            hoax_prob = round(100.0 - trust_score, 2)
            st.markdown(f"Probabilitas Teks Manipulatif (Hoaks): **{hoax_prob:.2f}%**")
            st.progress(hoax_prob / 100)
            
        col_signals, col_words = st.columns([7, 5])
        
        with col_signals:
            st.markdown("#### 📡 Sinyal Kebahasaan yang Terdeteksi:")
            if not detected_signals:
                st.success("✅ Tidak ditemukan sinyal anomali kebahasaan mayor pada susunan teks.")
            else:
                for sig in detected_signals:
                    if sig["type"] == "danger":
                        st.error(f"🚨 {sig['msg']}")
                    elif sig["type"] == "warning":
                        st.warning(f"⚠️ {sig['msg']}")
                    
        with col_words:
            st.markdown("#### 🔍 Istilah Sensasional / Atensi Khusus:")
            if len(flagged_terms) == 0:
                st.write("Tidak ditemukan kata-kata provokasi atau pancingan psikologis khusus.")
            else:
                st.caption("Istilah pemicu respon emosional pembaca yang diidentifikasi di dalam teks:")
                tags_html = "".join([f'<span class="flagged-tag">{word}</span>' for word in flagged_terms])
                st.markdown(tags_html, unsafe_allow_html=True)
