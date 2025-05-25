import azure.functions as func
import datetime
import json
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Import and register all blueprints
logging.info("function_app.py: Registering blueprints")

# Import ApiHealthCheck blueprint
from ApiHealthCheck.routes import bp as health_check_bp
app.register_functions(health_check_bp)
logging.info("function_app.py: Registered ApiHealthCheck blueprint")

# Import DetectObjectsVisual blueprint
from DetectObjectsVisual.routes import bp as detect_objects_bp
app.register_functions(detect_objects_bp)
logging.info("function_app.py: Registered DetectObjectsVisual blueprint")

# Import GenerateLesson blueprint
from GenerateLesson.routes import bp as generate_lesson_bp
app.register_functions(generate_lesson_bp)
logging.info("function_app.py: Registered GenerateLesson blueprint")

# Import GetObjectDetailsVisual blueprint
from GetObjectDetailsVisual.routes import bp as get_object_details_bp
app.register_functions(get_object_details_bp)
logging.info("function_app.py: Registered GetObjectDetailsVisual blueprint")

# Import GetTTSAudio blueprint
from GetTTSAudio.routes import bp as get_tts_audio_bp
app.register_functions(get_tts_audio_bp)
logging.info("function_app.py: Registered GetTTSAudio blueprint")

# Import PronunciationAssessmentFunc blueprint
from PronunciationAssessmentFunc.routes import bp as pronunciation_assessment_bp
app.register_functions(pronunciation_assessment_bp)
logging.info("function_app.py: Registered PronunciationAssessmentFunc blueprint")

# Add a final log message confirming all blueprints have been registered
logging.info("function_app.py: All blueprints successfully registered!")