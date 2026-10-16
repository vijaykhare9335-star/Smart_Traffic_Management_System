from flask import Flask, jsonify, Response
from flask_cors import CORS
import cv2
import os
import numpy as np
import time
import threading
from collections import defaultdict, deque
from traffic_predictor import TrafficDensityPredictor

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -----------------------------
# YOLO FILES
# -----------------------------   
WEIGHTS = os.path.join(BASE_DIR, "yolov3-tiny.weights")
CFG = os.path.join(BASE_DIR, "yolov3.tiny.cfg")
NAMES = os.path.join(BASE_DIR, "coco.names")

# -----------------------------
# LOAD CLASSES
# -----------------------------
with open(NAMES, "r") as f:
    classes = f.read().splitlines()

vehicle_classes = ["car", "bus", "truck", "motorbike"]

# Centroid tracker for counting unique vehicles per lane
class CentroidTracker:
    def __init__(self, max_disappeared=15, max_distance=40):
        self.next_object_id = 0
        self.objects = {}
        self.disappeared = defaultdict(int)
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
    
    def register(self, centroid):
        self.objects[self.next_object_id] = centroid
        self.next_object_id += 1
    
    def deregister(self, object_id):
        del self.objects[object_id]
        del self.disappeared[object_id]
    
    def update(self, rects):
        if len(rects) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects
        
        input_centroids = np.zeros((len(rects), 2), dtype="int")
        for i, rect in enumerate(rects):
            cx = rect[0] + rect[2] // 2
            cy = rect[1] + rect[3] // 2
            input_centroids[i] = [cx, cy]
        
        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.register(input_centroids[i])
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())
            
            distances = np.zeros((len(object_centroids), len(input_centroids)))
            for i in range(len(object_centroids)):
                for j in range(len(input_centroids)):
                    dist = np.linalg.norm(np.array(object_centroids[i]) - input_centroids[j])
                    distances[i][j] = dist
            
            rows = distances.min(axis=1).argsort()
            cols = distances.argmin(axis=1)[rows]
            
            used_rows = set()
            used_cols = set()
            
            for row, col in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if distances[row, col] > self.max_distance:
                    continue
                
                object_id = object_ids[row]
                self.objects[object_id] = input_centroids[col]
                self.disappeared[object_id] = 0
                
                used_rows.add(row)
                used_cols.add(col)
            
            unused_rows = set(range(0, distances.shape[0])).difference(used_rows)
            unused_cols = set(range(0, distances.shape[1])).difference(used_cols)
            
            if distances.shape[0] >= distances.shape[1]:
                for row in unused_rows:
                    object_id = object_ids[row]
                    self.disappeared[object_id] += 1
                    if self.disappeared[object_id] > self.max_disappeared:
                        self.deregister(object_id)
            else:
                for col in unused_cols:
                    self.register(input_centroids[col])
        
        return self.objects

# Initialize centroid trackers for each lane
centroid_trackers = {
    "North": CentroidTracker(),
    "South": CentroidTracker(),
    "East": CentroidTracker(),
    "West": CentroidTracker(),
}

# Track frames processed for each lane to prevent stale counts
frame_counters = {
    "North": 0,
    "South": 0,
    "East": 0,
    "West": 0,
}

# Reset tracker every N frames to prevent memory issues
RESET_TRACKER_EVERY = 150  # Reset more frequently

# Process every frame for more accurate vehicle counts
FRAME_SKIP = 1

# -----------------------------
# Load YOLO per lane with validation
# --------------------------------- 
def load_yolo():
    if not os.path.exists(WEIGHTS):
        raise FileNotFoundError(f"YOLO weights not found: {WEIGHTS}")
    if not os.path.exists(CFG):
        raise FileNotFoundError(f"YOLO config not found: {CFG}")
    
    net = cv2.dnn.readNet(WEIGHTS, CFG)
    if net.empty():
        raise RuntimeError("Failed to load YOLO model")
    
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return net

nets = {
    "North": load_yolo(),
    "South": load_yolo(),
    "East": load_yolo(),
    "West": load_yolo(),
}

# Get output layers (same for all)
layer_names = nets["North"].getLayerNames()
output_layers = [layer_names[i - 1] for i in nets["North"].getUnconnectedOutLayers().flatten()]

# -----------------------------
# VIDEO SOURCES
# -----------------------------
def initialize_video_sources():
    """Initialize video sources with error handling"""
    video_files = {
        "North": "north.mp4",
        "South": "south.mp4",
        "East": "east.mp4",
        "West": "west.mp4",
    }

    video_streams = {}
    for lane, filename in video_files.items():
        try:
            cap = cv2.VideoCapture(filename)
            if not cap.isOpened():
                print(f"ERROR: Cannot open {filename}")
                # Try alternative path
                alt_path = os.path.join(BASE_DIR, filename)
                cap = cv2.VideoCapture(alt_path)
                if not cap.isOpened():
                    print(f"ERROR: Cannot open {alt_path} either")
                    continue

            # Test reading first frame
            ret, frame = cap.read()
            if not ret or frame is None:
                print(f"ERROR: Cannot read first frame from {filename}")
                cap.release()
                continue

            print(f"SUCCESS: {filename} loaded - Frame shape: {frame.shape}")
            video_streams[lane] = cap

        except Exception as e:
            print(f"ERROR initializing {filename}: {e}")
            continue

    return video_streams

video_streams = initialize_video_sources()

# Thread locks for video streams
video_locks = {
    "North": threading.Lock(),
    "South": threading.Lock(),
    "East": threading.Lock(),
    "West": threading.Lock(),
}

# Shared frame cache to sync API and video streams
frame_cache = {
    "North": None,
    "South": None,
    "East": None,
    "West": None,
}
frame_cache_lock = threading.Lock()

# Store current vehicle counts for each lane (updated by video streams)
current_counts = {
    "North": 0,
    "South": 0,
    "East": 0,
    "West": 0,
}
count_lock = threading.Lock()

# Maintain a short history of counts for each lane. This helps the ML predictor
# learn patterns such as rising or falling traffic trends.
lane_history = {
    "North": deque(maxlen=4),
    "South": deque(maxlen=4),
    "East": deque(maxlen=4),
    "West": deque(maxlen=4),
}

density_predictor = TrafficDensityPredictor()

# -----------------------------
# DETECTION FUNCTION
# -----------------------------
def process_frame(frame, net, lane):
    global frame_counters
    try:
        # Validate frame
        if frame is None or frame.size == 0:
            return None, 0
        
        height, width = frame.shape[:2]
        if height <= 0 or width <= 0:
            return None, 0

        # Ensure width and height are reasonable
        if width < 100 or height < 100:
            return None, 0

        # Reset tracker periodically
        frame_counters[lane] += 1
        if frame_counters[lane] % RESET_TRACKER_EVERY == 0:
            centroid_trackers[lane] = CentroidTracker()

        # Frame skipping for performance - process every 2nd frame
        if frame_counters[lane] % FRAME_SKIP != 0:
            # Return frame with last known count for skipped frames
            last_count = getattr(process_frame, f'last_count_{lane}', 0)
            cv2.putText(frame, f"Vehicles: {last_count}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            return frame, last_count

        # Define ROI (region of interest) - keep a wider detection area for better coverage
        roi_y_start = max(0, int(height * 0.05))
        roi_y_end = min(height, int(height * 0.95))

        # Create blob safely with a slightly larger resolution for accuracy
        try:
            blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True)
            if blob is None or blob.size == 0:
                return None, 0
        except Exception as e:
            print(f"Blob creation error for {lane}:", e)
            return None, 0

        net.setInput(blob)
        outputs = net.forward(output_layers)

        boxes = []
        confidences = []
        class_ids = []

        for output in outputs:
            for detection in output:
                try:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = float(scores[class_id])

                    # Lower threshold to detect more vehicles reliably in traffic footage
                    if confidence < 0.3 or classes[class_id] not in vehicle_classes:
                        continue

                    # Safe coordinate calculation
                    center_x = float(detection[0]) * width
                    center_y = float(detection[1]) * height
                    w = float(detection[2]) * width
                    h = float(detection[3]) * height

                    # Validate coordinates
                    if np.isnan(center_x) or np.isnan(center_y) or np.isnan(w) or np.isnan(h):
                        continue
                    if w < 1 or h < 1:
                        continue

                    # Check ROI
                    if center_y < roi_y_start or center_y > roi_y_end:
                        continue

                    # Lower minimum size so smaller cars are still counted
                    if w < 10 or h < 10:
                        continue

                    x = int(max(0, center_x - w / 2))
                    y = int(max(0, center_y - h / 2))
                    w_int = int(w)
                    h_int = int(h)

                    # Make sure bbox is within frame
                    if x + w_int > width:
                        w_int = width - x
                    if y + h_int > height:
                        h_int = height - y

                    if w_int > 0 and h_int > 0:
                        boxes.append([x, y, w_int, h_int])
                        confidences.append(confidence)
                        class_ids.append(class_id)
                except Exception as e:
                    continue

        # Use NMS (Non-Maximum Suppression)
        count = 0
        if len(boxes) > 0:
            try:
                indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.3, 0.45)

                if len(indexes) > 0:
                    indexes_list = indexes.flatten()
                    count = len(indexes_list)  # Count only NMS-filtered detections in current frame

                    for i in indexes_list:
                        x, y, w, h = boxes[i]
                        label = classes[class_ids[i]]
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(frame, label, (x, y - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                    (0, 255, 0), 2)
                else:
                    pass  # No detections after NMS
            except Exception as e:
                print(f"NMS error for {lane}:", e)
                count = 0
        else:
            count = 0

        # Draw ROI
        if roi_y_start >= 0 and roi_y_end > roi_y_start and roi_y_end <= height and width > 0:
            cv2.rectangle(frame, (0, roi_y_start), (width, roi_y_end), (255, 0, 0), 2)
        
        cv2.putText(frame, f"Vehicles: {count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Store last count for frame skipping
        setattr(process_frame, f'last_count_{lane}', count)

        return frame, count

    except Exception as e:
        print(f"YOLO ERROR for {lane}:", e)
        return None, 0


# Initialize last counts for frame skipping
for lane in ["North", "South", "East", "West"]:
    setattr(process_frame, f'last_count_{lane}', 0)


# -----------------------------
# TRAFFIC API
# -----------------------------
@app.route("/traffic")
def traffic_data():
    result = {}
    total_count = 0

    with count_lock:
        for lane in current_counts:
            count = current_counts[lane]
            total_count += count

            lane_history[lane].append(count)
            trend = 0
            if len(lane_history[lane]) >= 2:
                trend = count - lane_history[lane][-2]
            average = float(sum(lane_history[lane]) / len(lane_history[lane]))

            density, confidence = density_predictor.predict_density(count, trend, average)
            green_time = density_predictor.predict_green_time(count, trend, average)
            high_traffic = density == "HIGH"
            signal_strategy = "EXTEND" if high_traffic else "NORMAL"

            result[lane] = {
                "vehicles": count,
                "density": density,
                "high_traffic": high_traffic,
                "traffic_state": "CONGESTED" if high_traffic else "NORMAL",
                "signal_strategy": signal_strategy,
                "green_time": green_time,
                "confidence": round(confidence, 2),
                "model": "ml-density-v1"
            }

    print(f"AI Traffic API Response - Total vehicles: {total_count} | Breakdown: {result}")
    return jsonify(result)


# -----------------------------
# VIDEO STREAM
# -----------------------------
def generate_frames(cap, net, lane):
    frame_count = 0
    while True:
        try:
            with video_locks[lane]:
                success, frame = cap.read()

                if not success:
                    print(f"[{lane}] End of video reached, restarting...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    success, frame = cap.read()
                    if not success:
                        print(f"[{lane}] ERROR: Cannot restart video")
                        time.sleep(1)
                        continue

            if frame is None or frame.size == 0:
                print(f"[{lane}] ERROR: Invalid frame")
                time.sleep(1)
                continue

            # Update frame cache for API synchronization
            with frame_cache_lock:
                frame_cache[lane] = frame.copy() if frame is not None else None

            processed_frame, count = process_frame(frame, net, lane)

            # Store current count for API to use
            with count_lock:
                current_counts[lane] = count

            if processed_frame is None:
                print(f"[{lane}] ERROR: Frame processing failed")
                continue

            ret, buffer = cv2.imencode('.jpg', processed_frame)
            if not ret:
                print(f"[{lane}] ERROR: Frame encoding failed")
                continue

            frame_count += 1
            frame_bytes = buffer.tobytes()
            time.sleep(0.1)  # Reduced sleep for smoother streaming

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        except Exception as e:
            print(f"[{lane}] STREAM ERROR: {e}")
            time.sleep(1)
            continue


@app.route('/video/<lane>')
def video_feed(lane):
    lane = lane.capitalize()

    cap = video_streams.get(lane)
    net = nets.get(lane)

    if cap is None or net is None:
        return f"Video stream for {lane} is not available", 503

    try:
        return Response(generate_frames(cap, net, lane),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print(f"Video feed error for {lane}: {e}")
        return f"Video feed error: {e}", 500


# -----------------------------
@app.route("/")
def home():
    return "AI Traffic Backend Running 🚦"


# -----------------------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)  # 🔥 ENABLED AUTO-RELOAD