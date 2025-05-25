import logging
import os
import azure.functions as func
import json # Tambahkan import json

from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures, DetectedObject # Impor DetectedObject
from azure.core.credentials import AzureKeyCredential

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request for DetectObjectsVisual.')

    try:
        ai_services_endpoint = os.environ.get("AZURE_AI_SERVICES_ENDPOINT")
        ai_services_key = os.environ.get("AZURE_AI_SERVICES_KEY")

        if not ai_services_endpoint or not ai_services_key:
            logging.error("Azure AI Services endpoint atau key tidak dikonfigurasi.")
            return func.HttpResponse(
                json.dumps({"error": "Error: Server configuration missing for AI Vision."}),
                mimetype="application/json",
                status_code=500
            )

        image_file = req.files.get('image') # DIPINDAHKAN DAN DIPERBAIKI
        if not image_file:
            logging.warning("Tidak ada file gambar yang diterima.")
            return func.HttpResponse(
                json.dumps({"error": "Harap unggah file gambar dengan field name 'image'."}),
                mimetype="application/json",
                status_code=400
            )

        image_bytes = image_file.read()

        cv_client = ImageAnalysisClient(
            endpoint=ai_services_endpoint,
            credential=AzureKeyCredential(ai_services_key)
        )

        logging.info("Memanggil Azure AI Vision untuk deteksi objek...")
        result = cv_client.analyze(
            image_data=image_bytes,
            visual_features=[VisualFeatures.OBJECTS]
        )

        detected_objects_output = []

        if result.objects and result.objects.list: # Gunakan result.objects.list
            logging.info(f"Ditemukan {len(result.objects.list)} objek.")
            for detected_object in result.objects.list: # Iterasi langsung objek DetectedObject
                obj_name = "Unknown"
                # Confidence objek keseluruhan, bukan per tag spesifik
                obj_confidence = detected_object.confidence

                # Ambil nama dari tag pertama dengan confidence tertinggi, atau gabungkan
                if detected_object.tags:
                    # Anda bisa memilih tag pertama atau yang paling relevan
                    obj_name = detected_object.tags[0].name
                    # Jika ingin confidence dari tag pertama:
                    # obj_confidence_tag = detected_object.tags[0].confidence

                rect_x, rect_y, rect_w, rect_h = 0, 0, 0, 0
                if detected_object.bounding_box:
                    bbox = detected_object.bounding_box
                    rect_x = bbox.x
                    rect_y = bbox.y
                    rect_w = bbox.width # Perhatikan ini 'width' bukan 'w' dari SDK
                    rect_h = bbox.height # Perhatikan ini 'height' bukan 'h'
                else:
                    logging.warning(f"Objek {obj_name} tidak memiliki atribut 'bounding_box'.")

                detected_objects_output.append({
                    "objectName": obj_name,
                    "confidence": obj_confidence, # Ini confidence objek keseluruhan
                    "boundingBox": {
                        "x": rect_x,
                        "y": rect_y,
                        "width": rect_w,
                        "height": rect_h
                    }
                })
        else:
            logging.info("Tidak ada objek visual yang terdeteksi atau result.objects.list kosong.")

        # Gunakan json.dumps untuk serialisasi yang benar
        return func.HttpResponse(
            body=json.dumps(detected_objects_output),
            mimetype="application/json",
            status_code=200
        )

    except ValueError as ve: # Misal jika file bukan gambar
        logging.error(f"ValueError: {str(ve)}")
        return func.HttpResponse(json.dumps({"error": f"Invalid input: {str(ve)}"}), mimetype="application/json", status_code=400)
    except Exception as e:
        logging.error(f"Terjadi kesalahan internal: {str(e)}")
        import traceback
        logging.error(traceback.format_exc()) # Log traceback untuk debug lebih lanjut
        return func.HttpResponse(json.dumps({"error": "Terjadi kesalahan pada server saat memproses gambar."}), mimetype="application/json", status_code=500)