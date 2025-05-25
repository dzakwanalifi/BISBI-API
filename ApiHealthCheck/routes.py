import azure.functions as func
import logging
from . import main as health_check_main

# Create Blueprint
bp = func.Blueprint()

@bp.route(route="ApiHealthCheck", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def ApiHealthCheck_handler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Blueprint: Routing to ApiHealthCheck")
    return health_check_main(req)