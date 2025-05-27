import logging
import os
import json
import azure.functions as func

# Import SDK untuk Azure OpenAI
from openai import AzureOpenAI # Pastikan versi openai >= 1.0.0
from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory # Import untuk Content Safety
from azure.ai.contentsafety import ContentSafetyClient # Import untuk Content Safety
from azure.core.credentials import AzureKeyCredential # Import untuk Content Safety

# Helper untuk mapping bahasa (bisa diperluas)
LANGUAGE_FULL_NAMES = {
    "en": "English",
    "id": "Indonesian",
    "es": "Spanish",
    # Tambahkan bahasa lain jika perlu
}

DEFAULT_PROFICIENCY = "intermediate"
CONTENT_SAFETY_TEXT_THRESHOLD = 1 # Threshold untuk content safety text analysis

# Inisialisasi Content Safety Client di luar fungsi main agar bisa di-reuse
# atau Anda bisa membuatnya sebagai singleton/dependency injection jika menggunakan framework
content_safety_client = None
try:
    CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
    CONTENT_SAFETY_KEY = os.environ.get("CONTENT_SAFETY_KEY")
    if CONTENT_SAFETY_ENDPOINT and CONTENT_SAFETY_KEY:
        content_safety_client = ContentSafetyClient(CONTENT_SAFETY_ENDPOINT, AzureKeyCredential(CONTENT_SAFETY_KEY))
        logging.info("ContentSafetyClient initialized successfully.")
    else:
        logging.warning("Content Safety Endpoint or Key is not configured. Text safety checks will be skipped.")
except Exception as cs_init_err:
    logging.error(f"Error initializing ContentSafetyClient: {cs_init_err}", exc_info=True)
    content_safety_client = None


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request for GenerateSituationalLesson.')

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

        # Content Safety Check untuk Input scenarioDescription
        if content_safety_client and scenario_description:
            try:
                logging.info(f"Performing content safety analysis on scenarioDescription: '{scenario_description[:100]}...'")
                analyze_text_request = AnalyzeTextOptions(
                    text=scenario_description,
                    categories=[TextCategory.SEXUAL, TextCategory.VIOLENCE, TextCategory.HATE, TextCategory.SELF_HARM]
                )
                response_text_safety = content_safety_client.analyze_text(analyze_text_request)

                blocked_input_categories = []
                if response_text_safety and hasattr(response_text_safety, 'categories_analysis'):
                    for category_result in response_text_safety.categories_analysis:
                        if category_result.severity >= CONTENT_SAFETY_TEXT_THRESHOLD:
                            blocked_input_categories.append(f"{category_result.category.value if hasattr(category_result.category, 'value') else category_result.category} (Score: {category_result.severity})")
                
                if blocked_input_categories:
                    logging.warning(f"Input scenarioDescription blocked by Content Safety. Categories: {', '.join(blocked_input_categories)}")
                    return func.HttpResponse(
                        json.dumps({"error": "Input scenario description contains inappropriate content.", "details": f"Blocked categories: {', '.join(blocked_input_categories)}"}),
                        mimetype="application/json",
                        status_code=400
                    )
                logging.info("Input scenarioDescription passed content safety check.")
            except Exception as text_safety_err:
                logging.error(f"Error during text content safety analysis for input: {text_safety_err}", exc_info=True)
                # Jika safety check gagal, putuskan apakah akan melanjutkan atau mengembalikan error
                # Untuk keamanan, lebih baik kembalikan error
                return func.HttpResponse(
                    json.dumps({"error": "Failed to verify safety of input scenario description."}),
                    mimetype="application/json",
                    status_code=500 
                )

        learning_lang_name = LANGUAGE_FULL_NAMES.get(learning_lang_code, "English")
        native_lang_name = LANGUAGE_FULL_NAMES.get(native_lang_code, "Indonesian")

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
Ensure all generated content is strictly appropriate for young children, avoiding any mature themes, violence, profanity, hate speech, or self-harm references.
The content should be positive, educational, and encouraging.
{json_schema_instruction}
"""
        
        user_message_content = f'Generate learning material for the following scenario: "{scenario_description}"'

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

                    # Content Safety Check untuk Output dari Azure OpenAI
                    if content_safety_client:
                        try:
                            texts_to_check = []
                            # Kumpulkan semua string dari output JSON
                            if "scenarioTitle" in parsed_json and isinstance(parsed_json["scenarioTitle"], dict):
                                texts_to_check.extend(str(v) for v in parsed_json["scenarioTitle"].values() if isinstance(v, (str, int, float)))
                            if "vocabulary" in parsed_json and isinstance(parsed_json["vocabulary"], list):
                                for item in parsed_json["vocabulary"]:
                                    if isinstance(item, dict) and "term" in item and isinstance(item["term"], dict):
                                        texts_to_check.extend(str(v) for v in item["term"].values() if isinstance(v, (str, int, float)))
                            if "keyPhrases" in parsed_json and isinstance(parsed_json["keyPhrases"], list):
                                for item in parsed_json["keyPhrases"]:
                                    if isinstance(item, dict) and "phrase" in item and isinstance(item["phrase"], dict):
                                        texts_to_check.extend(str(v) for v in item["phrase"].values() if isinstance(v, (str, int, float)))
                            if "grammarTips" in parsed_json and isinstance(parsed_json["grammarTips"], list):
                                for item in parsed_json["grammarTips"]:
                                    if isinstance(item, dict):
                                        if "tip" in item and isinstance(item["tip"], dict):
                                            texts_to_check.extend(str(v) for v in item["tip"].values() if isinstance(v, (str, int, float)))
                                        if "example" in item and isinstance(item["example"], dict):
                                            texts_to_check.extend(str(v) for v in item["example"].values() if isinstance(v, (str, int, float)))
                            
                            combined_text_output = " . ".join(filter(None, texts_to_check))

                            if combined_text_output:
                                logging.info(f"Performing content safety analysis on generated lesson output (length: {len(combined_text_output)})...")
                                analyze_output_request = AnalyzeTextOptions(
                                    text=combined_text_output,
                                    categories=[TextCategory.SEXUAL, TextCategory.VIOLENCE, TextCategory.HATE, TextCategory.SELF_HARM]
                                )
                                response_output_safety = content_safety_client.analyze_text(analyze_output_request)
                                
                                blocked_output_categories = []
                                if response_output_safety and hasattr(response_output_safety, 'categories_analysis'):
                                    for category_result in response_output_safety.categories_analysis:
                                        if category_result.severity >= CONTENT_SAFETY_TEXT_THRESHOLD:
                                            blocked_output_categories.append(f"{category_result.category.value if hasattr(category_result.category, 'value') else category_result.category} (Score: {category_result.severity})")

                                if blocked_output_categories:
                                    logging.warning(f"Generated lesson content blocked by Content Safety. Categories: {', '.join(blocked_output_categories)}")
                                    logging.warning(f"Blocked content (first 500 chars): {combined_text_output[:500]}")
                                    return func.HttpResponse(
                                        json.dumps({"error": "Generated lesson content was found to be inappropriate and has been blocked."}),
                                        mimetype="application/json",
                                        status_code=500 
                                    )
                                logging.info("Generated lesson content passed content safety check.")
                        except Exception as output_safety_err:
                            logging.error(f"Error during content safety analysis for generated output: {output_safety_err}", exc_info=True)
                            # Jika safety check gagal, lebih baik blokir output
                            return func.HttpResponse(
                                json.dumps({"error": "Failed to verify safety of generated content."}),
                                mimetype="application/json",
                                status_code=500
                            )
                    
                    # Jika lolos, kembalikan parsed_json
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
        logging.error(f"Terjadi kesalahan internal di GenerateLesson: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return func.HttpResponse(
            json.dumps({"error": "Terjadi kesalahan pada server saat memproses permintaan pelajaran."}),
            mimetype="application/json", status_code=500
        )