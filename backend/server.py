from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import uuid
from datetime import datetime, timezone
import mediapipe as mp
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
import cv2
import numpy as np
import json
import tempfile
from urllib.request import urlopen

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')
FRONTEND_BUILD_DIR = ROOT_DIR.parent / "frontend" / "build"

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

MIN_VISIBILITY = float(os.environ.get("POSE_MIN_VISIBILITY", "0.35"))
RELAXED_MIN_VISIBILITY = float(os.environ.get("POSE_RELAXED_MIN_VISIBILITY", "0.15"))
POSE_DETECTION_CONFIDENCE = float(os.environ.get("POSE_MIN_DETECTION_CONFIDENCE", "0.35"))
POSE_PRESENCE_CONFIDENCE = float(os.environ.get("POSE_MIN_PRESENCE_CONFIDENCE", "0.35"))
MAX_POSES = int(os.environ.get("POSE_MAX_PEOPLE", "6"))
POSE_MODEL_VARIANT = os.environ.get("POSE_MODEL_VARIANT", "heavy")
POSE_MODEL_DIR = ROOT_DIR / "models"
POSE_MODEL_PATH = POSE_MODEL_DIR / f"pose_landmarker_{POSE_MODEL_VARIANT}.task"
POSE_MODEL_URL = os.environ.get(
    "POSE_MODEL_URL",
    f"https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_{POSE_MODEL_VARIANT}/float16/1/pose_landmarker_{POSE_MODEL_VARIANT}.task",
)
pose_landmarker = None

TEMP_DIR = Path(tempfile.gettempdir()) / "pose_detection"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Define pose connections for stick figure
POSE_CONNECTIONS = [
    # Torso
    (11, 12),  # Left shoulder to right shoulder
    (11, 23),  # Left shoulder to left hip
    (12, 24),  # Right shoulder to right hip
    (23, 24),  # Left hip to right hip
    
    # Left arm
    (11, 13),  # Left shoulder to left elbow
    (13, 15),  # Left elbow to left wrist
    
    # Right arm
    (12, 14),  # Right shoulder to right elbow
    (14, 16),  # Right elbow to right wrist
    
    # Left leg
    (23, 25),  # Left hip to left knee
    (25, 27),  # Left knee to left ankle
    
    # Right leg
    (24, 26),  # Right hip to right knee
    (26, 28),  # Right knee to right ankle
    
    # Head
    (0, 1),    # Nose to left eye inner
    (1, 2),    # Left eye inner to left eye
    (2, 3),    # Left eye to left eye outer
    (0, 4),    # Nose to right eye inner
    (4, 5),    # Right eye inner to right eye
    (5, 6),    # Right eye to right eye outer
    (0, 11),   # Nose to left shoulder
    (0, 12),   # Nose to right shoulder
]

# Keypoint names for reference
KEYPOINT_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear", "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_pinky", "right_pinky",
    "left_index", "right_index", "left_thumb", "right_thumb",
    "left_hip", "right_hip", "left_knee", "right_knee",
    "left_ankle", "right_ankle", "left_heel", "right_heel",
    "left_foot_index", "right_foot_index"
]


POSE_COLORS = [
    ((0, 255, 0), (0, 0, 255)),
    ((255, 165, 0), (255, 0, 0)),
    ((255, 0, 255), (0, 255, 255)),
    ((255, 255, 0), (255, 0, 128)),
]


def ensure_pose_landmarker_model() -> Path:
    POSE_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if POSE_MODEL_PATH.exists():
        return POSE_MODEL_PATH

    logger.info("Downloading pose landmarker model to %s", POSE_MODEL_PATH)
    with urlopen(POSE_MODEL_URL, timeout=120) as response, open(POSE_MODEL_PATH, "wb") as model_file:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            model_file.write(chunk)

    return POSE_MODEL_PATH


def get_pose_landmarker() -> PoseLandmarker:
    global pose_landmarker
    if pose_landmarker is None:
        model_path = ensure_pose_landmarker_model()
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            num_poses=MAX_POSES,
            min_pose_detection_confidence=POSE_DETECTION_CONFIDENCE,
            min_pose_presence_confidence=POSE_PRESENCE_CONFIDENCE,
        )
        pose_landmarker = PoseLandmarker.create_from_options(options)
    return pose_landmarker


def landmark_in_frame(landmark) -> bool:
    return 0.0 <= landmark.x <= 1.0 and 0.0 <= landmark.y <= 1.0


def build_keypoint(landmark, width: int, height: int, idx: int) -> dict:
    return {
        "id": idx,
        "name": KEYPOINT_NAMES[idx] if idx < len(KEYPOINT_NAMES) else f"point_{idx}",
        "x": landmark.x,
        "y": landmark.y,
        "z": landmark.z,
        "visibility": landmark.visibility,
        "pixel_x": int(landmark.x * width),
        "pixel_y": int(landmark.y * height),
    }


def filter_person_keypoints(person_all_keypoints: list[dict]) -> list[dict]:
    visible_keypoints = [
        keypoint for keypoint in person_all_keypoints
        if keypoint["visibility"] >= MIN_VISIBILITY and 0.0 <= keypoint["x"] <= 1.0 and 0.0 <= keypoint["y"] <= 1.0
    ]
    if visible_keypoints:
        return visible_keypoints

    relaxed_keypoints = [
        keypoint for keypoint in person_all_keypoints
        if keypoint["visibility"] >= RELAXED_MIN_VISIBILITY and 0.0 <= keypoint["x"] <= 1.0 and 0.0 <= keypoint["y"] <= 1.0
    ]
    return relaxed_keypoints

# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Keypoint Detection API Ready"}

@api_router.post("/detect-pose")
async def detect_pose(file: UploadFile = File(...)):
    try:
        # Read the uploaded image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        landmarker = get_pose_landmarker()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        results = landmarker.detect(mp_image)

        if not results.pose_landmarks:
            raise HTTPException(status_code=400, detail="No pose detected in the image")
        
        # Get image dimensions
        height, width, _ = image.shape
        
        people = []
        keypoints = []
        all_keypoints = []

        for person_index, pose_landmarks in enumerate(results.pose_landmarks):
            person_all_keypoints = []

            for idx, landmark in enumerate(pose_landmarks):
                keypoint = build_keypoint(landmark, width, height, idx)
                person_all_keypoints.append(keypoint)
                all_keypoints.append({**keypoint, "person_index": person_index})

            person_keypoints = [
                {**keypoint, "person_index": person_index}
                for keypoint in filter_person_keypoints(person_all_keypoints)
            ]
            keypoints.extend(person_keypoints)
            people.append(
                {
                    "person_index": person_index,
                    "detected_keypoints": len(person_keypoints),
                    "model_keypoints": len(person_all_keypoints),
                    "keypoints": person_keypoints,
                    "all_keypoints": person_all_keypoints,
                }
            )

        if not people:
            raise HTTPException(
                status_code=400,
                detail="Pose was found, but no keypoints passed the visibility threshold for this image"
            )
        
        # Draw pose on image
        annotated_image = image.copy()

        for person in people:
            line_color, point_color = POSE_COLORS[person["person_index"] % len(POSE_COLORS)]
            visible_keypoint_ids = {kp["id"] for kp in person["keypoints"]}
            person_all_keypoints = {kp["id"]: kp for kp in person["all_keypoints"]}

            for start_idx, end_idx in POSE_CONNECTIONS:
                if start_idx in visible_keypoint_ids and end_idx in visible_keypoint_ids:
                    start_point = (
                        person_all_keypoints[start_idx]["pixel_x"],
                        person_all_keypoints[start_idx]["pixel_y"],
                    )
                    end_point = (
                        person_all_keypoints[end_idx]["pixel_x"],
                        person_all_keypoints[end_idx]["pixel_y"],
                    )
                    cv2.line(annotated_image, start_point, end_point, line_color, 3)

            for kp in person["keypoints"]:
                cv2.circle(annotated_image, (kp["pixel_x"], kp["pixel_y"]), 5, point_color, -1)
        
        # Generate unique ID for this detection
        detection_id = str(uuid.uuid4())
        
        # Save annotated image
        annotated_image_path = TEMP_DIR / f"{detection_id}_annotated.jpg"
        cv2.imwrite(str(annotated_image_path), annotated_image)
        
        # Create JSON output for Blender/Adobe Animate
        pose_data = {
            "metadata": {
                "detection_id": detection_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "image_width": width,
                "image_height": height,
                "format": "mediapipe_pose",
                "description": "Human pose keypoints for Blender/Adobe Animate import",
                "detected_people": len(people),
                "max_people_configured": MAX_POSES,
                "model_keypoints_per_person": len(people[0]["all_keypoints"]) if people else 0,
                "model_keypoints": len(all_keypoints),
                "detected_keypoints": len(keypoints),
                "visibility_threshold": MIN_VISIBILITY
            },
            "people": people,
            "keypoints": keypoints,
            "all_keypoints": all_keypoints,
            "connections": [
                {
                    "start": conn[0],
                    "end": conn[1],
                    "start_name": KEYPOINT_NAMES[conn[0]] if conn[0] < len(KEYPOINT_NAMES) else f"point_{conn[0]}",
                    "end_name": KEYPOINT_NAMES[conn[1]] if conn[1] < len(KEYPOINT_NAMES) else f"point_{conn[1]}"
                }
                for conn in POSE_CONNECTIONS
            ],
            "stick_figure": {
                "description": "Simplified stick figure representation for all detected people",
                "people": [
                    {
                        "person_index": person["person_index"],
                        "joints": person["keypoints"],
                        "bones": POSE_CONNECTIONS,
                    }
                    for person in people
                ],
                "joints": keypoints,
                "bones": POSE_CONNECTIONS
            }
        }
        
        # Save JSON file
        json_path = TEMP_DIR / f"{detection_id}_pose.json"
        with open(json_path, 'w') as f:
            json.dump(pose_data, f, indent=2)
        
        return {
            "success": True,
            "detection_id": detection_id,
            "people_count": len(people),
            "keypoints_count": len(keypoints),
            "model_keypoints_count": len(all_keypoints),
            "model_keypoints_per_person": len(people[0]["all_keypoints"]) if people else 0,
            "visibility_threshold": MIN_VISIBILITY,
            "message": f"Detected {len(people)} people successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@api_router.get("/download/{detection_id}/{file_type}")
async def download_file(detection_id: str, file_type: str):
    try:
        if file_type == "json":
            file_path = TEMP_DIR / f"{detection_id}_pose.json"
            media_type = "application/json"
            filename = f"pose_keypoints_{detection_id}.json"
        elif file_type == "image":
            file_path = TEMP_DIR / f"{detection_id}_annotated.jpg"
            media_type = "image/jpeg"
            filename = f"pose_annotated_{detection_id}.jpg"
        else:
            raise HTTPException(status_code=400, detail="Invalid file type. Use 'json' or 'image'")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_BUILD_DIR.exists():
    static_dir = FRONTEND_BUILD_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        requested_path = (FRONTEND_BUILD_DIR / full_path).resolve()
        build_root = FRONTEND_BUILD_DIR.resolve()
        if (
            full_path
            and requested_path.is_relative_to(build_root)
            and requested_path.exists()
            and requested_path.is_file()
        ):
            return FileResponse(requested_path)
        return FileResponse(FRONTEND_BUILD_DIR / "index.html")

@app.on_event("shutdown")
async def shutdown_db_client():
    global pose_landmarker
    if pose_landmarker is not None:
        pose_landmarker.close()
        pose_landmarker = None
    client.close()
