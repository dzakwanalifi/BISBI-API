import azure.functions as func
import logging
from . import main as get_object_details_main

# Create Blueprint
bp = func.Blueprint()

@bp.route(route="GetObjectDetailsVisual", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def GetObjectDetailsVisual_handler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Blueprint: Routing to GetObjectDetailsVisual")
    return get_object_details_main(req)