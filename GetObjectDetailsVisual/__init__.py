import logging
import os
import json
import base64 # Untuk encode gambar ke base64
import azure.functions as func

# Import SDK untuk Azure OpenAI
from openai import AzureOpenAI # Pastikan versi openai >= 1.0.0

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request for GetObjectDetailsVisual.')

    try:
        # 1. Ambil konfigurasi dari environment variables
        openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        openai_key = os.environ.get("AZURE_OPENAI_KEY")
        openai_deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME") # Nama deployment gpt-4.1 Anda

        if not all([openai_endpoint, openai_key, openai_deployment_name]):
            logging.error("Konfigurasi Azure OpenAI tidak lengkap.")
            return func.HttpResponse("Error: Server configuration missing for OpenAI.", status_code=500)

        # 2. Dapatkan file gambar dan parameter bahasa dari request
        image_file = req.files.get('image')
        # Ambil parameter dari form-data jika ada, jika tidak dari query params, lalu default
        target_lang_code = req.form.get('targetLanguage', req.params.get('targetLanguage', 'en'))
        source_lang_code = req.form.get('sourceLanguage', req.params.get('sourceLanguage', 'id'))
        
        # Mapping sederhana untuk nama bahasa (bisa diperluas)
        lang_names = {"en": "English", "id": "Indonesian"}
        target_language_name = lang_names.get(target_lang_code, "English")
        source_language_name = lang_names.get(source_lang_code, "Indonesian")


        if not image_file:
            logging.warning("Tidak ada file gambar yang diterima.")
            return func.HttpResponse("Harap unggah file gambar (cropped object) dengan field name 'image'.", status_code=400)
        
        # 3. Baca dan encode gambar ke base64
        image_bytes = image_file.read()
        base64_image_string = base64.b64encode(image_bytes).decode('utf-8')
        
        # Asumsi format gambar umum (JPEG/PNG), sesuaikan jika perlu
        # Untuk DALL-E atau model vision, biasanya cukup 'image/jpeg' atau 'image/png'
        image_mime_type = image_file.content_type if image_file.content_type else "image/jpeg"


        # 4. Inisialisasi klien Azure OpenAI
        client = AzureOpenAI(
            azure_endpoint=openai_endpoint,
            api_key=openai_key,
            api_version="2024-02-01" # Gunakan versi API yang mendukung model vision Anda (cek dokumentasi)
                                     # Contoh: "2023-12-01-preview", "2024-02-15-preview", atau versi GA yang sesuai
        )

        # 5. Susun prompt untuk Azure OpenAI
        system_prompt_content = f"""
You are an expert language tutor AI specializing in {target_language_name} and {source_language_name}.
Analyze the provided image of an object and generate detailed information.
Provide all text outputs in {target_language_name} (code: '{target_lang_code}') AND also provide translations in {source_language_name} (code: '{source_lang_code}').
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

        # 6. Panggil Azure OpenAI
        logging.info(f"Memanggil Azure OpenAI deployment '{openai_deployment_name}' untuk detail objek...")
        try:
            response = client.chat.completions.create(
                model=openai_deployment_name, # Nama deployment gpt-4.1 Anda
                messages=messages_payload,
                max_tokens=1000, # Sesuaikan sesuai kebutuhan
                temperature=0.3 # Lebih rendah untuk output yang lebih faktual dan terstruktur
            )
        except Exception as e_openai:
            logging.error(f"Error calling Azure OpenAI: {str(e_openai)}")
            import traceback
            logging.error(traceback.format_exc())
            return func.HttpResponse("Error communicating with AI model.", status_code=500)
        
        # 7. Proses respons dari Azure OpenAI
        if response.choices and len(response.choices) > 0:
            assistant_message = response.choices[0].message
            if assistant_message.content:
                try:
                    # Model diharapkan mengembalikan string JSON
                    json_output_str = assistant_message.content.strip()
                    # Hapus ```json ... ``` jika model menambahkannya
                    if json_output_str.startswith("```json"):
                        json_output_str = json_output_str[7:]
                    if json_output_str.endswith("```"):
                        json_output_str = json_output_str[:-3]
                    
                    json_output_str = json_output_str.strip()
                    parsed_json = json.loads(json_output_str)
                    logging.info(f"Respon JSON dari OpenAI berhasil di-parse.")
                    
                    # (Opsional) Validasi sederhana apakah struktur utama ada
                    # if not all(k in parsed_json for k in []):
                    #     logging.warning(f"Respon JSON dari OpenAI tidak memiliki semua kunci yang diharapkan: {parsed_json}")
                    #     # Anda bisa memilih untuk tetap mengembalikan apa yang ada, atau error
                    #     # return func.HttpResponse("AI model returned an unexpected JSON structure.", status_code=500)


                    return func.HttpResponse(
                        body=json.dumps(parsed_json), # Kembalikan JSON yang sudah diparsing dan di-dump lagi
                        mimetype="application/json",
                        status_code=200
                    )
                except json.JSONDecodeError as json_err:
                    logging.error(f"Gagal mem-parse JSON dari respons OpenAI: {json_err}")
                    logging.error(f"Respons mentah dari OpenAI: {assistant_message.content}")
                    return func.HttpResponse("AI model returned non-JSON content.", status_code=500)
            else:
                logging.warning("Respons OpenAI tidak memiliki konten.")
                return func.HttpResponse("AI model returned no content.", status_code=500)
        else:
            logging.warning("Respons OpenAI tidak memiliki choices.")
            return func.HttpResponse("AI model returned no choices.", status_code=500)

    except ValueError as ve:
        logging.error(f"ValueError: {str(ve)}")
        return func.HttpResponse(f"Invalid input: {str(ve)}", status_code=400)
    except Exception as e:
        logging.error(f"Terjadi kesalahan internal: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return func.HttpResponse("Terjadi kesalahan pada server saat memproses detail objek.", status_code=500)