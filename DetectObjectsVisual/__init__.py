import logging
import os
import azure.functions as func
import json
import requests
from PIL import Image
import io
from . import utils # Import helper functions

# Import SDK Azure AI Content Safety
from azure.ai.contentsafety import ContentSafetyClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.ai.contentsafety.models import AnalyzeImageOptions, ImageData, ImageCategory

# Import HuggingFace Hub client
from huggingface_hub import InferenceClient
from huggingface_hub.utils import HfHubHTTPError

# --- KONFIGURASI ---
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
HF_MODEL_ID = os.environ.get("HF_MODEL_ID", "facebook/detr-resnet-50")
# HF_INFERENCE_API_URL_TEMPLATE = os.environ.get("HF_INFERENCE_API_URL_TEMPLATE", "https://api-inference.huggingface.co/models/{model_id}") # Not used with InferenceClient
# HF_OBJECT_DETECTION_URL = HF_INFERENCE_API_URL_TEMPLATE.format(model_id=HF_MODEL_ID) # Not used with InferenceClient

NMS_IOU_THRESHOLD = float(os.environ.get("NMS_IOU_THRESHOLD", 0.4))
NMS_SCORE_THRESHOLD = float(os.environ.get("NMS_SCORE_THRESHOLD", 0.5)) # Ensure this is used
REQUESTS_TIMEOUT_SECONDS = int(os.environ.get("REQUESTS_TIMEOUT_SECONDS", 30))
MAX_IMAGE_UPLOAD_SIZE_BYTES = int(os.environ.get("MAX_IMAGE_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024)) # 10MB default

# Konfigurasi Azure AI Content Safety
CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
CONTENT_SAFETY_KEY = os.environ.get("CONTENT_SAFETY_KEY")

CONTENT_SAFETY_THRESHOLD_SEXUAL = 1
CONTENT_SAFETY_THRESHOLD_VIOLENCE = 1
CONTENT_SAFETY_THRESHOLD_HATE = 1  # Tambahkan ini
CONTENT_SAFETY_THRESHOLD_SELF_HARM = 1 # Tambahkan ini

# ----- VALIDASI KONFIGURASI AWAL -----
if not HF_API_TOKEN:
    logging.error("CRITICAL: HF_API_TOKEN environment variable not set at startup.")

content_safety_client = None
if CONTENT_SAFETY_ENDPOINT and CONTENT_SAFETY_KEY:
    try:
        content_safety_client = ContentSafetyClient(CONTENT_SAFETY_ENDPOINT, AzureKeyCredential(CONTENT_SAFETY_KEY))
        logging.info("Azure AI Content Safety client initialized successfully.")
    except Exception as cs_init_err:
        logging.error(f"Failed to initialize Azure AI Content Safety client: {cs_init_err}", exc_info=True)
        content_safety_client = None
else:
    logging.warning("Azure AI Content Safety endpoint or key not configured. Image safety analysis will be skipped.")

hf_inference_client_instance = None


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f'Python HTTP trigger function processed a request for DetectObjectsVisual. Model: {HF_MODEL_ID}')

    global hf_inference_client_instance

    if hf_inference_client_instance is None:
        HF_API_TOKEN_FUNC_LEVEL = os.environ.get("HF_API_TOKEN")
        if HF_API_TOKEN_FUNC_LEVEL:
            try:
                hf_inference_client_instance = InferenceClient(
                    token=HF_API_TOKEN_FUNC_LEVEL,
                    timeout=REQUESTS_TIMEOUT_SECONDS,
                    headers={"Content-Type": "image/jpeg"} # Ensure this header is present
                )
                logging.info(f"HuggingFace InferenceClient initialized successfully inside handler with timeout: {REQUESTS_TIMEOUT_SECONDS}s, Content-Type: image/jpeg (using default endpoint).")
            except Exception as hf_init_err:
                logging.error(f"Failed to initialize HuggingFace InferenceClient inside handler: {hf_init_err}", exc_info=True)
        else:
            logging.error("HF_API_TOKEN not configured. Cannot initialize HuggingFace InferenceClient.")
    
    if hf_inference_client_instance is None:
        logging.error("HuggingFace InferenceClient could not be initialized or is not available.")
        return func.HttpResponse(
             json.dumps({"error": "Server configuration error: HuggingFace client initialization failed."}),
             mimetype="application/json",
             status_code=500
        )

    try:
        image_file = req.files.get('image')
        if not image_file:
            logging.warning("Image file not found in request.")
            return func.HttpResponse(json.dumps({"error": "Image file is required."}), mimetype="application/json", status_code=400)

        image_bytes = image_file.read()
        if not image_bytes:
            logging.warning("Image file is empty.")
            return func.HttpResponse(json.dumps({"error": "Image file cannot be empty."}), mimetype="application/json", status_code=400)
        
        if len(image_bytes) > MAX_IMAGE_UPLOAD_SIZE_BYTES:
            logging.warning(f"Image size {len(image_bytes) / (1024*1024):.2f}MB exceeds limit of {MAX_IMAGE_UPLOAD_SIZE_BYTES / (1024*1024):.2f}MB.")
            return func.HttpResponse(
                json.dumps({"error": f"Image size exceeds the limit of {MAX_IMAGE_UPLOAD_SIZE_BYTES // (1024*1024)}MB."}),
                mimetype="application/json",
                status_code=413
            )
        
        logging.info(f"Received image: {image_file.filename}, size: {len(image_bytes)} bytes, type: {image_file.content_type}")

        # --- ANALISIS KEAMANAN GAMBAR DENGAN AZURE AI CONTENT SAFETY ---
        if content_safety_client:
            try:
                logging.info("Performing image safety analysis with Azure AI Content Safety...")
                image_data_for_cs = ImageData(content=image_bytes)
                request_cs = AnalyzeImageOptions(image=image_data_for_cs, categories=[
                    ImageCategory.SEXUAL, 
                    ImageCategory.VIOLENCE,
                    ImageCategory.HATE,         # Tambahkan ini
                    ImageCategory.SELF_HARM     # Tambahkan ini
                ])
                response_cs = content_safety_client.analyze_image(request_cs)
                
                logging.info(f"Raw Content Safety Response Object: {vars(response_cs)}")
                logging.info(f"ImageCategory.SEXUAL.value is: '{ImageCategory.SEXUAL.value}'") # For debug
                logging.info(f"ImageCategory.VIOLENCE.value is: '{ImageCategory.VIOLENCE.value}'") # For debug
                logging.info(f"ImageCategory.HATE.value is: '{ImageCategory.HATE.value}'") # For debug
                logging.info(f"ImageCategory.SELF_HARM.value is: '{ImageCategory.SELF_HARM.value}'") # For debug


                sexual_score_val = 0
                violence_score_val = 0
                hate_score_val = 0
                self_harm_score_val = 0

                # Prefer parsing the structured 'categories_analysis' attribute if available and correct
                # Based on the error, analysis_item.category is already a string.
                if hasattr(response_cs, 'categories_analysis') and response_cs.categories_analysis is not None:
                    logging.debug("Parsing Content Safety results using 'categories_analysis' public attribute.")
                    for analysis_item in response_cs.categories_analysis:
                        # analysis_item is azure.ai.contentsafety.models.ImageCategoryAnalysis
                        # Assuming analysis_item.category is a string "Sexual", "Violence", etc.
                        category_str_from_sdk = analysis_item.category
                        severity_from_sdk = analysis_item.severity if analysis_item.severity is not None else 0
                        
                        logging.info(f"CS SDK Public Prop: Category='{category_str_from_sdk}', Severity={severity_from_sdk}")

                        if category_str_from_sdk == ImageCategory.SEXUAL.value: # Compare string with enum's string value
                            sexual_score_val = severity_from_sdk
                        elif category_str_from_sdk == ImageCategory.VIOLENCE.value: # Compare string with enum's string value
                            violence_score_val = severity_from_sdk
                        elif category_str_from_sdk == ImageCategory.HATE.value:
                            hate_score_val = severity_from_sdk
                        elif category_str_from_sdk == ImageCategory.SELF_HARM.value:
                            self_harm_score_val = severity_from_sdk
                
                # Fallback or primary if _data is more reliable based on SDK version behavior
                # The previous logs showed _data being populated. Let's use that structure primarily.
                elif hasattr(response_cs, '_data') and isinstance(response_cs._data, dict) and \
                   'categoriesAnalysis' in response_cs._data and isinstance(response_cs._data['categoriesAnalysis'], list):
                    logging.debug("Parsing Content Safety results using '_data[categoriesAnalysis]' internal structure.")
                    for category_analysis_item in response_cs._data['categoriesAnalysis']:
                        if isinstance(category_analysis_item, dict):
                            category_name_from_resp = category_analysis_item.get('category') # String: "Sexual", "Violence"
                            severity_score = category_analysis_item.get('severity')

                            logging.info(f"CS Raw Item from _data: Category='{category_name_from_resp}', Severity={severity_score}")
                            
                            if severity_score is not None:
                                if category_name_from_resp == ImageCategory.SEXUAL.value:
                                    sexual_score_val = int(severity_score)
                                elif category_name_from_resp == ImageCategory.VIOLENCE.value:
                                    violence_score_val = int(severity_score)
                                elif category_name_from_resp == ImageCategory.HATE.value:
                                    hate_score_val = int(severity_score)
                                elif category_name_from_resp == ImageCategory.SELF_HARM.value:
                                    self_harm_score_val = int(severity_score)
                else:
                    logging.warning("Content Safety response structure not as expected (neither 'categories_analysis' nor '_data' suitable).")

                logging.info(f"Content Safety Analysis Result (Parsed): Sexual={sexual_score_val}, Violence={violence_score_val}, Hate={hate_score_val}, SelfHarm={self_harm_score_val}") 

                blocked_categories = []
                if sexual_score_val >= CONTENT_SAFETY_THRESHOLD_SEXUAL:
                    blocked_categories.append(f"Sexual (Score: {sexual_score_val})")
                if violence_score_val >= CONTENT_SAFETY_THRESHOLD_VIOLENCE:
                    blocked_categories.append(f"Violence (Score: {violence_score_val})")
                if hate_score_val >= CONTENT_SAFETY_THRESHOLD_HATE: # Tambahkan pemeriksaan ini
                    blocked_categories.append(f"Hate (Score: {hate_score_val})")
                if self_harm_score_val >= CONTENT_SAFETY_THRESHOLD_SELF_HARM: # Tambahkan pemeriksaan ini
                    blocked_categories.append(f"Self-Harm (Score: {self_harm_score_val})")
                
                if blocked_categories:
                    logging.warning(f"Image blocked by Content Safety. Categories: {', '.join(blocked_categories)}")
                    return func.HttpResponse(
                        json.dumps({"error": "Image cannot be processed due to safety concerns.", "details": f"Blocked categories: {', '.join(blocked_categories)}"}),
                        mimetype="application/json",
                        status_code=400
                    )
                else:
                    logging.info("Image passed safety analysis.")
            
            except AttributeError as attr_err:
                logging.error(f"Azure AI Content Safety AttributeError (e.g., ImageCategory enum issue or unexpected response structure): {attr_err}", exc_info=True)
                logging.warning("Skipping image safety check due to an SDK/configuration error with Content Safety. Proceeding with object detection.")
            except HttpResponseError as cs_http_err:
                logging.error(f"Azure AI Content Safety HTTPError: {cs_http_err.message}", exc_info=True)
                logging.warning("Skipping image safety check due to an error with Content Safety service. Proceeding with object detection.")
            except Exception as cs_err:
                logging.error(f"Error during Azure AI Content Safety analysis: {cs_err}", exc_info=True)
                logging.warning("Skipping image safety check due to an unexpected error. Proceeding with object detection.")
        else:
            logging.info("Content Safety client not available, skipping image safety analysis.")
        # --- AKHIR ANALISIS KEAMANAN GAMBAR ---

        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG')
            processed_image_bytes_for_hf = img_byte_arr.getvalue()
            logging.info(f"PIL processing successful for HF. Image format forced to JPEG. Length: {len(processed_image_bytes_for_hf)}")

        except Exception as img_err:
            logging.error(f"Failed to open or process image with PIL for HuggingFace: {img_err}", exc_info=True)
            return func.HttpResponse(
                json.dumps({"error": "Invalid image format or error during image pre-processing for detection."}),
                mimetype="application/json",
                status_code=400
            )

        response_hf_data = None
        try:
            logging.info(f"Sending image to HuggingFace model {HF_MODEL_ID} using InferenceClient...")
            response_hf_data_sdk = hf_inference_client_instance.object_detection(
                image=processed_image_bytes_for_hf, 
                model=HF_MODEL_ID
            )
            
            if isinstance(response_hf_data_sdk, list):
                response_hf_data = []
                for item in response_hf_data_sdk:
                    if hasattr(item, 'model_dump'):
                        response_hf_data.append(item.model_dump())
                    elif hasattr(item, 'dict'):
                        response_hf_data.append(item.dict())
                    elif isinstance(item, dict):
                        response_hf_data.append(item)
                    else:
                        logging.warning(f"Unexpected item type in InferenceClient response: {type(item)}")
                        response_hf_data.append(str(item)) # Convert to str if unknown
            elif isinstance(response_hf_data_sdk, dict) and "error" in response_hf_data_sdk:
                error_detail_hf = response_hf_data_sdk.get('error', 'Unknown error from HuggingFace service')
                logging.error(f"HuggingFace service returned an error: {error_detail_hf}")
                return func.HttpResponse(
                    json.dumps({"error": "Error from HuggingFace object detection service.", "details": error_detail_hf}),
                    mimetype="application/json",
                    status_code=502
                )
            else:
                logging.error(f"Unexpected response type from InferenceClient: {type(response_hf_data_sdk)}. Content: {response_hf_data_sdk}")
                response_hf_data = []

            logging.info(f"InferenceClient call successful. Received {len(response_hf_data) if isinstance(response_hf_data, list) else 'a non-list response'} detection items.")
            logging.debug(f"Full response from HuggingFace (InferenceClient): {response_hf_data}")

        except HfHubHTTPError as hf_http_err:
            logging.error(f"HuggingFace InferenceClient HfHubHTTPError: {hf_http_err}", exc_info=True)
            error_detail = f"Error communicating with HuggingFace service via SDK: {str(hf_http_err)}"
            status_code_return = 502
            if hasattr(hf_http_err, 'response') and hf_http_err.response is not None:
                logging.error(f"HF SDK Response Status: {hf_http_err.response.status_code}")
                try:
                    err_content = hf_http_err.response.json()
                    logging.error(f"HF SDK Response JSON Content: {err_content}")
                    extracted_error = err_content.get("error", error_detail)
                    if isinstance(extracted_error, dict) and "message" in extracted_error: error_detail = extracted_error["message"]
                    elif isinstance(extracted_error, str): error_detail = extracted_error
                except json.JSONDecodeError:
                    logging.error(f"HF SDK Response Text Content: {hf_http_err.response.text}")
                    error_detail = hf_http_err.response.text if hf_http_err.response.text else error_detail
                if 400 <= hf_http_err.response.status_code < 500: status_code_return = hf_http_err.response.status_code
            return func.HttpResponse(json.dumps({"error": "HuggingFace service error.", "details": error_detail}), mimetype="application/json", status_code=status_code_return)
        except requests.exceptions.Timeout:
            logging.error(f"Request to Hugging Face API (SDK) timed out after {REQUESTS_TIMEOUT_SECONDS} seconds.", exc_info=True)
            return func.HttpResponse(json.dumps({"error": "Object detection service (SDK) timed out."}), mimetype="application/json", status_code=504)
        except Exception as hf_sdk_err:
            logging.error(f"General error with HuggingFace InferenceClient: {hf_sdk_err}", exc_info=True)
            return func.HttpResponse(json.dumps({"error": "Failed to process image with HuggingFace SDK.", "details": str(hf_sdk_err)}), mimetype="application/json", status_code=500)

        if not isinstance(response_hf_data, list):
            logging.error(f"Unexpected data format for transformation (SDK): {type(response_hf_data)}. Expected a list.")
            return func.HttpResponse(json.dumps({"error": "Unexpected data format from object detection service (SDK) for further processing."}), mimetype="application/json", status_code=500)

        # Use the newly defined transformation function
        transformed_results = utils.transform_hf_predictions_to_custom_format(response_hf_data)
        logging.info(f"Transformed {len(transformed_results)} predictions.")
        
        # Correct NMS function call and pass score_threshold
        final_results = utils.apply_nms(
            transformed_results, 
            iou_threshold=NMS_IOU_THRESHOLD, 
            score_threshold=NMS_SCORE_THRESHOLD  # Pass the score threshold
        )
        logging.info(f"Applied Non-Max Suppression (IoU: {NMS_IOU_THRESHOLD}, Score: {NMS_SCORE_THRESHOLD}), {len(final_results)} predictions remaining.")

        return func.HttpResponse(json.dumps({"predictions": final_results}), mimetype="application/json", status_code=200)

    # Keep general exception handlers (Timeout, RequestException, ValueError, generic Exception) as they were
    except requests.exceptions.Timeout: # This would be for the old `requests.post` if it were still used
        logging.error(f"Request to Hugging Face API timed out after {REQUESTS_TIMEOUT_SECONDS} seconds (direct requests).", exc_info=True)
        return func.HttpResponse(json.dumps({"error": "Object detection service timed out."}), mimetype="application/json", status_code=504)
    except requests.exceptions.RequestException as req_err: # Also for old `requests.post`
        logging.error(f"Error calling Hugging Face API (direct requests): {req_err}", exc_info=True)
        error_detail = "Failed to communicate with object detection service."
        if req_err.response is not None:
            try: error_detail = req_err.response.json().get("error", error_detail)
            except json.JSONDecodeError: logging.error(f"HF Response Status: {req_err.response.status_code}, Content (not JSON): {req_err.response.text}")
        return func.HttpResponse(json.dumps({"error": error_detail}), mimetype="application/json", status_code=502)
    except ValueError as ve:
        logging.error(f"ValueError during processing: {ve}", exc_info=True)
        return func.HttpResponse(json.dumps({"error": f"Error processing data: {str(ve)}"}), mimetype="application/json", status_code=500)
    except Exception as e:
        logging.error(f"An unexpected error occurred in DetectObjectsVisual: {e}", exc_info=True)
        return func.HttpResponse(json.dumps({"error": "An unexpected error occurred."}), mimetype="application/json", status_code=500)