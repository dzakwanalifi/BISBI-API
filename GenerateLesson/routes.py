import azure.functions as func
import logging
from . import main as generate_lesson_main

# Create Blueprint
bp = func.Blueprint()

@bp.route(route="GenerateLesson", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def GenerateLesson_handler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Blueprint: Routing to GenerateLesson")
    return generate_lesson_main(req)