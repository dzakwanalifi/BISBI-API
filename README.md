# Lensa Bahasa - API Backend

Selamat datang di dokumentasi API Backend untuk Lensa Bahasa, sebuah aplikasi pembelajaran bahasa Inggris berbasis AI untuk pemuda Indonesia. API ini menyediakan fungsionalitas inti yang ditenagai oleh Azure AI Services untuk mendukung pengalaman belajar yang interaktif dan personal.

**API ini telah di-deploy dan dapat diakses melalui Azure Function App.**

## Daftar Isi

- [Lensa Bahasa - API Backend](#lensa-bahasa---api-backend)
  - [Daftar Isi](#daftar-isi)
  - [1. Deskripsi Proyek](#1-deskripsi-proyek)
  - [2. Arsitektur Backend](#2-arsitektur-backend)
  - [3. Prasyarat Penggunaan API](#3-prasyarat-penggunaan-api)
  - [4. Endpoint API](#4-endpoint-api)
    - [4.1 Status API (Health Check)](#41-status-api-health-check)
    - [4.2 Deteksi Objek Visual](#42-deteksi-objek-visual)
    - [4.3 Dapatkan Detail Objek Visual (dengan OpenAI)](#43-dapatkan-detail-objek-visual-dengan-openai)
    - [4.4 Generasi Pelajaran Situasional (dengan OpenAI)](#44-generasi-pelajaran-situasional-dengan-openai)
    - [4.5 Konversi Teks ke Audio (Text-to-Speech)](#45-konversi-teks-ke-audio-text-to-speech)
    - [4.6 Penilaian Pelafalan (Pronunciation Assessment)](#46-penilaian-pelafalan-pronunciation-assessment)
  - [5. Contoh Penggunaan dengan cURL](#5-contoh-penggunaan-dengan-curl)
  - [6. Struktur Respons](#6-struktur-respons)
  - [7. Catatan Tambahan](#7-catatan-tambahan)

## 1. Deskripsi Proyek

Lensa Bahasa bertujuan untuk memberdayakan pemuda Indonesia dengan keterampilan komunikasi bahasa Inggris yang praktis, kontekstual, dan personal. Backend API ini mendukung fitur-fitur seperti kamus visual interaktif, pelajaran situasional dinamis, output audio, dan umpan balik pelafalan.

## 2. Arsitektur Backend

*   **Platform:** Azure Functions (Serverless, Python)
*   **Layanan AI Utama:**
    *   Azure AI Vision (untuk deteksi objek)
    *   Azure OpenAI Service (GPT-4.1 atau setara, untuk analisis gambar objek, generasi teks deskriptif, dan generasi pelajaran situasional)
    *   Azure AI Speech (Text-to-Speech untuk generasi audio, Speech-to-Text & Pronunciation Assessment untuk penilaian pelafalan)
*   **Konfigurasi & Rahasia:** Dikelola melalui Azure Key Vault dan Application Settings di Azure Function App.

## 3. Prasyarat Penggunaan API

*   **URL Basis API:** `https://lensabahasa-api.azurewebsites.net/api` (Ganti `lensabahasa-api` dengan nama Function App Anda jika berbeda).
*   **Alat Pengujian API:** Postman, cURL, atau klien HTTP lainnya.
*   Tidak ada kunci API khusus yang diperlukan untuk memanggil endpoint ini saat ini (otorisasi diatur ke `Anonymous`). Ini mungkin berubah di masa depan.

## 4. Endpoint API

Berikut adalah detail untuk setiap endpoint yang tersedia:

### 4.1 Status API (Health Check)

Menyediakan status dasar API, versi, dan pesan selamat datang.

*   **URL:** `/health`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/health`
*   **Metode:** `GET`
*   **Respons Sukses (200 OK):**
    ```json
    {
      "status": "healthy",
      "message": "Welcome to Lensa Bahasa API! All systems operational.",
      "version": "0.1.0-mvp",
      "timestamp": "2025-05-16T08:00:00Z",
      "documentation": "https://github.com/dzakwanalifi/LensaBahasa-API-Trial/blob/master/README.md"
    }
    ```

### 4.2 Deteksi Objek Visual

Menerima gambar dan mengembalikan daftar objek yang terdeteksi.

*   **URL:** `/visual/detect-objects`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/visual/detect-objects`
*   **Metode:** `POST`
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
    ]
    ```

### 4.3 Dapatkan Detail Objek Visual (dengan OpenAI)

Menerima gambar objek yang sudah di-crop dan mengembalikan detail deskriptif bilingual.

*   **URL:** `/visual/get-object-details`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/visual/get-object-details`
*   **Metode:** `POST`
*   **Request Body:** `multipart/form-data`
    *   **Field:**
        *   `image`: (file) Gambar objek yang sudah di-crop.
        *   `targetLanguage` (opsional, teks, default: `en`): Kode bahasa target (misalnya, `en`, `id`).
        *   `sourceLanguage` (opsional, teks, default: `id`): Kode bahasa sumber untuk terjemahan.
*   **Respons Sukses (200 OK):**
    ```json
    {
        "objectName": { "en": "Smartphone", "id": "Ponsel pintar" },
        "description": { "en": "A modern smartphone...", "id": "Ponsel pintar modern..." },
        "exampleSentences": [ { "en": "I use my smartphone daily.", "id": "Saya menggunakan ponsel pintar setiap hari." } ],
        "relatedAdjectives": [ { "en": "smart", "id": "pintar" } ]
    }
    ```

### 4.4 Generasi Pelajaran Situasional (dengan OpenAI)

Menerima deskripsi skenario dan menghasilkan konten pembelajaran bilingual (kosakata, frasa, tips grammar).

*   **URL:** `/lessons/generate-situational`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/lessons/generate-situational`
*   **Metode:** `POST`
*   **Request Headers:** `Content-Type: application/json`
*   **Request Body (JSON):**
    ```json
    {
      "scenarioDescription": "I want to order food at a fancy restaurant for a birthday dinner.",
      "userNativeLanguageCode": "id",     // Default 'id'
      "learningLanguageCode": "en",     // Default 'en'
      "userProficiencyLevel": "intermediate" // Default 'intermediate', opsi: 'beginner', 'intermediate', 'advanced'
    }
    ```
*   **Respons Sukses (200 OK):**
    ```json
    {
        "scenarioTitle": { "en": "Ordering Food at a Fancy Restaurant", "id": "Memesan Makanan di Restoran Mewah" },
        "vocabulary": [
            { "term": { "en": "Reservation", "id": "Reservasi" } },
            { "term": { "en": "Appetizer", "id": "Makanan Pembuka" } }
        ],
        "keyPhrases": [
            { "phrase": { "en": "I would like to make a reservation.", "id": "Saya ingin membuat reservasi." } }
        ],
        "grammarTips": [
            {
                "tip": { "en": "Use polite forms like 'Could I...' or 'May I...'", "id": "Gunakan bentuk sopan seperti 'Bisakah saya...' atau 'Bolehkah saya...'" },
                "example": { "en": "Could I see the menu, please?", "id": "Bisakah saya melihat menunya?" }
            }
        ]
    }
    ```

### 4.5 Konversi Teks ke Audio (Text-to-Speech)

Menerima teks dan kode bahasa, mengembalikan data audio (MP3).

*   **URL:** `/audio/text-to-speech`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/audio/text-to-speech`
*   **Metode:** `POST`
*   **Request Headers:** `Content-Type: application/json`
*   **Request Body (JSON):**
    ```json
    {
      "text": "Hello Language Lens",
      "languageCode": "en-US",
      "voiceName": "en-US-AvaMultilingualNeural" // Opsional
    }
    ```
*   **Respons Sukses (200 OK):**
    *   **Content-Type:** `audio/mpeg`
    *   **Body:** Data biner dari file audio MP3.

### 4.6 Penilaian Pelafalan (Pronunciation Assessment)

Menerima rekaman audio pengguna, teks referensi, dan bahasa, lalu memberikan umpan balik pelafalan.

*   **URL:** `/audio/assess-pronunciation`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/audio/assess-pronunciation`
*   **Metode:** `POST`
*   **Request Body:** `multipart/form-data`
    *   **Field:**
        *   `audio`: (file) File audio rekaman suara pengguna (WAV direkomendasikan, MP3 mungkin didukung).
        *   `referenceText`: (teks) Teks yang seharusnya diucapkan.
        *   `languageCode`: (teks) Kode bahasa (misalnya, `en-US`).
        *   `gradingSystem` (opsional, teks, default: `HundredMark`): Sistem penilaian (`HundredMark`, `FivePoint`).
        *   `granularity` (opsional, teks, default: `Phoneme`): Detail umpan balik (`Phoneme`, `Word`, `FullText`).
*   **Contoh Request (menggunakan cURL):**
    ```bash
    curl -X POST \
      https://lensabahasa-api.azurewebsites.net/api/audio/assess-pronunciation \
      -F "audio=@/path/to/your/speech.wav" \
      -F "referenceText=Hello world" \
      -F "languageCode=en-US"
    ```
*   **Respons Sukses (200 OK):**
    Objek JSON berisi skor dan detail penilaian.
    ```json
    {
        "recognizedText": "Hello world",
        "accuracyScore": 85.0,
        "pronunciationScore": 78.0,
        "completenessScore": 100.0,
        "fluencyScore": 70.0,
        "prosodyScore": null, // Mungkin null
        "words": [
            {
                "word": "Hello",
                "accuracyScore": 90.0,
                "errorType": "None", // Bisa "Mispronunciation", "Omission", "Insertion"
                "phonemes": [
                    { "phoneme": "h", "accuracyScore": 95.0 },
                    { "phoneme": "eh", "accuracyScore": 80.0 },
                    // ... fonem lainnya
                ]
            },
            // ... kata lainnya
        ]
    }
    ```

*   **Respons Error:**
    *   `400 Bad Request`: Input tidak valid.
    *   `500 Internal Server Error`: Masalah di sisi server atau layanan Speech.

## 5. Contoh Penggunaan dengan cURL

Contoh cURL spesifik disediakan di bawah setiap deskripsi endpoint di atas. Ingat untuk:
*   Mengganti URL basis jika nama Function App Anda berbeda.
*   Mengganti `/path/to/your/file` dengan path file lokal yang benar saat mengunggah file.
*   Menyimpan output audio dari endpoint TTS ke file (misalnya, menggunakan `--output audio.mp3` di cURL).

## 6. Struktur Respons

Struktur JSON respons detail telah dijelaskan untuk setiap endpoint yang mengembalikan JSON. Endpoint TTS mengembalikan data audio biner.

## 7. Catatan Tambahan

*   **Status Proyek:** Backend ini aktif dikembangkan sebagai bagian dari MVP Lensa Bahasa.
*   **Keamanan:** Endpoint saat ini `Anonymous`. Keamanan akan ditingkatkan.
*   **Penanganan Error:** Pesan error dasar disediakan. Log server di Azure Application Insights dapat memberikan detail lebih lanjut.
*   **Batasan Layanan Azure:** Setiap layanan Azure yang digunakan (AI Vision, OpenAI, AI Speech) memiliki batasan penggunaan dan harga sendiri sesuai dengan tier yang dipilih.
*   **Repositori Kode Frontend (jika ada):** [Link ke repo frontend Anda]
*   **Informasi Kontak/Kontribusi:** [Cara berkontribusi atau menghubungi Anda]

---
Untuk pertanyaan atau masalah, silakan buka *issue* di repositori GitHub ini (jika Anda membuatnya publik): `https://github.com/dzakwanalifi/LensaBahasa-API-Trial`