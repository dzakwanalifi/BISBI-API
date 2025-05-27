import logging
import os
import json
import azure.functions as func

# Import SDK untuk Azure AI Speech (Text-to-Speech)
import azure.cognitiveservices.speech as speechsdk

# UBAH DEFINISI FUNGSI main UNTUK MENERIMA user_id
def main(req: func.HttpRequest, user_id: str = None) -> func.HttpResponse: # Tambahkan user_id opsional
    if user_id:
        logging.info(f'Python HTTP trigger function processed a request for GetTTSAudio by user {user_id}.')
    else:
        logging.warning('GetTTSAudio accessed without user_id. Auth might not be applied.')

    try:
        # 1. Ambil konfigurasi dari environment variables
        speech_key = os.environ.get("AZURE_AI_SERVICES_KEY")
        speech_region = os.environ.get("AZURE_AI_SERVICES_REGION")

        if not speech_key or not speech_region:
            logging.error("Konfigurasi Azure AI Speech (key atau region) tidak lengkap.")
            return func.HttpResponse(json.dumps({"error": "Error: Server configuration missing for Speech service."}), mimetype="application/json", status_code=500)

        # 2. Dapatkan input JSON dari request body
        try:
            req_body = req.get_json()
        except ValueError:
            logging.warning("Request body bukan JSON yang valid.")
            return func.HttpResponse(json.dumps({"error": "Harap kirim request body dalam format JSON."}), mimetype="application/json", status_code=400)

        text_to_speak = req_body.get('text')
        language_code = req_body.get('languageCode')
        voice_name_input = req_body.get('voiceName') # Opsional

        if not text_to_speak or not language_code:
            logging.warning("Parameter 'text' atau 'languageCode' tidak ada di request body.")
            return func.HttpResponse(
                json.dumps({"error": "Harap sertakan 'text' dan 'languageCode' dalam request body JSON."}),
                mimetype="application/json",
                 status_code=400
            )

        # 3. Inisialisasi konfigurasi Azure AI Speech
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        
        # (Opsional) Atur suara jika diberikan oleh klien
        if voice_name_input:
            speech_config.speech_synthesis_voice_name = voice_name_input
        else:
            # Atur default voice jika tidak ada input (sesuaikan dengan kebutuhan)
            # Contoh: jika language_code adalah id-ID, pilih suara Indonesia
            if language_code.lower() == "id-id":
                speech_config.speech_synthesis_voice_name = "id-ID-ArdiNeural"
            elif language_code.lower() == "en-us":
                speech_config.speech_synthesis_voice_name = "en-US-AvaMultilingualNeural"
            # Tambahkan default lain jika perlu

        # Atur format output audio (misalnya, MP3)
        # Daftar format: https://docs.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.speechsynthesisoutputformat?view=azure-python
        speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)

        # Inisialisasi SpeechSynthesizer. Kita tidak akan menulis ke file, jadi audio_config bisa None.
        # Hasil audio akan ada di result.audio_data
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

        # 4. Panggil Azure AI Speech untuk sintesis teks
        logging.info(f"Mensintesis teks: '{text_to_speak}' ke bahasa '{language_code}'...")
        
        # Menggunakan speak_text_async untuk teks (SSML juga bisa dengan speak_ssml_async)
        result = speech_synthesizer.speak_text_async(text_to_speak).get()

        # 5. Proses respons dari Azure AI Speech
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio_data = result.audio_data # Ini adalah bytes audio
            logging.info(f"Sintesis audio berhasil, ukuran data: {len(audio_data)} bytes.")
            return func.HttpResponse(
                body=audio_data,
                mimetype="audio/mpeg", # Sesuaikan dengan format yang dipilih di speech_config
                status_code=200
            )
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            logging.error(f"Sintesis audio dibatalkan: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                logging.error(f"Detail error: {cancellation_details.error_details}")
            return func.HttpResponse(
                json.dumps({"error": f"Gagal mensintesis audio: {cancellation_details.reason}"}),
                mimetype="application/json",
                status_code=500
            )
        else:
            logging.error(f"Alasan sintesis audio tidak diketahui: {result.reason}")
            return func.HttpResponse(
                json.dumps({"error": "Terjadi kesalahan yang tidak diketahui saat sintesis audio."}),
                mimetype="application/json",
                status_code=500
            )

    except Exception as e:
        logging.error(f"Terjadi kesalahan internal: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            json.dumps({"error": "Terjadi kesalahan pada server saat memproses permintaan text-to-speech."}),
            mimetype="application/json",
            status_code=500
        )