import logging # Ensure logging is imported

def calculate_iou(box1, box2):
    """
    Calculates Intersection over Union (IoU) between two bounding boxes.

    Args:
        box1 (dict): The first bounding box, with keys "x", "y", "width", "height".
        box2 (dict): The second bounding box, with keys "x", "y", "width", "height".

    Returns:
        float: The IoU score, between 0.0 and 1.0.
    """
    x1_1, y1_1 = box1['x'], box1['y']
    x2_1, y2_1 = box1['x'] + box1['width'], box1['y'] + box1['height']
    
    x1_2, y1_2 = box2['x'], box2['y']
    x2_2, y2_2 = box2['x'] + box2['width'], box2['y'] + box2['height']
    
    xi_1 = max(x1_1, x1_2)
    yi_1 = max(y1_1, y1_2)
    xi_2 = min(x2_1, x2_2)
    yi_2 = min(y2_1, y2_2)
    
    inter_width = max(0, xi_2 - xi_1)
    inter_height = max(0, yi_2 - yi_1)
    inter_area = inter_width * inter_height
    
    area1 = box1['width'] * box1['height']
    area2 = box2['width'] * box2['height']
    
    union_area = area1 + area2 - inter_area
    
    if union_area == 0:
        return 0.0
        
    iou = inter_area / union_area
    return iou

def apply_nms(detections, iou_threshold=0.5, score_threshold=0.5):
    """
    Applies Non-Maximum Suppression (NMS) to a list of detections.

    Args:
        detections (list): A list of detection dictionaries. Each dictionary
                           should have "confidence", "objectName", and "boundingBox".
        iou_threshold (float): The IoU threshold for suppressing overlapping boxes.
        score_threshold (float): The minimum confidence score for a detection to be considered.

    Returns:
        list: A list of filtered detections after applying NMS.
    """
    # Filter berdasarkan score_threshold dulu
    detections = [d for d in detections if d.get('confidence', 0) >= score_threshold] # Use .get for safety

    # Urutkan berdasarkan confidence score (tertinggi dulu)
    detections.sort(key=lambda x: x.get('confidence', 0), reverse=True) # Use .get for safety
    
    selected_detections = []
    
    while detections:
        current_detection = detections.pop(0)
        selected_detections.append(current_detection)
        
        remaining_detections = []
        for det in detections:
            # Ensure both detections have necessary keys before calling IoU
            if det.get('objectName') == current_detection.get('objectName') and \
               'boundingBox' in current_detection and 'boundingBox' in det:
                iou = calculate_iou(current_detection['boundingBox'], det['boundingBox'])
                if iou < iou_threshold:
                    remaining_detections.append(det)
            else: 
                remaining_detections.append(det)
        detections = remaining_detections
        
    return selected_detections

def transform_hf_predictions_to_custom_format(hf_predictions):
    """
    Transforms predictions from HuggingFace object detection format
    (e.g., from DETR models like facebook/detr-resnet-50) to the custom format.

    HF format item (dict):
        {'score': float, 'label': str, 'box': {'xmin': int, 'ymin': int, 'xmax': int, 'ymax': int}}
    
    Custom format item (dict):
        {'confidence': float, 'objectName': str, 'boundingBox': {'x': int, 'y': int, 'width': int, 'height': int}}
    """
    custom_results = []
    if not isinstance(hf_predictions, list):
        logging.error(f"transform_hf_predictions_to_custom_format: Expected a list, got {type(hf_predictions)}")
        return custom_results

    for pred in hf_predictions:
        if not isinstance(pred, dict):
            logging.warning(f"transform_hf_predictions_to_custom_format: Skipping non-dict item: {pred}")
            continue

        try:
            score = pred.get('score')
            label = pred.get('label')
            box = pred.get('box')

            if score is None or label is None or box is None or not isinstance(box, dict):
                logging.warning(f"transform_hf_predictions_to_custom_format: Skipping prediction with missing/invalid fields: {pred}")
                continue
            
            xmin = box.get('xmin')
            ymin = box.get('ymin')
            xmax = box.get('xmax')
            ymax = box.get('ymax')

            if any(coord is None for coord in [xmin, ymin, xmax, ymax]):
                logging.warning(f"transform_hf_predictions_to_custom_format: Skipping prediction with missing box coordinates: {pred}")
                continue

            custom_pred = {
                'confidence': float(score),
                'objectName': str(label),
                'boundingBox': {
                    'x': int(xmin),
                    'y': int(ymin),
                    'width': int(xmax - xmin),
                    'height': int(ymax - ymin)
                }
            }
            # Ensure width and height are non-negative
            if custom_pred['boundingBox']['width'] < 0 or custom_pred['boundingBox']['height'] < 0:
                logging.warning(f"transform_hf_predictions_to_custom_format: Skipping prediction with negative width/height: {custom_pred}")
                continue
                
            custom_results.append(custom_pred)
        except (TypeError, ValueError) as e: # Catch errors during conversion (e.g. float(), int())
            logging.error(f"transform_hf_predictions_to_custom_format: Error converting prediction data: {pred}. Error: {e}", exc_info=True)
        except Exception as e:
            logging.error(f"transform_hf_predictions_to_custom_format: Unexpected error transforming prediction: {pred}. Error: {e}", exc_info=True)
            
    return custom_results