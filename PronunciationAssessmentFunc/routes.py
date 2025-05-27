import azure.functions as func
import logging
from . import main as pronunciation_assessment_main

try:
    from ..auth_utils import require_auth
except ImportError:
    from auth_utils import require_auth

# Create Blueprint
bp = func.Blueprint()

@bp.route(route="PronunciationAssessmentFunc", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
@require_auth
def PronunciationAssessmentFunc_handler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f"Blueprint: Routing to PronunciationAssessmentFunc")
    # Call the main logic function, user_id akan diambil dari req di dalam main
    return pronunciation_assessment_main(req)