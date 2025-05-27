import logging
import os
import json
import azure.functions as func

# Import SDK untuk Azure OpenAI
from openai import AzureOpenAI # Pastikan versi openai >= 1.0.0

# Helper untuk mapping bahasa (bisa diperluas)
LANGUAGE_FULL_NAMES = {
    "en": "English",
    "id": "Indonesian",
    "es": "Spanish",
    # Tambahkan bahasa lain jika perlu
}

DEFAULT_PROFICIENCY = "intermediate"

# UBAH DEFINISI FUNGSI main UNTUK MENERIMA user_id dari kwargs (atau sebagai parameter)
def main(req: func.HttpRequest) -> func.HttpResponse: # Tambahkan user_id opsional
    user_id = getattr(req, 'user_id_injected', None) # Retrieve user_id from req

    # Jika user_id tidak None, berarti sudah diautentikasi oleh decorator di routes.py
    if user_id:
        logging.info(f'Python HTTP trigger function processed a request for GenerateLesson by user {user_id}.')
    else:
        # Ini seharusnya tidak terjadi jika decorator diterapkan dengan benar di routes.py
        logging.warning('GenerateLesson accessed without user_id. Auth might not be applied.')
        # Anda bisa memutuskan untuk mengembalikan error di sini jika user_id wajib
        # return func.HttpResponse("Authentication required.", status_code=401)

    try:
        # 1. Ambil konfigurasi Azure OpenAI dari environment variables
        openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        openai_key = os.environ.get("AZURE_OPENAI_KEY")
        openai_deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") # Nama deployment gpt-4.1 Anda

        if not all([openai_endpoint, openai_key, openai_deployment_name]):
            logging.error("Konfigurasi Azure OpenAI tidak lengkap.")
            return func.HttpResponse(
                json.dumps({"error": "Server configuration missing for OpenAI."}), 
                mimetype="application/json", status_code=500
            )

        # 2. Dapatkan input JSON dari request body
        try:
            req_body = req.get_json()
        except ValueError:
            logging.warning("Request body bukan JSON yang valid.")
            return func.HttpResponse(
                json.dumps({"error": "Harap kirim request body dalam format JSON."}), 
                mimetype="application/json", status_code=400
            )

        scenario_description = req_body.get('scenarioDescription')
        native_lang_code = req_body.get('userNativeLanguageCode', 'id') # Default ke Indonesia
        learning_lang_code = req_body.get('learningLanguageCode', 'en') # Default ke Inggris
        proficiency_level = req_body.get('userProficiencyLevel', DEFAULT_PROFICIENCY).lower()

        if not scenario_description:
            logging.warning("Parameter 'scenarioDescription' tidak ada di request body.")
            return func.HttpResponse(
                json.dumps({"error": "Harap sertakan 'scenarioDescription' dalam request body JSON."}),
                mimetype="application/json", status_code=400
            )

        learning_lang_name = LANGUAGE_FULL_NAMES.get(learning_lang_code, "English")
        native_lang_name = LANGUAGE_FULL_NAMES.get(native_lang_code, "Indonesian")

        # --- CONTOH PENGGUNAAN user_id (JIKA PERLU) ---
        # Misalnya, jika Anda ingin menyimpan riwayat pelajaran yang digenerate untuk pengguna ini:
        if user_id:
            logging.info(f"User {user_id} requested a lesson for scenario: '{scenario_description}'")
        # Nanti setelah pelajaran berhasil digenerate, Anda bisa panggil fungsi untuk menyimpan
        # save_lesson_history(user_id, scenario_description, generated_lesson_json)
        # --- AKHIR CONTOH PENGGUNAAN user_id ---

        # 3. Inisialisasi klien Azure OpenAI
        client = AzureOpenAI(
            azure_endpoint=openai_endpoint,
            api_key=openai_key,
            api_version="2024-02-01" # Sesuaikan dengan versi API yang Anda gunakan
        )

        # 4. Susun Prompt untuk Azure OpenAI (Model Teks)
        # Ini adalah bagian yang paling membutuhkan iterasi (prompt engineering)
        
        # Definisikan skema JSON yang kita inginkan dalam prompt
        # (Menyederhanakan: menghilangkan exampleDialogue untuk MVP awal, fokus pada vocab, phrases, grammar)
        json_schema_instruction = f"""
Respond ONLY with a single, valid JSON object matching this exact schema. Do not add any text before or after the JSON object.
The JSON object should contain:
1.  "scenarioTitle": an object with two keys, "{learning_lang_code}" and "{native_lang_code}", containing a concise and relevant title for the learning scenario in both languages.
2.  "vocabulary": an array of objects. Each object must have a "term" key. The value of "term" is an object with two keys: "{learning_lang_code}" (the vocabulary word in the learning language) and "{native_lang_code}" (its translation). Include 5-7 highly relevant vocabulary items.
3.  "keyPhrases": an array of objects. Each object must have a "phrase" key. The value of "phrase" is an object with two keys: "{learning_lang_code}" (the key phrase in the learning language) and "{native_lang_code}" (its translation). Include 3-5 highly relevant key phrases.
4.  "grammarTips": an array of objects. Each object must have a "tip" key and an "example" key. The value of "tip" is an object with two keys: "{learning_lang_code}" (the grammar explanation) and "{native_lang_code}" (its translation). The value of "example" is also an object with two keys: "{learning_lang_code}" (an example sentence demonstrating the grammar point) and "{native_lang_code}" (its translation). Include 1-2 concise and practical grammar tips relevant to the scenario and proficiency level.

Example of a vocabulary item: {{ "term": {{ "{learning_lang_code}": "Airport", "{native_lang_code}": "Bandara" }} }}
Example of a key phrase item: {{ "phrase": {{ "{learning_lang_code}": "Where is the check-in counter?", "{native_lang_code}": "Di mana konter check-in?" }} }}
Example of a grammar tip item: {{ "tip": {{ "{learning_lang_code}": "Use 'the' for specific nouns.", "{native_lang_code}": "Gunakan 'the' untuk kata benda spesifik." }}, "example": {{ "{learning_lang_code}": "The airport is big.", "{native_lang_code}": "Bandara itu besar." }} }}
"""

        system_message_content = f"""
You are an expert AI language tutor creating personalized learning content. 
The user wants to learn {learning_lang_name} (target language, code: '{learning_lang_code}'). 
Their native language is {native_lang_name} (source language, code: '{native_lang_code}').
Their current proficiency level in {learning_lang_name} is '{proficiency_level}'.
Adjust the complexity and depth of the content according to this proficiency level. For beginners, use simpler words and basic grammar. For advanced, use more nuanced vocabulary and complex structures.
{json_schema_instruction}
"""
        
        user_message_content = f"Generate learning material for the following scenario: \"{scenario_description}\""

        messages_payload = [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": user_message_content}
        ]

        # 5. Panggil Azure OpenAI
        logging.info(f"Memanggil Azure OpenAI deployment '{openai_deployment_name}' untuk pelajaran situasional...")
        try:
            response = client.chat.completions.create(
                model=openai_deployment_name, 
                messages=messages_payload,
                max_tokens=1500, # Mungkin perlu lebih besar untuk konten yang kaya
                temperature=0.5, # Cukup seimbang antara kreativitas dan keteraturan
                # response_format={ "type": "json_object" } # Coba ini jika model mendukung, bisa meningkatkan keandalan JSON
            )
        except Exception as e_openai:
            logging.error(f"Error calling Azure OpenAI: {str(e_openai)}")
            import traceback
            logging.error(traceback.format_exc())
            return func.HttpResponse(
                json.dumps({"error": "Error communicating with AI model."}), 
                mimetype="application/json", status_code=500
            )

        # 6. Proses respons dari Azure OpenAI
        if response.choices and len(response.choices) > 0:
            assistant_message = response.choices[0].message # Access the first choice's message
            if assistant_message and assistant_message.content:
                try:
                    json_output_str = assistant_message.content.strip()
                    # Hapus ```json ... ``` jika model menambahkannya
                    if json_output_str.startswith("```json"):
                        json_output_str = json_output_str[7:]
                    elif json_output_str.startswith("```"): # Gunakan elif jika ```json tidak ada
                        json_output_str = json_output_str[3:]
                    if json_output_str.endswith("```"):
                        json_output_str = json_output_str[:-3]
                    
                    parsed_json = json.loads(json_output_str.strip()) # Penting
                    logging.info("Respon JSON dari OpenAI berhasil di-parse untuk pelajaran situasional.")
                    
                    # --- CONTOH PENYIMPANAN RIWAYAT (JIKA PERLU) ---
                    if user_id: # Pastikan user_id ada
                        logging.info(f"Lesson generation history can be saved for user {user_id}")
                    #   from ..shared_code import lesson_history_db # Asumsi ada modul untuk interaksi DB
                    #   try:
                    #       lesson_history_db.save_lesson_attempt(
                    #           user_id=user_id,
                    #           scenario_description=scenario_description,
                    #           learning_language_code=learning_lang_code,
                    #           native_language_code=native_lang_code,
                    #           proficiency_level=proficiency_level,
                    #           generated_lesson_json=parsed_json # atau bagian pentingnya
                    #       )
                    #       logging.info(f"Lesson generation history saved for user {user_id}")
                    #   except Exception as db_error:
                    #       logging.error(f"Failed to save lesson history for user {user_id}: {db_error}")
                    # --- AKHIR CONTOH PENYIMPANAN RIWAYAT ---

                    return func.HttpResponse(
                        body=json.dumps(parsed_json),
                        mimetype="application/json",
                        status_code=200
                    )
                except json.JSONDecodeError as json_err:
                    logging.error(f"Gagal mem-parse JSON dari respons OpenAI: {json_err}")
                    logging.error(f"Respons mentah dari OpenAI: {assistant_message.content}")
                    return func.HttpResponse(
                        json.dumps({"error": "AI model returned non-JSON content or malformed JSON."}),
                        mimetype="application/json", status_code=500
                    )
            else:
                logging.warning("Respons OpenAI untuk pelajaran situasional tidak memiliki konten.")
                return func.HttpResponse(
                    json.dumps({"error": "AI model returned no content."}),
                    mimetype="application/json", status_code=500
                )
        else:
            logging.warning("Respons OpenAI untuk pelajaran situasional tidak memiliki choices.")
            return func.HttpResponse(
                json.dumps({"error": "AI model returned no choices."}),
                mimetype="application/json", status_code=500
            )

    except Exception as e:
        # if isinstance(e, AuthError):
        #     logging.error(f"AuthError in GenerateLesson main: {e.error}")
        #     return func.HttpResponse(
        #         json.dumps(e.error),
        #         status_code=e.status_code,
        #         mimetype="application/json"
        #     )
        
        logging.error(f"Terjadi kesalahan internal di GenerateLesson: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            json.dumps({"error": "Terjadi kesalahan pada server saat memproses permintaan pelajaran."}),
            mimetype="application/json", status_code=500
        )