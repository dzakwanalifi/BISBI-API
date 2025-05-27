import logging
import os
import json
import base64 # Untuk encode gambar ke base64
import azure.functions as func

# Import SDK untuk Azure OpenAI
from openai import AzureOpenAI # Pastikan versi openai >= 1.0.0

# Import untuk Content Safety
from azure.ai.contentsafety import ContentSafetyClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError # Untuk menangani error dari Content Safety Service
from azure.ai.contentsafety.models import (
    AnalyzeTextOptions,
    TextCategory,
    AnalyzeImageOptions, # <-- Tambahkan ini
    ImageData,           # <-- Tambahkan ini
    ImageCategory        # <-- Tambahkan ini
)

# --- KONFIGURASI CONTENT SAFETY ---
# Threshold untuk Teks (digunakan untuk output OpenAI)
CONTENT_SAFETY_TEXT_THRESHOLD = 1

# Threshold untuk Gambar (digunakan untuk input gambar) - bisa disamakan atau dibedakan
CONTENT_SAFETY_IMAGE_THRESHOLD_SEXUAL = 1
CONTENT_SAFETY_IMAGE_THRESHOLD_VIOLENCE = 1
CONTENT_SAFETY_IMAGE_THRESHOLD_HATE = 1
CONTENT_SAFETY_IMAGE_THRESHOLD_SELF_HARM = 1
# ------------------------------------

# Inisialisasi Content Safety Client (Global untuk modul ini)
content_safety_client = None
CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
CONTENT_SAFETY_KEY = os.environ.get("CONTENT_SAFETY_KEY")

if CONTENT_SAFETY_ENDPOINT and CONTENT_SAFETY_KEY:
    try:
        content_safety_client = ContentSafetyClient(CONTENT_SAFETY_ENDPOINT, AzureKeyCredential(CONTENT_SAFETY_KEY))
        logging.info("ContentSafetyClient initialized successfully for GetObjectDetailsVisual.")
    except Exception as cs_init_err:
        logging.error(f"Error initializing ContentSafetyClient for GetObjectDetailsVisual: {cs_init_err}", exc_info=True)
        content_safety_client = None # Pastikan None jika gagal
else:
    logging.warning("Content Safety Endpoint or Key is not configured for GetObjectDetailsVisual. Safety checks might be skipped.")


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request for GetObjectDetailsVisual.')

    try:
        # 1. Ambil konfigurasi OpenAI dari environment variables
        openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        openai_key = os.environ.get("AZURE_OPENAI_KEY")
        openai_deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")

        if not all([openai_endpoint, openai_key, openai_deployment_name]):
            logging.error("Konfigurasi Azure OpenAI tidak lengkap.")
            return func.HttpResponse(
                json.dumps({"error": "Server configuration missing for OpenAI."}),
                mimetype="application/json",
                status_code=500
            )

        # 2. Dapatkan file gambar dan parameter bahasa dari request
        image_file = req.files.get('image')
        target_lang_code = req.form.get('targetLanguage', req.params.get('targetLanguage', 'en'))
        source_lang_code = req.form.get('sourceLanguage', req.params.get('sourceLanguage', 'id'))
        
        lang_names = {"en": "English", "id": "Indonesian"}
        target_language_name = lang_names.get(target_lang_code, "English")
        source_language_name = lang_names.get(source_lang_code, "Indonesian")

        if not image_file:
            logging.warning("Tidak ada file gambar yang diterima.")
            return func.HttpResponse(
                json.dumps({"error": "Harap unggah file gambar (cropped object) dengan field name 'image'."}),
                mimetype="application/json",
                status_code=400
            )
        
        # 3. Baca byte gambar DULU untuk Content Safety
        image_bytes = image_file.read() # Baca sekali saja
        if not image_bytes:
            logging.warning("File gambar kosong.")
            return func.HttpResponse(json.dumps({"error": "File gambar tidak boleh kosong."}),mimetype="application/json",status_code=400)

        # --- ANALISIS KEAMANAN GAMBAR INPUT DENGAN AZURE AI CONTENT SAFETY ---
        # Ini adalah langkah PENTING sebelum mengirim ke OpenAI
        if content_safety_client:
            try:
                logging.info("Performing image safety analysis on input image...")
                image_data_for_cs = ImageData(content=image_bytes)
                request_cs_image = AnalyzeImageOptions(image=image_data_for_cs, categories=[
                    ImageCategory.SEXUAL, 
                    ImageCategory.VIOLENCE,
                    ImageCategory.HATE,
                    ImageCategory.SELF_HARM
                ])
                response_cs_image = content_safety_client.analyze_image(request_cs_image)
                
                # Logika parsing dan pengecekan threshold untuk gambar
                sexual_img_score = 0
                violence_img_score = 0
                hate_img_score = 0
                self_harm_img_score = 0

                if hasattr(response_cs_image, 'categories_analysis') and response_cs_image.categories_analysis is not None:
                    for analysis_item in response_cs_image.categories_analysis:
                        category_str = analysis_item.category # Ini adalah enum, gunakan .value jika perlu string
                        severity = analysis_item.severity if analysis_item.severity is not None else 0
                        
                        if category_str == ImageCategory.SEXUAL:
                            sexual_img_score = severity
                        elif category_str == ImageCategory.VIOLENCE:
                            violence_img_score = severity
                        elif category_str == ImageCategory.HATE:
                            hate_img_score = severity
                        elif category_str == ImageCategory.SELF_HARM:
                            self_harm_img_score = severity
                
                logging.info(f"Input Image Content Safety Analysis: Sexual={sexual_img_score}, Violence={violence_img_score}, Hate={hate_img_score}, SelfHarm={self_harm_img_score}")

                blocked_input_image_categories = []
                if sexual_img_score >= CONTENT_SAFETY_IMAGE_THRESHOLD_SEXUAL:
                    blocked_input_image_categories.append(f"Sexual (Score: {sexual_img_score})")
                if violence_img_score >= CONTENT_SAFETY_IMAGE_THRESHOLD_VIOLENCE:
                    blocked_input_image_categories.append(f"Violence (Score: {violence_img_score})")
                if hate_img_score >= CONTENT_SAFETY_IMAGE_THRESHOLD_HATE:
                    blocked_input_image_categories.append(f"Hate (Score: {hate_img_score})")
                if self_harm_img_score >= CONTENT_SAFETY_IMAGE_THRESHOLD_SELF_HARM:
                    blocked_input_image_categories.append(f"Self-Harm (Score: {self_harm_img_score})")
                
                if blocked_input_image_categories:
                    logging.warning(f"Input image blocked by Content Safety. Categories: {', '.join(blocked_input_image_categories)}")
                    return func.HttpResponse(
                        json.dumps({"error": "Uploaded image contains inappropriate content.", "details": f"Blocked categories: {', '.join(blocked_input_image_categories)}"}),
                        mimetype="application/json",
                        status_code=400 
                    )
                logging.info("Input image passed content safety check.")
            
            except HttpResponseError as cs_http_err: # Menangkap error spesifik dari service Content Safety
                logging.error(f"Azure AI Content Safety HTTPError for image: {cs_http_err.message}", exc_info=True)
                logging.warning("Skipping image safety check due to an error with Content Safety service. Proceeding with caution to OpenAI.")
                # Anda bisa memilih untuk blokir di sini jika Content Safety adalah syarat mutlak
                # return func.HttpResponse(json.dumps({"error": "Failed to analyze image safety."}), mimetype="application/json", status_code=500)
            except Exception as cs_img_err:
                logging.error(f"Error during Azure AI Content Safety image analysis: {cs_img_err}", exc_info=True)
                logging.warning("Skipping image safety check due to an unexpected error. Proceeding with caution to OpenAI.")
                # Sama seperti di atas, pertimbangkan untuk blokir
        else:
            logging.warning("Content Safety client not available for image check, skipping image safety analysis. Proceeding to OpenAI.")
        # --- AKHIR ANALISIS KEAMANAN GAMBAR INPUT ---

        # 4. Encode gambar ke base64 SETELAH lolos Content Safety (jika lolos)
        base64_image_string = base64.b64encode(image_bytes).decode('utf-8')
        image_mime_type = image_file.content_type if image_file.content_type else "image/jpeg" # Tetap ambil dari file asli

        # 5. Inisialisasi klien Azure OpenAI
        client = AzureOpenAI(
            azure_endpoint=openai_endpoint,
            api_key=openai_key,
            api_version="2024-02-01" 
        )

        # 6. Susun prompt untuk Azure OpenAI (tetap sama)
        system_prompt_content = f"""
You are an expert language tutor AI specializing in {target_language_name} and {source_language_name}.
Analyze the provided image of an object and generate detailed information.
Provide all text outputs in {target_language_name} (code: '{target_lang_code}') AND also provide translations in {source_language_name} (code: '{source_lang_code}').
Ensure all generated text is strictly appropriate for young children, avoiding any mature themes, violence, profanity, hate speech, or self-harm references.
The descriptions should be factual, educational, and positive.
Respond ONLY with a single, valid JSON object matching the following schema:
{{
  "objectName": {{ "{target_lang_code}": "string", "{source_lang_code}": "string" }},
  "description": {{ "{target_lang_code}": "string", "{source_lang_code}": "string" }},
  "exampleSentences": [ 
    {{ "{target_lang_code}": "string", "{source_lang_code}": "string" }}, 
    {{ "{target_lang_code}": "string", "{source_lang_code}": "string" }} 
  ],
  "relatedAdjectives": [ 
    {{ "{target_lang_code}": "string", "{source_lang_code}": "string" }},
    {{ "{target_lang_code}": "string", "{source_lang_code}": "string" }}
  ]
}}
If you cannot identify the object or provide information, return an empty JSON object {{}}.
"""
        messages_payload = [
            {"role": "system", "content": system_prompt_content},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Please analyze this object and provide details in {target_language_name} with {source_language_name} translations."},
                    {"type": "image_url", "image_url": {"url": f"data:{image_mime_type};base64,{base64_image_string}"}}
                ]
            }
        ]

        # 7. Panggil Azure OpenAI (tetap sama)
        logging.info(f"Memanggil Azure OpenAI deployment '{openai_deployment_name}' untuk detail objek...")
        try:
            response = client.chat.completions.create(
                model=openai_deployment_name,
                messages=messages_payload,
                max_tokens=1000,
                temperature=0.3
            )
        except Exception as e_openai:
            logging.error(f"Error calling Azure OpenAI: {str(e_openai)}", exc_info=True)
            return func.HttpResponse(
                json.dumps({"error": "Error communicating with AI model.", "details": str(e_openai)}),
                mimetype="application/json",
                status_code=500
            )
        
        # 8. Proses respons dari Azure OpenAI (termasuk filter teks output yang sudah ada)
        if response.choices and len(response.choices) > 0:
            assistant_message = response.choices[0].message
            if assistant_message.content:
                try:
                    json_output_str = assistant_message.content.strip()
                    if json_output_str.startswith("```json"):
                        json_output_str = json_output_str[7:]
                    if json_output_str.endswith("```"):
                        json_output_str = json_output_str[:-3]
                    
                    json_output_str = json_output_str.strip()
                    parsed_json = json.loads(json_output_str)
                    logging.info(f"Respon JSON dari OpenAI berhasil di-parse.")
                    
                    # --- FILTER KEAMANAN TEKS OUTPUT (TETAP ADA) ---
                    if content_safety_client:
                        try:
                            texts_to_check_obj = []
                            # (Logika pengumpulan teks Anda sudah bagus di sini)
                            if "objectName" in parsed_json and isinstance(parsed_json["objectName"], dict):
                                texts_to_check_obj.extend(str(v) for v in parsed_json["objectName"].values() if isinstance(v, (str, int, float)))
                            if "description" in parsed_json and isinstance(parsed_json["description"], dict):
                                texts_to_check_obj.extend(str(v) for v in parsed_json["description"].values() if isinstance(v, (str, int, float)))
                            if "exampleSentences" in parsed_json and isinstance(parsed_json["exampleSentences"], list):
                                for item in parsed_json["exampleSentences"]:
                                    if isinstance(item, dict):
                                        texts_to_check_obj.extend(str(v) for v in item.values() if isinstance(v, (str, int, float)))
                            if "relatedAdjectives" in parsed_json and isinstance(parsed_json["relatedAdjectives"], list):
                                for item in parsed_json["relatedAdjectives"]:
                                    if isinstance(item, dict):
                                        texts_to_check_obj.extend(str(v) for v in item.values() if isinstance(v, (str, int, float)))
                            
                            combined_text_output_obj = " . ".join(filter(None, texts_to_check_obj))

                            if combined_text_output_obj:
                                logging.info(f"Performing content safety analysis on generated object details output (length: {len(combined_text_output_obj)})...")
                                analyze_output_request_obj = AnalyzeTextOptions(
                                    text=combined_text_output_obj,
                                    categories=[TextCategory.SEXUAL, TextCategory.VIOLENCE, TextCategory.HATE, TextCategory.SELF_HARM]
                                )
                                response_output_safety_obj = content_safety_client.analyze_text(analyze_output_request_obj)
                                
                                blocked_output_categories_obj = []
                                if response_output_safety_obj and hasattr(response_output_safety_obj, 'categories_analysis'):
                                    for category_result in response_output_safety_obj.categories_analysis:
                                        if category_result.severity >= CONTENT_SAFETY_TEXT_THRESHOLD:
                                            blocked_output_categories_obj.append(f"{category_result.category.value if hasattr(category_result.category, 'value') else category_result.category} (Score: {category_result.severity})")

                                if blocked_output_categories_obj:
                                    logging.warning(f"Generated object details content blocked by Content Safety. Categories: {', '.join(blocked_output_categories_obj)}")
                                    return func.HttpResponse(
                                        json.dumps({"error": "Generated object details were found to be inappropriate and has been blocked."}),
                                        mimetype="application/json",
                                        status_code=500 
                                    )
                                logging.info("Generated object details content passed content safety check.")
                        except Exception as output_safety_err_obj:
                            logging.error(f"Error during content safety analysis for generated object details: {output_safety_err_obj}", exc_info=True)
                            return func.HttpResponse(
                                json.dumps({"error": "Failed to verify safety of generated object details."}),
                                mimetype="application/json",
                                status_code=500
                            )
                    # --- AKHIR FILTER KEAMANAN TEKS OUTPUT ---

                    # ---- BLOK KODE UNTUK FILTER OBJEK BERDASARKAN NAMA (OPSIONAL, JIKA DIPERLUKAN) ----
                    # FORBIDDEN_OBJECT_KEYWORDS_EN = ["handgun", "pistol", "gun", "rifle", "weapon", "knife", "blade"] 
                    # FORBIDDEN_OBJECT_KEYWORDS_ID = ["pistol", "senjata", "senapan", "pisau", "belati"] 

                    # object_name_en = parsed_json.get("objectName", {}).get(target_lang_code, "").lower()
                    # object_name_id = parsed_json.get("objectName", {}).get(source_lang_code, "").lower()

                    # is_forbidden_by_name = False
                    # if any(keyword in object_name_en for keyword in FORBIDDEN_OBJECT_KEYWORDS_EN):
                    #     is_forbidden_by_name = True
                    # if any(keyword in object_name_id for keyword in FORBIDDEN_OBJECT_KEYWORDS_ID):
                    #     is_forbidden_by_name = True
                    
                    # if is_forbidden_by_name:
                    #     logging.warning(f"Object '{object_name_en}/{object_name_id}' is on the forbidden list by name. Blocking details.")
                    #     return func.HttpResponse(
                    #         json.dumps({"error": "Details for this type of object are not available.", "reason": "Object type restricted by name"}),
                    #         mimetype="application/json",
                    #         status_code=403 # Forbidden
                    #     )
                    # ---- AKHIR BLOK KODE FILTER OBJEK BERDASARKAN NAMA ----


                    return func.HttpResponse(
                        body=json.dumps(parsed_json),
                        mimetype="application/json",
                        status_code=200
                    )
                # ... (sisa error handling Anda sudah bagus) ...
                except json.JSONDecodeError as json_err:
                    logging.error(f"Gagal mem-parse JSON dari respons OpenAI: {json_err}")
                    logging.error(f"Respons mentah dari OpenAI: {assistant_message.content}")
                    return func.HttpResponse(json.dumps({"error": "AI model returned non-JSON content or malformed JSON."}),mimetype="application/json",status_code=500)
            else:
                logging.warning("Respons OpenAI tidak memiliki konten.")
                return func.HttpResponse(json.dumps({"error": "AI model returned no content."}),mimetype="application/json",status_code=500)
        else:
            logging.warning("Respons OpenAI tidak memiliki choices.")
            return func.HttpResponse(json.dumps({"error": "AI model returned no choices."}),mimetype="application/json",status_code=500)

    except ValueError as ve:
        logging.error(f"ValueError: {str(ve)}")
        return func.HttpResponse(json.dumps({"error": f"Invalid input: {str(ve)}"}),mimetype="application/json",status_code=400)
    except Exception as e:
        logging.error(f"Terjadi kesalahan internal: {str(e)}", exc_info=True)
        return func.HttpResponse(json.dumps({"error": "Terjadi kesalahan pada server saat memproses detail objek.", "details": str(e)}),mimetype="application/json",status_code=500)