import azure.functions as func
import logging
from . import main as detect_objects_main

# TAMBAHKAN IMPORT INI (sesuaikan path jika perlu)
try:
    from ..auth_utils import require_auth
except ImportError:
    from auth_utils import require_auth

# Create Blueprint
bp = func.Blueprint()

# TERAPKAN DECORATOR @require_auth DI SINI
@bp.route(route="DetectObjectsVisual", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"]) # Ubah auth_level
@require_auth # Decorator diterapkan di sini
def DetectObjectsVisual_handler(req: func.HttpRequest, user_id: str) -> func.HttpResponse: # Tambahkan user_id
    logging.info(f"Blueprint: Routing to DetectObjectsVisual for user {user_id}")
    # Teruskan user_id ke fungsi main
    return detect_objects_main(req, user_id=user_id)