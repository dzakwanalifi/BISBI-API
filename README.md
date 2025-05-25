# BISBI AI - API Backend

Selamat datang di dokumentasi API Backend untuk BISBI AI (Bisa Bahasa Inggris AI), sebuah aplikasi pembelajaran bahasa Inggris berbasis kecerdasan buatan (AI) yang dirancang khusus untuk memberdayakan pemuda Indonesia. API ini menyediakan fungsionalitas inti yang ditenagai oleh layanan Microsoft Azure AI untuk mendukung pengalaman belajar yang interaktif, personal, dan kontekstual.

**API ini telah di-deploy dan dapat diakses melalui Azure Function App.**

## Daftar Isi

- [BISBI AI - API Backend](#bisbi-ai---api-backend)
  - [Daftar Isi](#daftar-isi)
  - [1. Deskripsi Proyek](#1-deskripsi-proyek)
  - [2. Arsitektur Backend](#2-arsitektur-backend)
  - [3. Prasyarat Penggunaan API](#3-prasyarat-penggunaan-api)
  - [4. Endpoint API](#4-endpoint-api)
    - [4.1 Status API (Health Check)](#41-status-api-health-check)
    - [4.2 Deteksi Objek Visual (BISBI Pindai - Backend)](#42-deteksi-objek-visual-bisbi-pindai---backend)
    - [4.3 Dapatkan Detail Objek Visual dengan OpenAI (BISBI Pindai - Backend)](#43-dapatkan-detail-objek-visual-dengan-openai-bisbi-pindai---backend)
    - [4.4 Generasi Pelajaran Situasional dengan OpenAI (BISBI Situasi - Backend)](#44-generasi-pelajaran-situasional-dengan-openai-bisbi-situasi---backend)
    - [4.5 Konversi Teks ke Audio (Text-to-Speech / BISBI Dengar - Backend)](#45-konversi-teks-ke-audio-text-to-speech--bisbi-dengar---backend)
    - [4.6 Penilaian Pelafalan (Pronunciation Assessment / BISBI Lafal - Backend)](#46-penilaian-pelafalan-pronunciation-assessment--bisbi-lafal---backend)
  - [5. Contoh Penggunaan dengan cURL](#5-contoh-penggunaan-dengan-curl)
  - [6. Struktur Respons](#6-struktur-respons)
  - [7. Catatan Tambahan](#7-catatan-tambahan)

## 1. Deskripsi Proyek

BISBI AI bertujuan untuk memberdayakan pemuda Indonesia, khususnya rentang usia 17-25 tahun, dengan keterampilan komunikasi bahasa Inggris yang praktis, kontekstual, dan hiper-personalisasi. Backend API ini mendukung fitur-fitur unggulan aplikasi BISBI AI seperti Kamus Visual Interaktif (BISBI Pindai), Pelajaran Situasional Dinamis (BISBI Situasi), output audio untuk pendengaran (BISBI Dengar), dan umpan balik pelafalan mendetail (BISBI Lafal).

## 2. Arsitektur Backend

*   **Platform:** Azure Functions (Serverless, Python)
*   **Layanan AI Utama (Microsoft Azure):**
    *   **Azure AI Vision:** Digunakan untuk deteksi objek pada fitur BISBI Pindai.
    *   **Azure OpenAI Service (Model GPT-4 Series atau setara):**
        *   Untuk analisis gambar objek dan generasi teks deskriptif bilingual pada fitur BISBI Pindai.
        *   Untuk generasi konten pelajaran situasional dinamis pada fitur BISBI Situasi.
    *   **Azure AI Speech:**
        *   Text-to-Speech (TTS) untuk generasi output audio pada fitur BISBI Dengar dan bagian lain aplikasi.
        *   Pronunciation Assessment untuk analisis dan umpan balik pelafalan pada fitur BISBI Lafal.
*   **Konfigurasi & Rahasia:** Dikelola melalui Application Settings di Azure Function App (yang dapat diintegrasikan dengan Azure Key Vault untuk keamanan lebih lanjut di lingkungan produksi).
*   **Monitoring:** Azure Application Insights.

## 3. Prasyarat Penggunaan API

*   **URL Basis API:** `https://bisbi-api.azurewebsites.net/api`
*   **Alat Pengujian API:** Postman, cURL, Insomnia, atau klien HTTP lainnya.
*   **Otorisasi:**
    *   Untuk versi MVP saat ini, beberapa endpoint mungkin diatur ke otorisasi `Anonymous` untuk kemudahan testing, sementara yang lain mungkin menggunakan `Function` key.
    *   Jika `Function` key diperlukan, sertakan header `x-functions-key: YOUR_FUNCTION_KEY` atau parameter query `code=YOUR_FUNCTION_KEY` dalam request Anda. Kunci fungsi dapat ditemukan di Azure Portal di bawah Function App -> Functions -> (Pilih Fungsi) -> Function Keys.
    *   Ini akan ditingkatkan dengan mekanisme otorisasi yang lebih robust (seperti Azure AD B2C dengan token) di fase pengembangan selanjutnya.

## 4. Endpoint API

Berikut adalah detail untuk setiap endpoint yang tersedia:

### 4.1 Status API (Health Check)

Menyediakan status dasar API, versi, dan pesan selamat datang.

*   **URL:** `/ApiHealthCheck` (Nama fungsi menjadi route jika tidak ada route custom di `function_app.py`)
*   **URL Lengkap (Contoh):** `https://bisbi-api.azurewebsites.net/api/ApiHealthCheck`
*   **Metode:** `GET`
*   **Otorisasi:** `Anonymous` (Umumnya)
*   **Respons Sukses (200 OK):**
    ```json
    {
      "status": "healthy",
      "message": "Welcome to BISBI AI API! All systems operational.",
      "version": "0.1.0-mvp", // Sesuaikan dengan versi dari kode Anda
      "timestamp": "2024-05-17T10:00:00Z", // Contoh timestamp
      "documentation": "https://github.com/dzakwanalifi/BISBI-API/blob/master/README.md" // Ganti dengan URL README Anda
    }
    ```

### 4.2 Deteksi Objek Visual (BISBI Pindai - Backend)

Menerima gambar dan mengembalikan daftar objek yang terdeteksi beserta bounding box-nya.

*   **URL:** `/DetectObjectsVisual`
*   **URL Lengkap (Contoh):** `https://bisbi-api.azurewebsites.net/api/DetectObjectsVisual`
*   **Metode:** `POST`
*   **Otorisasi:** `Function` (Rekomendasi) atau `Anonymous` (Untuk MVP)
*   **Request Body:** `multipart/form-data`
    *   **Field:** `image` (file: JPEG, PNG, dll.)
*   **Respons Sukses (200 OK):**
    ```json
    [
      {
        "objectName": "cat",
        "confidence": 0.95,
        "boundingBox": { "x": 150, "y": 200, "width": 120, "height": 100 }
      }
      // ... objek lain jika terdeteksi
    ]
    ```

### 4.3 Dapatkan Detail Objek Visual dengan OpenAI (BISBI Pindai - Backend)

Menerima gambar objek (sebaiknya yang sudah di-crop) dan mengembalikan detail deskriptif bilingual (nama objek, deskripsi, contoh kalimat, kata sifat terkait) yang dihasilkan oleh model vision Azure OpenAI.

*   **URL:** `/GetObjectDetailsVisual`
*   **URL Lengkap (Contoh):** `https://bisbi-api.azurewebsites.net/api/GetObjectDetailsVisual`
*   **Metode:** `POST`
*   **Otorisasi:** `Function` (Rekomendasi) atau `Anonymous` (Untuk MVP)
*   **Request Body:** `multipart/form-data`
    *   **Field:**
        *   `image`: (file) Gambar objek yang akan dianalisis.
        *   `targetLanguage` (opsional, teks, default: `en`): Kode bahasa target (misalnya, `en` untuk Inggris, `id` untuk Indonesia).
        *   `sourceLanguage` (opsional, teks, default: `id`): Kode bahasa sumber untuk terjemahan.
*   **Respons Sukses (200 OK):**
    ```json
    {
        "objectName": { "en": "Smartphone", "id": "Ponsel pintar" },
        "description": { "en": "A modern mobile device offering various functionalities...", "id": "Perangkat seluler modern yang menawarkan berbagai fungsionalitas..." },
        "exampleSentences": [
            { "en": "She uses her smartphone to call her friends.", "id": "Dia menggunakan ponsel pintarnya untuk menelepon teman-temannya." },
            { "en": "This smartphone has a great camera.", "id": "Ponsel pintar ini memiliki kamera yang bagus." }
        ],
        "relatedAdjectives": [
            { "en": "smart", "id": "pintar" },
            { "en": "new", "id": "baru" },
            { "en": "useful", "id": "berguna" }
        ]
    }
    ```

### 4.4 Generasi Pelajaran Situasional dengan OpenAI (BISBI Situasi - Backend)

Menerima deskripsi skenario dari pengguna dan menghasilkan paket konten pembelajaran bilingual (judul, kosakata kunci, frasa penting, tips tata bahasa) yang disesuaikan, menggunakan Azure OpenAI.

*   **URL:** `/GenerateLesson` (atau nama fungsi GenerateSituationalLesson Anda)
*   **URL Lengkap (Contoh):** `https://bisbi-api.azurewebsites.net/api/GenerateLesson`
*   **Metode:** `POST`
*   **Otorisasi:** `Function` (Rekomendasi) atau `Anonymous` (Untuk MVP)
*   **Request Headers:** `Content-Type: application/json`
*   **Request Body (JSON):**
    ```json
    {
      "scenarioDescription": "I want to ask for directions to the nearest train station in a new city.",
      "userNativeLanguageCode": "id",     // Default 'id' (Indonesia)
      "learningLanguageCode": "en",     // Default 'en' (Inggris)
      "userProficiencyLevel": "beginner" // Opsi: 'beginner', 'intermediate', 'advanced' (default: 'intermediate')
    }
    ```
*   **Respons Sukses (200 OK):**
    ```json
    {
        "scenarioTitle": { "en": "Asking for Directions to the Train Station", "id": "Meminta Petunjuk Arah ke Stasiun Kereta" },
        "vocabulary": [
            { "term": { "en": "Station", "id": "Stasiun" } },
            { "term": { "en": "Direction", "id": "Arah" } },
            { "term": { "en": "Nearest", "id": "Terdekat" } }
        ],
        "keyPhrases": [
            { "phrase": { "en": "Excuse me, how can I get to the nearest train station?", "id": "Permisi, bagaimana cara saya ke stasiun kereta terdekat?" } },
            { "phrase": { "en": "Is it far from here?", "id": "Apakah jauh dari sini?" } }
        ],
        "grammarTips": [
            {
                "tip": { "en": "Use question words like 'How', 'Where', 'Is it' to ask for information.", "id": "Gunakan kata tanya seperti 'Bagaimana', 'Di mana', 'Apakah' untuk meminta informasi." },
                "example": { "en": "Where is the ticket counter?", "id": "Di mana loket tiket?" }
            }
        ]
    }
    ```

### 4.5 Konversi Teks ke Audio (Text-to-Speech / BISBI Dengar - Backend)

Menerima teks, kode bahasa, dan nama suara (opsional), lalu mengembalikan data audio dalam format MP3 menggunakan Azure AI Speech.

*   **URL:** `/GetTTSAudio`
*   **URL Lengkap (Contoh):** `https://bisbi-api.azurewebsites.net/api/GetTTSAudio`
*   **Metode:** `POST`
*   **Otorisasi:** `Function` (Rekomendasi) atau `Anonymous` (Untuk MVP)
*   **Request Headers:** `Content-Type: application/json`
*   **Request Body (JSON):**
    ```json
    {
      "text": "Welcome to BISBI AI learning application.",
      "languageCode": "en-US", // Contoh: "en-US", "id-ID"
      "voiceName": "en-US-AvaMultilingualNeural" // Opsional, jika tidak ada, akan menggunakan default berdasarkan languageCode
    }
    ```
*   **Respons Sukses (200 OK):**
    *   **Content-Type:** `audio/mpeg`
    *   **Body:** Data biner dari file audio MP3.

### 4.6 Penilaian Pelafalan (Pronunciation Assessment / BISBI Lafal - Backend)

Menerima rekaman audio pengguna, teks referensi, kode bahasa, dan parameter penilaian opsional, lalu memberikan umpan balik pelafalan mendetail menggunakan Azure AI Speech.

*   **URL:** `/PronunciationAssessmentFunc`
*   **URL Lengkap (Contoh):** `https://bisbi-api.azurewebsites.net/api/PronunciationAssessmentFunc`
*   **Metode:** `POST`
*   **Otorisasi:** `Function` (Rekomendasi) atau `Anonymous` (Untuk MVP)
*   **Request Body:** `multipart/form-data`
    *   **Field:**
        *   `audio`: (file) File audio rekaman suara pengguna (format WAV direkomendasikan untuk kualitas terbaik, MP3 mungkin didukung tergantung konfigurasi SDK).
        *   `referenceText`: (teks) Teks yang seharusnya diucapkan oleh pengguna.
        *   `languageCode`: (teks) Kode bahasa dari audio dan teks referensi (contoh: `en-US`, `id-ID`).
        *   `gradingSystem` (opsional, teks, default: `HundredMark`): Sistem penilaian yang digunakan (`HundredMark`, `FivePoint`).
        *   `granularity` (opsional, teks, default: `Phoneme`): Tingkat detail umpan balik (`Phoneme` untuk per fonem, `Word` untuk per kata, `FullText` untuk keseluruhan).
*   **Contoh Request (menggunakan cURL):**
    ```bash
    curl -X POST \
      "https://bisbi-api.azurewebsites.net/api/PronunciationAssessmentFunc?code=YOUR_FUNCTION_KEY_IF_NEEDED" \
      -F "audio=@/path/to/your/speech.wav" \
      -F "referenceText=Hello world, welcome to BISBI AI" \
      -F "languageCode=en-US" \
      -F "granularity=Phoneme"
    ```
*   **Respons Sukses (200 OK):**
    Objek JSON yang berisi skor akurasi, kelancaran, kelengkapan, skor per kata, dan skor per fonem (jika diminta).
    ```json
    {
        "recognizedText": "Hello world welcome to BISBY AI", // Teks yang dikenali oleh STT
        "accuracyScore": 85.0,        // Skor akurasi keseluruhan
        "pronunciationScore": 78.0,   // Skor pelafalan keseluruhan (kualitas pengucapan)
        "completenessScore": 100.0,   // Seberapa banyak teks referensi yang diucapkan
        "fluencyScore": 70.0,         // Skor kelancaran berbicara
        "prosodyScore": 75.0,         // Skor prosodi (intonasi, ritme, stres), mungkin null jika tidak didukung/dihasilkan
        "words": [
            {
                "word": "Hello",
                "accuracyScore": 90.0,
                "errorType": "None", // Bisa "Mispronunciation", "Omission", "Insertion"
                "phonemes": [
                    { "phoneme": "h", "accuracyScore": 95.0 },
                    { "phoneme": "ə", "accuracyScore": 80.0 }, // Contoh, fonem bisa berbeda
                    { "phoneme": "l", "accuracyScore": 92.0 },
                    { "phoneme": "oʊ", "accuracyScore": 88.0 }
                ]
            },
            // ... detail untuk kata-kata lainnya ...
        ]
    }
    ```

*   **Respons Error Umum:**
    *   `400 Bad Request`: Input tidak valid (misalnya, field hilang, format salah).
    *   `401 Unauthorized`: Kunci fungsi tidak valid atau hilang (jika otorisasi `Function`).
    *   `500 Internal Server Error`: Masalah di sisi server atau saat berkomunikasi dengan layanan Azure AI. Periksa log Application Insights untuk detail.

## 5. Contoh Penggunaan dengan cURL

Contoh cURL spesifik disediakan di bawah setiap deskripsi endpoint di atas. Ingat untuk:
*   Mengganti `bisbi-api.azurewebsites.net` dengan URL basis Anda jika berbeda.
*   Menambahkan `?code=YOUR_FUNCTION_KEY` ke URL atau header `x-functions-key: YOUR_FUNCTION_KEY` jika endpoint memerlukan otorisasi `Function`.
*   Mengganti `/path/to/your/file` dengan path file lokal yang benar saat mengunggah file.
*   Saat menguji endpoint TTS, Anda bisa menyimpan output audio ke file, misalnya dengan menambahkan `--output audio.mp3` pada perintah cURL.

## 6. Struktur Respons

Struktur JSON respons detail telah dijelaskan untuk setiap endpoint yang mengembalikan JSON. Endpoint TTS (`/GetTTSAudio`) mengembalikan data audio biner (`audio/mpeg`).

## 7. Catatan Tambahan

*   **Status Proyek:** Backend ini aktif dikembangkan sebagai bagian dari Minimum Viable Product (MVP) BISBI AI. Fitur dan endpoint dapat berkembang.
*   **Keamanan:** Otorisasi endpoint akan terus ditinjau dan ditingkatkan seiring perkembangan proyek menuju produksi.
*   **Penanganan Error:** Pesan error dasar HTTP disediakan. Untuk debugging lebih lanjut, log server terperinci tersedia melalui Azure Application Insights yang terintegrasi dengan Function App `bisbi-api`.
*   **Batasan dan Biaya Layanan Azure:** Setiap layanan Azure yang digunakan (Azure AI Vision, Azure OpenAI Service, Azure AI Speech) memiliki batasan penggunaan (rate limits, kuota) dan implikasi biaya sendiri sesuai dengan pricing tier yang dipilih dan volume penggunaan. Kelola ini melalui Azure Portal.
*   **Versi Kode:** Lihat `ApiHealthCheck` untuk versi API saat ini.

---
Untuk pertanyaan, masalah, atau kontribusi, silakan buka *issue* di repositori GitHub proyek ini (jika Anda telah membuatnya publik dan ingin membagikan URL-nya).
Contoh: `https://github.com/dzakwanalifi/BISBI-API` (Ganti dengan URL repositori Anda yang sebenarnya).