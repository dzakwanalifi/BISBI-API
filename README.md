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

-   **Platform:** Azure Functions (Serverless, Python)
-   **Layanan AI Utama:**
    -   **Hugging Face Inference API (Model facebook/detr-resnet-50 atau serupa):** Digunakan untuk deteksi objek pada fitur BISBI Pindai. Dijalankan melalui provider "hf-inference" dengan model Pay-As-You-Go.
    -   **Azure OpenAI Service (Model GPT-4 Series atau setara):**
        -   Untuk analisis gambar objek dan generasi teks deskriptif bilingual pada fitur BISBI Pindai (setelah objek dideteksi).
        -   Untuk generasi konten pelajaran situasional dinamis pada fitur BISBI Situasi.
    -   **Azure AI Speech:**
        -   Text-to-Speech (TTS) untuk generasi output audio pada fitur BISBI Dengar dan bagian lain aplikasi.
        -   Pronunciation Assessment untuk analisis dan umpan balik pelafalan pada fitur BISBI Lafal.
-   **Konfigurasi & Rahasia:** Dikelola melalui Application Settings di Azure Function App (yang dapat diintegrasikan dengan Azure Key Vault untuk keamanan lebih lanjut di lingkungan produksi). Ini termasuk HF_API_TOKEN untuk akses ke Hugging Face API.
-   **Monitoring:** Azure Application Insights.

## 3. Prasyarat Penggunaan API

*   **URL Basis API:** `https://bisbi-api.azurewebsites.net/api`
*   **Alat Pengujian API:** Postman, cURL, Insomnia, atau klien HTTP lainnya.
*   **Otorisasi:**
    *   Sebagian besar endpoint API ini diamankan menggunakan otorisasi level **`Function`**. Ini berarti Anda memerlukan **Kunci Fungsi (Function Key)** atau **Kunci Host (App Key)** untuk mengaksesnya.
    *   Endpoint `ApiHealthCheck` diatur ke otorisasi `Anonymous` dan tidak memerlukan kunci.
    *   **Cara Mendapatkan Kunci:**
        *   Buka Azure Portal dan navigasi ke Function App `bisbi-api` Anda.
        *   Untuk **Kunci Host `default`** (direkomendasikan untuk akses klien ke beberapa fungsi):
            *   Di menu Function App, di bawah "Settings", pilih **App keys**.
            *   Salin nilai kunci `default`.
        *   Untuk **Kunci Fungsi spesifik** (jika Anda ingin kunci per fungsi):
            *   Di menu Function App, di bawah "Functions", pilih **Functions**.
            *   Klik pada nama fungsi yang diinginkan (misalnya, `DetectObjectsVisual_handler`).
            *   Di menu fungsi tersebut, pilih **Function Keys**.
            *   Salin nilai kunci `default` untuk fungsi tersebut.
    *   **Cara Menggunakan Kunci dalam Request:**
        *   **Sebagai parameter query string (direkomendasikan untuk cURL & pengujian cepat):** Tambahkan `?code=NILAI_KUNCI_ANDA` ke akhir URL endpoint.
        *   **Sebagai header HTTP:** Sertakan header `x-functions-key: NILAI_KUNCI_ANDA` dalam request Anda.
    *   *Catatan: Mekanisme otorisasi yang lebih robust seperti Azure AD B2C dengan token OAuth2 dapat dipertimbangkan untuk fase pengembangan selanjutnya.*

## 4. Endpoint API

Berikut adalah detail untuk setiap endpoint yang tersedia:

### 4.1 Status API (Health Check)

Menyediakan status dasar API, versi, dan pesan selamat datang.

*   **URL:** `/ApiHealthCheck`
*   **URL Lengkap (Contoh):** `https://bisbi-api.azurewebsites.net/api/ApiHealthCheck`
*   **Metode:** `GET`
*   **Otorisasi:** `Anonymous` (Tidak memerlukan kunci)
*   **Respons Sukses (200 OK):**
    ```json
    {
      "status": "healthy",
      "message": "Welcome to BISBI AI API! All systems operational.",
      "version": "0.1.0-mvp",
      "timestamp": "2024-05-25T18:00:00Z",
      "documentation": "https://github.com/dzakwanalifi/BISBI-API/blob/master/README.md"
    }
    ```

### 4.2 Deteksi Objek Visual (BISBI Pindai - Backend)

Menerima gambar dan mengembalikan daftar objek yang terdeteksi beserta bounding box-nya. Fungsionalitas ini ditenagai oleh model deteksi objek dari Hugging Face (misalnya, facebook/detr-resnet-50) yang diakses melalui Inference API mereka.

-   **URL:** `/DetectObjectsVisual`
-   **URL Lengkap (Contoh dengan Kunci):** `https://bisbi-api.azurewebsites.net/api/DetectObjectsVisual?code=NILAI_KUNCI_ANDA`
-   **Metode:** `POST`
-   **Otorisasi:** `Function` (Memerlukan kunci)
-   **Request Body:** `multipart/form-data`
    -   **Field:** `image` (file: JPEG, PNG, dll.)
-   **Respons Sukses (200 OK):**

    ```json
    [
      {
        "objectName": "cat",
        "confidence": 0.95,
        "boundingBox": { "x": 150, "y": 200, "width": 120, "height": 100 }
      }
    ]
    ```
    *Catatan: Akurasi dan label objectName akan bergantung pada model yang digunakan di backend Hugging Face.*

### 4.3 Dapatkan Detail Objek Visual dengan OpenAI (BISBI Pindai - Backend)

Menerima gambar objek (sebaiknya yang sudah di-crop) dan mengembalikan detail deskriptif bilingual.

*   **URL:** `/GetObjectDetailsVisual`
*   **URL Lengkap (Contoh dengan Kunci):** `https://bisbi-api.azurewebsites.net/api/GetObjectDetailsVisual?code=NILAI_KUNCI_ANDA`
*   **Metode:** `POST`
*   **Otorisasi:** `Function` (Memerlukan kunci)
*   **Request Body:** `multipart/form-data`
    *   **Field:**
        *   `image`: (file) Gambar objek yang akan dianalisis.
        *   `targetLanguage` (opsional, teks, default: `en`)
        *   `sourceLanguage` (opsional, teks, default: `id`)
*   **Respons Sukses (200 OK):**
    ```json
    {
        "objectName": { "en": "Smartphone", "id": "Ponsel pintar" },
        "description": { "en": "A modern mobile device...", "id": "Perangkat seluler modern..." },
        "exampleSentences": [
            { "en": "She uses her smartphone...", "id": "Dia menggunakan ponsel pintarnya..." }
        ],
        "relatedAdjectives": [
            { "en": "smart", "id": "pintar" }
        ]
    }
    ```

### 4.4 Generasi Pelajaran Situasional dengan OpenAI (BISBI Situasi - Backend)

Menerima deskripsi skenario dan menghasilkan konten pembelajaran bilingual.

*   **URL:** `/GenerateLesson`
*   **URL Lengkap (Contoh dengan Kunci):** `https://bisbi-api.azurewebsites.net/api/GenerateLesson?code=NILAI_KUNCI_ANDA`
*   **Metode:** `POST`
*   **Otorisasi:** `Function` (Memerlukan kunci)
*   **Request Headers:** `Content-Type: application/json`
*   **Request Body (JSON):**
    ```json
    {
      "scenarioDescription": "I want to ask for directions...",
      "userNativeLanguageCode": "id",
      "learningLanguageCode": "en",
      "userProficiencyLevel": "beginner"
    }
    ```
*   **Respons Sukses (200 OK):**
    ```json
    {
        "scenarioTitle": { "en": "Asking for Directions...", "id": "Meminta Petunjuk Arah..." },
        "vocabulary": [
            { "term": { "en": "Station", "id": "Stasiun" } }
        ],
        "keyPhrases": [
            { "phrase": { "en": "Excuse me, how can I get to...?", "id": "Permisi, bagaimana cara saya ke...?" } }
        ],
        "grammarTips": [
            {
                "tip": { "en": "Use question words...", "id": "Gunakan kata tanya..." },
                "example": { "en": "Where is...?", "id": "Di mana...?" }
            }
        ]
    }
    ```

### 4.5 Konversi Teks ke Audio (Text-to-Speech / BISBI Dengar - Backend)

Menerima teks dan mengembalikan data audio MP3.

*   **URL:** `/GetTTSAudio`
*   **URL Lengkap (Contoh dengan Kunci):** `https://bisbi-api.azurewebsites.net/api/GetTTSAudio?code=NILAI_KUNCI_ANDA`
*   **Metode:** `POST`
*   **Otorisasi:** `Function` (Memerlukan kunci)
*   **Request Headers:** `Content-Type: application/json`
*   **Request Body (JSON):**
    ```json
    {
      "text": "Welcome to BISBI AI learning application.",
      "languageCode": "en-US",
      "voiceName": "en-US-AvaMultilingualNeural" 
    }
    ```
*   **Respons Sukses (200 OK):**
    *   **Content-Type:** `audio/mpeg`
    *   **Body:** Data biner dari file audio MP3.

### 4.6 Penilaian Pelafalan (Pronunciation Assessment / BISBI Lafal - Backend)

Menerima rekaman audio dan teks referensi, memberikan umpan balik pelafalan.

*   **URL:** `/PronunciationAssessmentFunc`
*   **URL Lengkap (Contoh dengan Kunci):** `https://bisbi-api.azurewebsites.net/api/PronunciationAssessmentFunc?code=NILAI_KUNCI_ANDA`
*   **Metode:** `POST`
*   **Otorisasi:** `Function` (Memerlukan kunci)
*   **Request Body:** `multipart/form-data`
    *   **Field:**
        *   `audio`: (file) File audio pengguna.
        *   `referenceText`: (teks) Teks referensi.
        *   `languageCode`: (teks) Kode bahasa (misal: `en-US`, `id-ID`).
        *   `gradingSystem` (opsional, default: `HundredMark`)
        *   `granularity` (opsional, default: `Phoneme`)
*   **Respons Sukses (200 OK):**
    ```json
    {
        "recognizedText": "Hello world welcome to BISBY AI",
        "accuracyScore": 85.0,
        "pronunciationScore": 78.0,
        "completenessScore": 100.0,
        "fluencyScore": 70.0,
        "prosodyScore": 75.0,
        "words": [
            {
                "word": "Hello",
                "accuracyScore": 90.0,
                "errorType": "None",
                "phonemes": [
                    { "phoneme": "h", "accuracyScore": 95.0 }
                ]
            }
        ]
    }
    ```

*   **Respons Error Umum:**
    *   `400 Bad Request`: Input tidak valid.
    *   `401 Unauthorized`: Kunci fungsi tidak valid atau hilang.
    *   `500 Internal Server Error`: Masalah di sisi server.

## 5. Contoh Penggunaan dengan cURL

Berikut adalah contoh penggunaan cURL untuk beberapa endpoint. Ingat untuk mengganti `NILAI_KUNCI_ANDA` dengan kunci fungsi (App Key `default` direkomendasikan) yang Anda dapatkan dari Azure Portal.

*   **ApiHealthCheck (Tanpa Kunci):**
    ```bash
    curl "https://bisbi-api.azurewebsites.net/api/ApiHealthCheck"
    ```

*   **DetectObjectsVisual:**
    ```bash
    curl -X POST \
      "https://bisbi-api.azurewebsites.net/api/DetectObjectsVisual?code=NILAI_KUNCI_ANDA" \
      -F "image=@/path/to/your/image.jpg"
    ```
    Atau dengan header:
    ```bash
    curl -X POST \
      "https://bisbi-api.azurewebsites.net/api/DetectObjectsVisual" \
      -H "x-functions-key: NILAI_KUNCI_ANDA" \
      -F "image=@/path/to/your/image.jpg"
    ```

*   **GenerateLesson:**
    ```bash
    curl -X POST \
      "https://bisbi-api.azurewebsites.net/api/GenerateLesson?code=NILAI_KUNCI_ANDA" \
      -H "Content-Type: application/json" \
      -d '{
            "scenarioDescription": "Ordering food at a restaurant",
            "userNativeLanguageCode": "id",
            "learningLanguageCode": "en",
            "userProficiencyLevel": "intermediate"
          }'
    ```

*   **GetTTSAudio (Simpan output ke file):**
    ```bash
    curl -X POST \
      "https://bisbi-api.azurewebsites.net/api/GetTTSAudio?code=NILAI_KUNCI_ANDA" \
      -H "Content-Type: application/json" \
      -d '{
            "text": "Hello, this is a test.",
            "languageCode": "en-US"
          }' \
      --output audio_output.mp3
    ```

*   **PronunciationAssessmentFunc:**
    ```bash
    curl -X POST \
      "https://bisbi-api.azurewebsites.net/api/PronunciationAssessmentFunc?code=NILAI_KUNCI_ANDA" \
      -F "audio=@/path/to/your/speech.wav" \
      -F "referenceText=Hello world" \
      -F "languageCode=en-US"
    ```

## 6. Struktur Respons

Struktur JSON respons detail telah dijelaskan untuk setiap endpoint yang mengembalikan JSON. Endpoint TTS (`/GetTTSAudio`) mengembalikan data audio biner (`audio/mpeg`).

## 7. Catatan Tambahan

*   **Status Proyek:** Backend ini aktif dikembangkan sebagai bagian dari Minimum Viable Product (MVP) BISBI AI.
*   **Keamanan:** Penggunaan kunci fungsi adalah langkah awal. Pertimbangkan mekanisme otorisasi yang lebih kuat untuk produksi.
*   **Penanganan Error:** Pesan error dasar HTTP disediakan. Gunakan Application Insights untuk log server terperinci.
*   **Batasan dan Biaya Layanan Azure:** Kelola batasan dan biaya layanan Azure AI yang digunakan melalui Azure Portal.
*   **Versi Kode:** Lihat `ApiHealthCheck` untuk versi API saat ini.

---
Untuk pertanyaan, masalah, atau kontribusi, silakan buka *issue* di repositori GitHub proyek ini.