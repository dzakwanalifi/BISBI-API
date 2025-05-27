\
import logging

def calculate_iou(box1, box2):
    """
    Calculates Intersection over Union (IoU) between two bounding boxes.

    Args:
        box1 (dict): The first bounding box, with keys "x", "y", "width", "height".
        box2 (dict): The second bounding box, with keys "x", "y", "width", "height".

    Returns:
        float: The IoU score, between 0.0 and 1.0.
    """
    # box format: {"x": ..., "y": ..., "width": ..., "height": ...}
    # Ubah ke x1, y1, x2, y2
    x1_1, y1_1 = box1['x'], box1['y']
    x2_1, y2_1 = box1['x'] + box1['width'], box1['y'] + box1['height']
    
    x1_2, y1_2 = box2['x'], box2['y']
    x2_2, y2_2 = box2['x'] + box2['width'], box2['y'] + box2['height']
    
    # Hitung area interseksi
    xi_1 = max(x1_1, x1_2)
    yi_1 = max(y1_1, y1_2)
    xi_2 = min(x2_1, x2_2)
    yi_2 = min(y2_1, y2_2)
    
    inter_width = max(0, xi_2 - xi_1)
    inter_height = max(0, yi_2 - yi_1)
    inter_area = inter_width * inter_height
    
    # Hitung area masing-masing box
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
    detections = [d for d in detections if d['confidence'] >= score_threshold]

    # Urutkan berdasarkan confidence score (tertinggi dulu)
    detections.sort(key=lambda x: x['confidence'], reverse=True)
    
    selected_detections = []
    
    while detections:
        # Ambil deteksi dengan confidence tertinggi
        current_detection = detections.pop(0)
        selected_detections.append(current_detection)
        
        # Buang deteksi lain yang IoU-nya tinggi DENGAN KELAS YANG SAMA
        remaining_detections = []
        for det in detections:
            if det['objectName'] == current_detection['objectName']: # Hanya NMS untuk kelas yang sama
                iou = calculate_iou(current_detection['boundingBox'], det['boundingBox'])
                if iou < iou_threshold:
                    remaining_detections.append(det)
            else: # Jika kelas berbeda, jangan lakukan NMS, biarkan saja
                remaining_detections.append(det)
        detections = remaining_detections
        
    return selected_detections
