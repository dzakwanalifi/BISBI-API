import azure.functions as func
import logging
from . import main as pronunciation_assessment_main

# Create Blueprint
bp = func.Blueprint()

@bp.route(route="PronunciationAssessmentFunc", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def PronunciationAssessmentFunc_handler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Blueprint: Routing to PronunciationAssessmentFunc")
    return pronunciation_assessment_main(req)