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
    - [4.1 Health Check API](#41-health-check-api)
    - [4.2 Deteksi Objek Visual](#42-deteksi-objek-visual)
    - [4.3 Dapatkan Detail Objek Visual (dengan OpenAI)](#43-dapatkan-detail-objek-visual-dengan-openai)
    - [4.4 Konversi Teks ke Audio (Text-to-Speech)](#44-konversi-teks-ke-audio-text-to-speech)
    - [4.5 Generasi Pelajaran Situasional (dengan OpenAI) *(Baru Ditambahkan)*](#45-generasi-pelajaran-situasional-dengan-openai-baru-ditambahkan)
  - [5. Contoh Penggunaan dengan cURL](#5-contoh-penggunaan-dengan-curl)
  - [6. Struktur Respons](#6-struktur-respons)
  - [7. Catatan Tambahan](#7-catatan-tambahan)

## 1. Deskripsi Proyek

Lensa Bahasa bertujuan untuk memberdayakan pemuda Indonesia dengan keterampilan komunikasi bahasa Inggris yang praktis, kontekstual, dan personal. Backend API ini mendukung fitur-fitur seperti kamus visual interaktif, pelajaran situasional dinamis, dan output audio.

## 2. Arsitektur Backend

*   **Platform:** Azure Functions (Serverless, Python)
*   **Layanan AI Utama:**
    *   Azure AI Vision (untuk deteksi objek)
    *   Azure OpenAI Service (GPT-4.1 atau setara, untuk analisis gambar objek, generasi teks deskriptif, dan generasi konten pelajaran)
    *   Azure AI Speech (Text-to-Speech untuk generasi audio)
*   **Konfigurasi & Rahasia:** Dikelola melalui Azure Key Vault dan Application Settings di Azure Function App.

## 3. Prasyarat Penggunaan API

*   **URL Basis API:** `https://lensabahasa-api.azurewebsites.net/api` (Ganti `lensabahasa-api` dengan nama Function App Anda jika berbeda).
*   **Alat Pengujian API:** Postman, cURL, atau klien HTTP lainnya.
*   Tidak ada kunci API khusus yang diperlukan untuk memanggil endpoint ini saat ini (otorisasi diatur ke `Anonymous`).

## 4. Endpoint API

Berikut adalah detail untuk setiap endpoint yang tersedia:

### 4.1 Health Check API

Endpoint ini menyediakan status dasar API.

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

Endpoint ini menerima gambar dan mengembalikan daftar objek yang terdeteksi.

*   **URL:** `/visual/detect-objects`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/visual/detect-objects`
*   **Metode:** `POST`
*   **Request Body:** `multipart/form-data`
    *   **Field:** `image` (file)
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
    *   **Field:** `image` (file), `targetLanguage` (opsional, teks, default: `en`), `sourceLanguage` (opsional, teks, default: `id`)
*   **Respons Sukses (200 OK):**
    ```json
    {
        "objectName": { "en": "Smartphone", "id": "Ponsel pintar" },
        "description": { "en": "A modern smartphone...", "id": "Ponsel pintar modern..." },
        "exampleSentences": [ { "en": "I use my smartphone daily.", "id": "Saya menggunakan ponsel pintar saya setiap hari." } ],
        "relatedAdjectives": [ { "en": "smart", "id": "pintar" } ]
    }
    ```

### 4.4 Konversi Teks ke Audio (Text-to-Speech)

Menerima teks dan kode bahasa, mengembalikan data audio MP3.

*   **URL:** `/audio/text-to-speech`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/audio/text-to-speech`
*   **Metode:** `POST`
*   **Request Headers:** `Content-Type: application/json`
*   **Request Body (JSON):**
    ```json
    {
      "text": "Hello Lensa Bahasa",
      "languageCode": "en-US",
      "voiceName": "en-US-AvaNeural" // Opsional
    }
    ```
*   **Respons Sukses (200 OK):**
    *   **Content-Type:** `audio/mpeg`
    *   **Body:** Data biner audio MP3.

### 4.5 Generasi Pelajaran Situasional (dengan OpenAI) *(Baru Ditambahkan)*

Endpoint ini menerima deskripsi skenario dari pengguna dan menghasilkan konten pembelajaran bilingual (kosakata, frasa kunci, tips grammar) secara dinamis menggunakan Azure OpenAI.

*   **URL:** `/lessons/situational`
*   **URL Lengkap:** `https://lensabahasa-api.azurewebsites.net/api/lessons/situational`
*   **Metode:** `POST`
*   **Request Headers:**
    *   `Content-Type: application/json`
*   **Request Body (JSON):**
    ```json
    {
      "scenarioDescription": "Saya mau pergi ke supermarket untuk membeli buah-buahan dan sayuran.",
      "userNativeLanguageCode": "id", 
      "learningLanguageCode": "en", 
      "userProficiencyLevel": "beginner" // Opsional, default: "intermediate"
    }
    ```
    *   `scenarioDescription` (string, wajib): Deskripsi situasi oleh pengguna.
    *   `userNativeLanguageCode` (string, wajib, default `id`): Kode bahasa ibu pengguna (misalnya, "id", "en").
    *   `learningLanguageCode` (string, wajib, default `en`): Kode bahasa yang ingin dipelajari (misalnya, "en", "id").
    *   `userProficiencyLevel` (string, opsional, default `intermediate`): Tingkat kemahiran pengguna ("beginner", "intermediate", "advanced").

*   **Contoh Request (menggunakan cURL):**
    ```bash
    curl -X POST \
      https://lensabahasa-api.azurewebsites.net/api/lessons/situational \
      -H "Content-Type: application/json" \
      -d '{
            "scenarioDescription": "I need to book a hotel room for 3 nights.",
            "userNativeLanguageCode": "id",
            "learningLanguageCode": "en",
            "userProficiencyLevel": "intermediate"
          }'
    ```

*   **Respons Sukses (200 OK):**
    Objek JSON berisi materi pelajaran yang terstruktur.
    ```json
    {
        "scenarioTitle": {
            "en": "Booking a Hotel Room",
            "id": "Memesan Kamar Hotel"
        },
        "vocabulary": [
            {
                "term": { "en": "Reservation", "id": "Reservasi" }
            },
            {
                "term": { "en": "Availability", "id": "Ketersediaan" }
            }
            // ... lebih banyak kosakata
        ],
        "keyPhrases": [
            {
                "phrase": { "en": "I would like to make a reservation.", "id": "Saya ingin membuat reservasi." }
            },
            {
                "phrase": { "en": "Do you have any rooms available?", "id": "Apakah Anda memiliki kamar yang tersedia?" }
            }
            // ... lebih banyak frasa kunci
        ],
        "grammarTips": [
            {
                "tip": { 
                    "en": "Use 'would like to' for polite requests.", 
                    "id": "Gunakan 'would like to' untuk permintaan yang sopan." 
                },
                "example": { 
                    "en": "I would like to book a single room.", 
                    "id": "Saya ingin memesan kamar untuk satu orang." 
                }
            }
            // ... tips grammar lainnya
        ]
    }
    ```
    *(Struktur detail di atas adalah contoh. Output aktual mungkin sedikit bervariasi tergantung respons AI).*

*   **Respons Error:**
    *   `400 Bad Request`: Jika JSON input tidak valid atau parameter wajib hilang.
    *   `500 Internal Server Error`: Jika ada masalah di sisi server atau dengan panggilan ke OpenAI.

## 5. Contoh Penggunaan dengan cURL

Lihat contoh cURL di bawah setiap deskripsi endpoint di atas. Pastikan untuk mengganti URL basis jika nama Function App Anda berbeda dan sesuaikan path file atau data JSON.

## 6. Struktur Respons

*   Untuk endpoint yang mengembalikan data JSON, struktur detail telah dijelaskan di bawah masing-masing endpoint. Output dapat bervariasi tergantung pada input dan respons dari layanan AI.
*   Untuk endpoint TTS, respons adalah data audio biner.

## 7. Catatan Tambahan

*   **Status Proyek:** Backend ini masih dalam tahap pengembangan aktif (MVP untuk Hackathon). Fitur dan endpoint baru akan ditambahkan.
*   **Keamanan:** Endpoint saat ini menggunakan otorisasi `Anonymous`.
*   **Prompt Engineering:** Kualitas output dari endpoint yang menggunakan Azure OpenAI (`/visual/get-object-details`, `/lessons/situational`) sangat bergantung pada *prompt engineering* dan dapat ditingkatkan lebih lanjut.
*   **Batasan Layanan AI:** Harap perhatikan batasan penggunaan dan biaya dari layanan Azure AI yang mendasarinya.

---
Untuk pertanyaan atau masalah, silakan buka *issue* di repositori GitHub Anda (jika ini adalah proyek publik).