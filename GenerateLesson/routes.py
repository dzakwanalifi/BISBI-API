import azure.functions as func
import logging
from . import main as generate_lesson_main

# TAMBAHKAN IMPORT INI (sesuaikan path jika perlu, seperti contoh sebelumnya)
try:
    from ..auth_utils import require_auth
except ImportError:
    from auth_utils import require_auth

# Create Blueprint
bp = func.Blueprint()

# TERAPKAN DECORATOR @require_auth DI SINI
@bp.route(route="GenerateLesson", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"]) # Ubah auth_level ke ANONYMOUS
@require_auth # Decorator diterapkan di sini
def GenerateLesson_handler(req: func.HttpRequest) -> func.HttpResponse: # Hapus user_id dari signature
    # user_id akan di-inject ke req oleh decorator @require_auth
    # logging.info(f"Blueprint: Routing to GenerateLesson for user {getattr(req, 'user_id_injected', 'UNKNOWN')}")
    # Tidak perlu inject user_id lagi di sini, sudah dilakukan di decorator
    # setattr(req, 'user_id_injected', user_id)
    
    # Call the main logic function, user_id akan diambil dari req di dalam main
    return generate_lesson_main(req)