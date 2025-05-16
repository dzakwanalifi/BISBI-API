import logging
import os
import azure.functions as func
import json # Tambahkan import json

from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request for DetectObjectsVisual.')

    try:
        ai_services_endpoint = os.environ.get("AZURE_AI_SERVICES_ENDPOINT")
        ai_services_key = os.environ.get("AZURE_AI_SERVICES_KEY")

        if not ai_services_endpoint or not ai_services_key:
            logging.error("Azure AI Services endpoint atau key tidak dikonfigurasi.")
            return func.HttpResponse("Error: Server configuration missing.", status_code=500)

        image_file = req.files.get('image')
        if not image_file:
            logging.warning("Tidak ada file gambar yang diterima.")
            return func.HttpResponse("Harap unggah file gambar dengan field name 'image'.", status_code=400)
        
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

        if result.objects and hasattr(result.objects, 'values') and callable(getattr(result.objects, 'values')):
            list_of_all_detected_objects_groups = result.objects.values() 
            
            if list_of_all_detected_objects_groups:
                logging.info(f"result.objects.values() mengembalikan list dengan {len(list_of_all_detected_objects_groups)} grup hasil.")

                # Kita asumsikan grup hasil yang relevan ada di elemen pertama (jika ada)
                # atau kita bisa iterasi semua grup jika strukturnya memungkinkan
                for object_group_list in list_of_all_detected_objects_groups:
                    # 'object_group_list' sekarang seharusnya adalah list objek individual
                    # seperti yang terlihat di log: [{'boundingBox': ..., 'tags': ...}, {'boundingBox': ..., 'tags': ...}]
                    
                    # Pastikan object_group_list adalah list
                    if not isinstance(object_group_list, list):
                        logging.warning(f"Elemen dalam values() bukan list, melainkan {type(object_group_list)}. Skipping.")
                        continue

                    logging.info(f"Memproses grup dengan {len(object_group_list)} objek visual individual.")
                    for individual_detected_object in object_group_list:
                        # 'individual_detected_object' sekarang adalah objek SDK yang sebenarnya
                        # (bukan dictionary mentah dari log, tapi objek dengan atribut)
                        
                        obj_name = "Unknown"
                        obj_confidence = 0.0
                        rect_x, rect_y, rect_w, rect_h = 0, 0, 0, 0

                        # Mengakses atribut langsung dari objek SDK
                        if hasattr(individual_detected_object, 'tags') and individual_detected_object.tags:
                            if len(individual_detected_object.tags) > 0:
                                tag_obj = individual_detected_object.tags[0]
                                if hasattr(tag_obj, 'name'):
                                   obj_name = tag_obj.name
                                if hasattr(tag_obj, 'confidence'):
                                   obj_confidence = tag_obj.confidence
                        
                        if hasattr(individual_detected_object, 'bounding_box'):
                            bbox = individual_detected_object.bounding_box
                            if bbox: # Pastikan bounding_box tidak None
                                rect_x = bbox.x
                                rect_y = bbox.y
                                rect_w = bbox.width
                                rect_h = bbox.height
                        else:
                            logging.warning(f"Objek {obj_name} tidak memiliki atribut 'bounding_box'.")
                        
                        detected_objects_output.append({
                            "objectName": obj_name,
                            "confidence": obj_confidence,
                            "boundingBox": {
                                "x": rect_x,
                                "y": rect_y,
                                "width": rect_w,
                                "height": rect_h
                            }
                        })
            else:
                logging.info("List objek visual dari 'result.objects.values()' kosong.")
        else:
            logging.warning("Struktur 'result.objects' tidak memiliki method 'values' atau 'result.objects' adalah None atau values() tidak mengembalikan list.")
                
        # Gunakan json.dumps untuk serialisasi yang benar
        return func.HttpResponse(
            body=json.dumps(detected_objects_output), 
            mimetype="application/json",
            status_code=200
        )

    except ValueError as ve:
        logging.error(f"ValueError: {str(ve)}")
        return func.HttpResponse(f"Invalid input: {str(ve)}", status_code=400)
    except Exception as e:
        logging.error(f"Terjadi kesalahan internal: {str(e)}")
        import traceback
        logging.error(traceback.format_exc()) # Log traceback untuk debug lebih lanjut
        return func.HttpResponse("Terjadi kesalahan pada server saat memproses gambar.", status_code=500)