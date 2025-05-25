import logging
import json
import datetime
import azure.functions as func

# Versi API bisa di-hardcode di sini atau diambil dari env variable jika perlu
API_VERSION = "0.1.0-mvp" 

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request for ApiHealthCheck.')

    try:
        # Dapatkan timestamp saat ini dalam format ISO 8601 UTC
        current_timestamp = datetime.datetime.utcnow().isoformat() + "Z"

        response_data = {
            "status": "healthy",
            "message": "Welcome to Lensa Bahasa API! All systems operational.",
            "version": API_VERSION,
            "timestamp": current_timestamp,
            "documentation": "https://github.com/dzakwanalifi/BISBI-API/blob/master/README.md" # Ganti dengan URL README Anda
        }

        return func.HttpResponse(
            body=json.dumps(response_data),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error in ApiHealthCheck: {str(e)}")
        # Seharusnya tidak banyak error di sini, tapi untuk jaga-jaga
        return func.HttpResponse(
             json.dumps({"status": "error", "message": "An unexpected error occurred."}),
             mimetype="application/json",
             status_code=500
        )