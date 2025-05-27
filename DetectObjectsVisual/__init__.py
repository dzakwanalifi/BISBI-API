import logging
import os
import azure.functions as func
import json
import requests 
from PIL import Image 
import io 
from . import utils # Import helper functions

# --- KONFIGURASI ---
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
HF_MODEL_ID = os.environ.get("HF_MODEL_ID", "facebook/detr-resnet-50")
HF_INFERENCE_API_URL_TEMPLATE = os.environ.get("HF_INFERENCE_API_URL_TEMPLATE", "https://router.huggingface.co/hf-inference/models/{model_id}")
HF_OBJECT_DETECTION_URL = HF_INFERENCE_API_URL_TEMPLATE.format(model_id=HF_MODEL_ID)

NMS_IOU_THRESHOLD = float(os.environ.get("NMS_IOU_THRESHOLD", 0.4))
NMS_SCORE_THRESHOLD = float(os.environ.get("NMS_SCORE_THRESHOLD", 0.5))
REQUESTS_TIMEOUT_SECONDS = int(os.environ.get("REQUESTS_TIMEOUT_SECONDS", 30))
MAX_IMAGE_UPLOAD_SIZE_BYTES = int(os.environ.get("MAX_IMAGE_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024)) # 10MB default


# ----- VALIDASI KONFIGURASI AWAL -----
if not HF_API_TOKEN:
    logging.error("CRITICAL: HF_API_TOKEN environment variable not set at startup.")
    # Anda bisa memilih untuk raise error di sini untuk menghentikan inisialisasi fungsi jika token tidak ada
    # raise EnvironmentError("HF_API_TOKEN must be set") 


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f'Python HTTP trigger function processed a request for DetectObjectsVisual. Model: {HF_MODEL_ID}')

    if not HF_API_TOKEN: # Cek lagi di dalam fungsi jika tidak di-raise saat startup
        logging.error("HuggingFace token not configured. Cannot process request.")
        return func.HttpResponse(
             json.dumps({"error": "Server configuration error: HuggingFace token not available."}),
             mimetype="application/json",
             status_code=500
        )

    try:
        image_file = req.files.get('image')
        if not image_file:
            logging.warning("No image file received.")
            return func.HttpResponse(
                json.dumps({"error": "Please upload an image file with the field name 'image'"}),
                mimetype="application/json",
                status_code=400
            )

        image_bytes = image_file.read()

        if not image_bytes:
            logging.warning("Received an empty image file.")
            return func.HttpResponse(
                json.dumps({"error": "Image file is empty. Please upload a valid image."}),
                mimetype="application/json",
                status_code=400
            )
        
        if len(image_bytes) > MAX_IMAGE_UPLOAD_SIZE_BYTES:
            logging.warning(f"Image file size {len(image_bytes)} bytes exceeds limit of {MAX_IMAGE_UPLOAD_SIZE_BYTES} bytes.")
            return func.HttpResponse(
                json.dumps({"error": f"Image file too large. Maximum size is {MAX_IMAGE_UPLOAD_SIZE_BYTES // (1024*1024)}MB."}),
                mimetype="application/json",
                status_code=413 # Payload Too Large
            )

        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG')
            processed_image_bytes = img_byte_arr.getvalue()
            
            logging.info(f"PIL processing successful. Image format forced to JPEG. Mode: {pil_image.mode}. Size: {pil_image.size}. Length: {len(processed_image_bytes)}")

        except Exception as img_err:
            logging.error(f"Failed to open or process image with PIL: {img_err}", exc_info=True)
            return func.HttpResponse(
                json.dumps({"error": "Invalid image format or error during image pre-processing."}),
                mimetype="application/json",
                status_code=400
            )

        logging.info("Sending image to HuggingFace for object detection using manual requests...")
        
        headers_hf = {
            "Authorization": f"Bearer {HF_API_TOKEN}",
            "Content-Type": "image/jpeg" 
        }
        
        response_hf_data = None

        try:
            logging.debug(f"Attempting POST to: {HF_OBJECT_DETECTION_URL} with timeout {REQUESTS_TIMEOUT_SECONDS}s")
            # logging.debug(f"POST Headers: {headers_hf}") # Sensitive, token might be logged

            api_response = requests.post(HF_OBJECT_DETECTION_URL, headers=headers_hf, data=processed_image_bytes, timeout=REQUESTS_TIMEOUT_SECONDS)
            api_response.raise_for_status()
            
            response_hf_data = api_response.json()
            logging.info(f"Manual POST successful. Received {len(response_hf_data) if isinstance(response_hf_data, list) else 'a non-list response'} items from HuggingFace.")
            logging.debug(f"Full response from HuggingFace: {response_hf_data}")

        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HuggingFace API HTTPError: {http_err}", exc_info=True)
            error_content = "Unknown error from HuggingFace."
            status_code_return = 502 # Default Bad Gateway for upstream errors
            if http_err.response is not None:
                logging.error(f"HF Response Status: {http_err.response.status_code}")
                logging.error(f"HF Response Headers: {http_err.response.headers}")
                try:
                    error_content = http_err.response.json()
                except json.JSONDecodeError:
                    error_content = http_err.response.text
                logging.error(f"HF Response Content: {error_content}")
                if 400 <= http_err.response.status_code < 500:
                    status_code_return = 400 # Client error from HF, pass as client error
                elif http_err.response.status_code >= 500:
                    status_code_return = 502 # Server error from HF, treat as Bad Gateway
            return func.HttpResponse(
                 json.dumps({"error": "Error communicating with HuggingFace service.", "details": error_content}),
                 mimetype="application/json",
                 status_code=status_code_return
            )
        except requests.exceptions.RequestException as req_err: 
            logging.error(f"HuggingFace API RequestException (e.g., timeout, DNS error): {req_err}", exc_info=True)
            return func.HttpResponse(
                 json.dumps({"error": "Network error or timeout communicating with HuggingFace service."}),
                 mimetype="application/json",
                 status_code=504 # Gateway Timeout
            )
        except json.JSONDecodeError as json_err:
            logging.error(f"Failed to decode JSON response from HuggingFace: {json_err}", exc_info=True)
            raw_response_text = "N/A"
            if 'api_response' in locals() and hasattr(api_response, 'text'):
                raw_response_text = api_response.text
            logging.error(f"Raw response content that failed to parse: {raw_response_text}")
            return func.HttpResponse(
                json.dumps({"error": "Received non-JSON or malformed JSON response from HuggingFace service."}),
                mimetype="application/json",
                status_code=502 # Bad Gateway, as upstream service returned invalid data
            )
            
        logging.debug(f"Received response from HuggingFace: {response_hf_data}")

        if not isinstance(response_hf_data, list):
            logging.error(f"Unexpected response type from HF. Expected list, got {type(response_hf_data)}. Response: {response_hf_data}")
            return func.HttpResponse(
                json.dumps({"error": "Error processing detection results: Unexpected format from upstream service."}),
                mimetype="application/json",
                status_code=500
            )
        
        bisbi_detections = []
        for idx, detection_hf in enumerate(response_hf_data):
            if not isinstance(detection_hf, dict) or not all(k in detection_hf for k in ('score', 'label', 'box')):
                logging.warning(f"Skipping malformed detection object at index {idx} from HF: {detection_hf}")
                continue
            if not isinstance(detection_hf['box'], dict) or not all(k in detection_hf['box'] for k in ('xmin', 'ymin', 'xmax', 'ymax')):
                logging.warning(f"Skipping detection with malformed 'box' at index {idx} from HF: {detection_hf}")
                continue
            
            label = detection_hf.get('label', 'unknown')
            score = detection_hf.get('score', 0.0)
            box_hf = detection_hf.get('box', {})
            
            xmin = box_hf.get('xmin', 0)
            ymin = box_hf.get('ymin', 0)
            xmax = box_hf.get('xmax', 0)
            ymax = box_hf.get('ymax', 0)

            bisbi_detections.append({
                "objectName": label,
                "confidence": round(float(score), 3),
                "boundingBox": {
                    "x": round(float(xmin), 2),
                    "y": round(float(ymin), 2),
                    "width": round(float(xmax - xmin), 2),
                    "height": round(float(ymax - ymin), 2)
                }
            })
            
        logging.info(f"Number of valid detections before NMS: {len(bisbi_detections)}")
        
        final_detections = utils.apply_nms(bisbi_detections, iou_threshold=NMS_IOU_THRESHOLD, score_threshold=NMS_SCORE_THRESHOLD)
        logging.info(f"Number of detections after NMS (IoU: {NMS_IOU_THRESHOLD}, Score: {NMS_SCORE_THRESHOLD}): {len(final_detections)}")

        return func.HttpResponse(
            body=json.dumps(final_detections),
            mimetype="application/json",
            status_code=200
        )

    except ValueError as ve: 
        logging.error(f"ValueError during request processing: {str(ve)}", exc_info=True)
        return func.HttpResponse(json.dumps({"error": f"Invalid input: {str(ve)}"}), mimetype="application/json", status_code=400)
    except Exception as e:
        logging.error(f"An unexpected internal error occurred: {str(e)}", exc_info=True)
        return func.HttpResponse(json.dumps({"error": "An unexpected server error occurred while processing the image."}), mimetype="application/json", status_code=500)

# Functions calculate_iou and apply_nms are now in utils.py