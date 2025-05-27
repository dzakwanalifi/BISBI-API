import azure.functions as func
import logging
from . import main as detect_objects_main

# Create Blueprint
bp = func.Blueprint()

@bp.route(route="DetectObjectsVisual", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def DetectObjectsVisual_handler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Blueprint: Routing to DetectObjectsVisual")
    return detect_objects_main(req)