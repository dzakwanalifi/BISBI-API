import azure.functions as func
import logging
from . import main as get_tts_audio_main

# Create Blueprint
bp = func.Blueprint()

@bp.route(route="GetTTSAudio", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def GetTTSAudio_handler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Blueprint: Routing to GetTTSAudio")
    return get_tts_audio_main(req)