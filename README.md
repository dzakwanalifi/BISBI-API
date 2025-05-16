# Lensa Bahasa - API Backend

Selamat datang di dokumentasi API Backend untuk Lensa Bahasa, sebuah aplikasi pembelajaran bahasa Inggris berbasis AI untuk pemuda Indonesia. API ini menyediakan fungsionalitas inti yang ditenagai oleh Azure AI Services.

**API ini telah di-deploy dan dapat diakses melalui Azure Function App.**

## Daftar Isi

- [Lensa Bahasa - API Backend](#lensa-bahasa---api-backend)
  - [Daftar Isi](#daftar-isi)
  - [1. Deskripsi Proyek](#1-deskripsi-proyek)
  - [2. Arsitektur Backend](#2-arsitektur-backend)
  - [3. Prasyarat Penggunaan API](#3-prasyarat-penggunaan-api)
  - [4. Endpoint API](#4-endpoint-api)
    - [4.1 Deteksi Objek Visual](#41-deteksi-objek-visual)
    - [4.2 Dapatkan Detail Objek Visual (dengan OpenAI)](#42-dapatkan-detail-objek-visual-dengan-openai)
    - [4.3 Konversi Teks ke Audio (Text-to-Speech)](#43-konversi-teks-ke-audio-text-to-speech)
  - [5. Contoh Penggunaan dengan cURL](#5-contoh-penggunaan-dengan-curl)
  - [6. Struktur Respons](#6-struktur-respons)
  - [7. Catatan Tambahan](#7-catatan-tambahan)

## 1. Deskripsi Proyek

Lensa Bahasa bertujuan untuk memberdayakan pemuda Indonesia dengan keterampilan komunikasi bahasa Inggris yang praktis, kontekstual, dan personal. Backend API ini mendukung fitur-fitur seperti kamus visual interaktif, pelajaran situasional (akan datang), dan output audio.

## 2. Arsitektur Backend

*   **Platform:** Azure Functions (Serverless, Python)
*   **Layanan AI Utama:**
    *   Azure AI Vision (untuk deteksi objek)
    *   Azure OpenAI Service (GPT-4.1 atau setara, untuk analisis gambar objek dan generasi teks deskriptif)
    *   Azure AI Speech (Text-to-Speech untuk generasi audio)
*   **Konfigurasi & Rahasia:** Dikelola melalui Azure Key Vault dan Application Settings di Azure Function App.

## 3. Prasyarat Penggunaan API

*   **URL Basis API:** `https://lensabahasa-api.azurewebsites.net/api` (Ganti `lensabahasa-api` dengan nama Function App Anda jika berbeda).
*   **Alat Pengujian API:** Postman, cURL, atau klien HTTP lainnya.
*   Tidak ada kunci API khusus yang diperlukan untuk memanggil endpoint ini saat ini (otorisasi diatur ke `Anonymous`). Ini mungkin berubah di masa depan untuk meningkatkan keamanan.

## 4. Endpoint API

Berikut adalah detail untuk setiap endpoint yang tersedia:

### 4.1 Deteksi Objek Visual

Endpoint ini menerima gambar dan mengembalikan daftar objek yang terdeteksi beserta bounding box dan skor kepercayaannya.

*   **URL:** `/visual/detect-objects`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/visual/detect-objects`
*   **Metode:** `POST`
*   **Request Body:** `multipart/form-data`
    *   **Field:**
        *   `image`: (file) File gambar yang akan dianalisis (format yang didukung: JPEG, PNG, GIF, BMP).

*   **Contoh Request (menggunakan cURL):**
    ```bash
    curl -X POST \
      https://lensabahasa-api.azurewebsites.net/api/visual/detect-objects \
      -F "image=@/path/to/your/image.jpg"
    ```
    (Ganti `/path/to/your/image.jpg` dengan path sebenarnya ke file gambar Anda).

*   **Respons Sukses (200 OK):**
    Array JSON berisi objek-objek yang terdeteksi.
    ```json
    [
      {
        "objectName": "cat",
        "confidence": 0.95,
        "boundingBox": {
          "x": 150,
          "y": 200,
          "width": 120,
          "height": 100
        }
      },
      // ... objek lain
    ]
    ```
    Jika tidak ada objek terdeteksi, akan mengembalikan array kosong `[]`.

*   **Respons Error:**
    *   `400 Bad Request`: Jika field `image` tidak ada atau ada masalah dengan format request.
        ```json
        { "error": "Harap unggah file gambar dengan field name 'image'." }
        ```
    *   `500 Internal Server Error`: Jika ada masalah di sisi server.
        ```json
        { "error": "Terjadi kesalahan pada server saat memproses gambar." }
        ```

### 4.2 Dapatkan Detail Objek Visual (dengan OpenAI)

Endpoint ini menerima gambar objek tunggal yang sudah di-crop dan mengembalikan detail deskriptif bilingual (Inggris dan Indonesia) tentang objek tersebut menggunakan Azure OpenAI.

*   **URL:** `/visual/get-object-details`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/visual/get-object-details`
*   **Metode:** `POST`
*   **Request Body:** `multipart/form-data`
    *   **Field:**
        *   `image`: (file) File gambar objek tunggal yang sudah di-crop.
        *   `targetLanguage` (opsional, teks): Kode bahasa target untuk output utama (default: `en`). Contoh: `en`, `id`.
        *   `sourceLanguage` (opsional, teks): Kode bahasa sumber/native untuk terjemahan (default: `id`). Contoh: `id`, `en`.

*   **Contoh Request (menggunakan cURL):**
    ```bash
    curl -X POST \
      https://lensabahasa-api.azurewebsites.net/api/visual/get-object-details \
      -F "image=@/path/to/your/cropped_object.jpg" \
      -F "targetLanguage=en" \
      -F "sourceLanguage=id"
    ```

*   **Respons Sukses (200 OK):**
    Objek JSON tunggal berisi detail objek.
    ```json
    {
        "objectName": {
            "en": "Smartphone displaying a conversation card game app",
            "id": "Ponsel pintar yang menampilkan aplikasi permainan kartu percakapan"
        },
        "description": {
            "en": "The image shows a person holding a smartphone with an app called 'kenallebih' open on the screen...",
            "id": "Gambar ini menunjukkan seseorang memegang ponsel pintar dengan aplikasi bernama 'kenallebih' terbuka di layar..."
        },
        "exampleSentences": [
            {
                "en": "She used her smartphone to play a conversation card game with her friends.",
                "id": "Dia menggunakan ponsel pintarnya untuk bermain permainan kartu percakapan bersama teman-temannya."
            }
        ],
        "relatedAdjectives": [
            {
                "en": "interactive",
                "id": "interaktif"
            }
        ]
    }
    ```

*   **Respons Error:**
    *   `400 Bad Request`: Jika input tidak valid.
    *   `500 Internal Server Error`: Jika ada masalah di sisi server atau dengan panggilan ke OpenAI.

### 4.3 Konversi Teks ke Audio (Text-to-Speech)

Endpoint ini menerima teks dan kode bahasa, lalu mengembalikan data audio (MP3) dari teks tersebut.

*   **URL:** `/audio/text-to-speech`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/audio/text-to-speech`
*   **Metode:** `POST`
*   **Request Headers:**
    *   `Content-Type: application/json`
*   **Request Body (JSON):**
    ```json
    {
      "text": "Halo Lensa Bahasa",
      "languageCode": "id-ID",
      "voiceName": "id-ID-ArdiNeural" // Opsional
    }
    ```
    Atau untuk bahasa Inggris:
    ```json
    {
      "text": "Hello Language Lens",
      "languageCode": "en-US",
      "voiceName": "en-US-AvaNeural" // Opsional
    }
    ```
    *   `text`: Teks yang akan dikonversi.
    *   `languageCode`: Kode bahasa (misalnya, `id-ID`, `en-US`). Lihat [Dokumentasi Azure Speech Language Support](https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support?tabs=tts#neural-voices) untuk kode dan nama suara yang didukung.
    *   `voiceName`: (Opsional) Nama spesifik suara neural yang diinginkan. Jika tidak disertakan, default akan dipilih berdasarkan `languageCode`.

*   **Contoh Request (menggunakan cURL):**
    ```bash
    curl -X POST \
      https://lensabahasa-api.azurewebsites.net/api/audio/text-to-speech \
      -H "Content-Type: application/json" \
      -d '{"text": "Selamat pagi", "languageCode": "id-ID"}' \
      --output audio_output.mp3
    ```
    Perintah di atas akan menyimpan output audio ke file `audio_output.mp3`.

*   **Respons Sukses (200 OK):**
    *   **Content-Type:** `audio/mpeg`
    *   **Body:** Data biner dari file audio MP3. Klien perlu menangani data biner ini (misalnya, menyimpannya ke file atau memutarnya langsung).

*   **Respons Error:**
    *   `400 Bad Request`: Jika JSON input tidak valid atau parameter hilang.
        ```json
        { "error": "Harap sertakan 'text' dan 'languageCode' dalam request body JSON." }
        ```
    *   `500 Internal Server Error`: Jika ada masalah saat sintesis audio.
        ```json
        { "error": "Gagal mensintesis audio: <alasan_dari_azure>" }
        ```

## 5. Contoh Penggunaan dengan cURL

Lihat contoh cURL di bawah setiap deskripsi endpoint di atas.

## 6. Struktur Respons

*   Untuk endpoint yang mengembalikan data JSON, struktur detail telah dijelaskan di bawah masing-masing endpoint.
*   Untuk endpoint TTS, respons adalah data audio biner.

## 7. Catatan Tambahan

*   **Status Proyek:** Backend ini masih dalam tahap pengembangan awal (MVP untuk Hackathon). Fitur dan endpoint baru akan ditambahkan di masa depan.
*   **Keamanan:** Saat ini, endpoint menggunakan otorisasi `Anonymous`. Untuk penggunaan produksi, keamanan akan ditingkatkan (misalnya, menggunakan Azure API Management dengan kunci API atau autentikasi OAuth 2.0).
*   **Penanganan Error:** Penanganan error dasar telah diimplementasikan. Pesan error yang lebih detail mungkin tersedia di log server (Application Insights) untuk tujuan debugging.
*   **Batasan (Rate Limiting):** Saat ini tidak ada rate limiting eksplisit yang diterapkan di level fungsi. Namun, layanan Azure yang mendasarinya (AI Vision, OpenAI, AI Speech) memiliki batasan penggunaan sendiri tergantung pada tier layanan yang digunakan.
*   **Kontribusi:** (Jika proyek open source) Informasi tentang cara berkontribusi.
*   **Lisensi:** (Jika ada).

---
Untuk pertanyaan atau masalah, silakan buka *issue* di repositori ini (jika ada).