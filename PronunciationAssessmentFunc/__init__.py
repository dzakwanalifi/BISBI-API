import logging
import os
import json
# Hapus tempfile jika tidak digunakan lagi untuk opsi ini
import azure.functions as func
import azure.cognitiveservices.speech as speechsdk

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request for PronunciationAssessmentFunc.')

    try:
        speech_key = os.environ.get("AZURE_AI_SERVICES_KEY")
        speech_region = os.environ.get("AZURE_AI_SERVICES_REGION")

        if not speech_key or not speech_region:
            # ... (error handling) ...
            return func.HttpResponse(
                json.dumps({"error": "Server configuration missing for Speech service."}),
                mimetype="application/json", status_code=500
            )

        audio_file_from_req = req.files.get('audio')
        reference_text = req.form.get('referenceText')
        language_code = req.form.get('languageCode', 'en-US')
        grading_system_str = req.form.get('gradingSystem', 'HundredMark')
        granularity_str = req.form.get('granularity', 'Phoneme')

        if not audio_file_from_req or not reference_text:
            # ... (error handling) ...
            return func.HttpResponse(
                json.dumps({"error": "Harap unggah file audio dengan field name 'audio' dan sertakan 'referenceText'."}),
                mimetype="application/json", status_code=400
            )

        audio_bytes = audio_file_from_req.read() # Baca byte audio

        # 4. Inisialisasi konfigurasi Azure AI Speech
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        
        # --- PERUBAHAN UNTUK AUDIO INPUT ---
        # Tentukan format stream audio jika memungkinkan (misalnya, jika Anda tahu itu MP3)
        # Untuk MP3, Anda mungkin perlu SpeechServiceConnection_RecoLanguage_MP3_Direct_OwnCompressor = "true"
        # atau biarkan SDK mencoba mendeteksinya.
        # Namun, untuk Pronunciation Assessment, WAV lebih disarankan.
        # Jika klien mengirim MP3, idealnya dikonversi ke WAV dulu.
        # Untuk sekarang, kita coba dengan PushAudioInputStream, SDK mungkin bisa handle MP3.
        
        # Dapatkan format audio dari content_type jika ada, atau default
        # Ini lebih untuk informasi, SDK stream biasanya bisa auto-detect format umum
        audio_format_str = audio_file_from_req.mimetype if audio_file_from_req.mimetype else "audio/mpeg" 
        logging.info(f"Mencoba memproses audio dengan format yang dilaporkan: {audio_format_str}")

        # Buat PushAudioInputStream
        push_stream = speechsdk.audio.PushAudioInputStream() # Default format bisa jadi WAV
        # Jika Anda tahu formatnya MP3, Anda bisa coba:
        # format = speechsdk.audio.AudioStreamFormat(compressed_format=speechsdk.AudioStreamContainerFormat.MP3)
        # push_stream = speechsdk.audio.PushAudioInputStream(stream_format=format)
        
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        # --- AKHIR PERUBAHAN AUDIO INPUT ---

        grading_system_map = {
            "HundredMark": speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            "FivePoint": speechsdk.PronunciationAssessmentGradingSystem.FivePoint
        }
        granularity_map = {
            "Phoneme": speechsdk.PronunciationAssessmentGranularity.Phoneme,
            "Word": speechsdk.PronunciationAssessmentGranularity.Word,
            "FullText": speechsdk.PronunciationAssessmentGranularity.FullText
        }

        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=grading_system_map.get(grading_system_str, speechsdk.PronunciationAssessmentGradingSystem.HundredMark),
            granularity=granularity_map.get(granularity_str, speechsdk.PronunciationAssessmentGranularity.Phoneme)
        )
        pronunciation_config.enable_miscue = True # Tambahkan ini untuk tes
        
        speech_config.speech_recognition_language = language_code
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        pronunciation_config.apply_to(speech_recognizer)

        # Tulis byte audio ke stream SEBELUM memulai recognizer
        push_stream.write(audio_bytes)
        push_stream.close() # Menandakan akhir stream audio

        logging.info(f"Melakukan penilaian pelafalan untuk teks: '{reference_text}' bahasa: '{language_code}'...")
        result = speech_recognizer.recognize_once_async().get()

        # ... (sisa kode untuk memproses 'result' sama seperti sebelumnya) ...
        # (Pastikan Anda memiliki 'response_data' diinisialisasi di sini jika 'result.reason' bukan RecognizedSpeech)
        response_data = {"error": "Gagal memproses hasil."} # Default error

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            logging.info(f"Teks dikenali: {result.text}")
            pronunciation_result_json_str = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
            # logging.info(f"JSON Mentah dari SpeechServiceResponse: {pronunciation_result_json_str}")
            if pronunciation_result_json_str:
                pronunciation_details = json.loads(pronunciation_result_json_str)
                logging.info("Berhasil mendapatkan detail penilaian pelafalan.")
                # logging.info(f"JSON Mentah Parsed: {json.dumps(pronunciation_details, indent=2)}") # Log JSON yang sudah diparsing untuk verifikasi                # Inisialisasi response_data
                response_data = {
                    "recognizedText": pronunciation_details.get("DisplayText"),
                    "accuracyScore": None,
                    "pronunciationScore": None,
                    "completenessScore": None,
                    "fluencyScore": None,
                    "prosodyScore": None, # Mungkin tidak selalu ada
                    "words": []
                }                # Skor utama ada di dalam NBest -> elemen pertama -> PronunciationAssessment
                if "NBest" in pronunciation_details and \
                   isinstance(pronunciation_details.get("NBest"), list) and \
                   len(pronunciation_details["NBest"]) > 0:
                    
                    best_recognition_candidate = pronunciation_details["NBest"][0] # Ambil kandidat pertama
                    
                    # Ambil recognizedText dari NBest jika lebih akurat
                    response_data["recognizedText"] = best_recognition_candidate.get("Display", response_data["recognizedText"])

                    if "PronunciationAssessment" in best_recognition_candidate:
                        pa_overall_scores = best_recognition_candidate["PronunciationAssessment"]
                        response_data["accuracyScore"] = pa_overall_scores.get("AccuracyScore")
                        response_data["pronunciationScore"] = pa_overall_scores.get("PronScore")
                        response_data["completenessScore"] = pa_overall_scores.get("CompletenessScore")
                        response_data["fluencyScore"] = pa_overall_scores.get("FluencyScore")
                        response_data["prosodyScore"] = pa_overall_scores.get("ProsodyScore")                    # Proses kata-kata dari hasil NBest terbaik
                    if "Words" in best_recognition_candidate:
                        for word_info in best_recognition_candidate.get("Words", []): # Default ke list kosong
                            word_data = {
                                "word": word_info.get("Word"),
                                "accuracyScore": None,
                                "errorType": "None", # Default ke "None"
                                "phonemes": []
                            }
                            # Skor dan ErrorType kata ada di dalam PronunciationAssessment per kata
                            if "PronunciationAssessment" in word_info:
                                pa_word_details = word_info["PronunciationAssessment"]
                                word_data["accuracyScore"] = pa_word_details.get("AccuracyScore")
                                word_data["errorType"] = pa_word_details.get("ErrorType", "None") # AMBIL DARI SINI
                            
                            if granularity_str == "Phoneme" and "Phonemes" in word_info:
                                for p_info in word_info.get("Phonemes", []): # Default ke list kosong
                                    phoneme_accuracy = None
                                    # Skor fonem ada di dalam PronunciationAssessment-nya sendiri di dalam objek fonem
                                    if "PronunciationAssessment" in p_info:
                                        pa_phoneme_details = p_info["PronunciationAssessment"]
                                        phoneme_accuracy = pa_phoneme_details.get("AccuracyScore")

                                    word_data["phonemes"].append({
                                        "phoneme": p_info.get("Phoneme"),
                                        "accuracyScore": phoneme_accuracy
                                    })
                            response_data["words"].append(word_data)
                    else:
                        logging.warning("Tidak ada 'Words' dalam NBest candidate.")
                else:
                    logging.warning("Tidak ada 'NBest' atau format NBest tidak sesuai dalam hasil Pronunciation Assessment.")
                
                return func.HttpResponse(
                    body=json.dumps(response_data),
                    mimetype="application/json",
                    status_code=200
                )
            else:
                logging.error("Tidak ada detail JSON penilaian pelafalan dalam respons.")
                response_data = {"error": "Gagal mendapatkan detail penilaian dari layanan."}
                return func.HttpResponse(
                    json.dumps(response_data),
                    mimetype="application/json", status_code=500
                )
        elif result.reason == speechsdk.ResultReason.NoMatch:
            logging.warning(f"Tidak ada ucapan yang dikenali: {result.no_match_details}")
            response_data = {"error": "Tidak ada ucapan yang bisa dikenali."}
            return func.HttpResponse(
                json.dumps(response_data),
                mimetype="application/json", status_code=400
            )
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            logging.error(f"Penilaian pelafalan dibatalkan: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                logging.error(f"Detail error: {cancellation_details.error_details}")
            response_data = {"error": f"Gagal melakukan penilaian pelafalan: {cancellation_details.reason}"}
            return func.HttpResponse(
                json.dumps(response_data),
                mimetype="application/json", status_code=500
            )
        else:
            logging.error(f"Alasan penilaian pelafalan tidak diketahui: {result.reason}")
            response_data = {"error": "Terjadi kesalahan yang tidak diketahui saat penilaian pelafalan."}
            return func.HttpResponse(
                json.dumps(response_data),
                mimetype="application/json", status_code=500
            )
    except ValueError as ve: # Untuk req.form atau req.files jika ada masalah
        logging.error(f"ValueError: {str(ve)}")
        return func.HttpResponse(
            body=json.dumps({"error": f"Invalid input: {str(ve)}"}), # Pastikan body di sini juga json.dumps
            mimetype="application/json",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Terjadi kesalahan internal di PronunciationAssessmentFunc: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        
        error_payload = {
            "error": "Terjadi kesalahan pada server saat memproses penilaian pelafalan.",
            "details": str(e) # Sertakan detail error jika membantu
        }
        return func.HttpResponse(
            body=json.dumps(error_payload),
            mimetype="application/json",
            status_code=500
        )