#!/usr/bin/env python3
"""
FS Source Native - Local camera version (no OBS WebSocket needed for capture)
Monitors local camera directly and switches OBS source visibility
Best for when camera and OBS are on the same machine
"""

import json
import time
import cv2
import mediapipe as mp
import numpy as np
from obswebsocket import obsws, requests as obs_requests
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FaceDetectionNative:
    def __init__(self, config):
        self.config = config
        self.obs_ws = None
        self.camera = None
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0, 
            min_detection_confidence=config.get('face_detection_confidence', 0.7)
        )
        self.face_detected = False
        self.last_detection_time = 0
        
    def connect_obs(self):
        """Connect to OBS WebSocket"""
        try:
            self.obs_ws = obsws(
                self.config['obs_host'], 
                self.config['obs_port'], 
                self.config.get('obs_password', '')
            )
            self.obs_ws.connect()
            logger.info(f"Connected to OBS at {self.config['obs_host']}:{self.config['obs_port']}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OBS: {e}")
            return False
    
    def disconnect_obs(self):
        """Disconnect from OBS WebSocket"""
        if self.obs_ws:
            self.obs_ws.disconnect()
            logger.info("Disconnected from OBS")
    
    def init_camera(self):
        """Initialize local camera"""
        camera_index = self.config.get('camera_index', 0)
        camera_path = self.config.get('camera_path')
        
        try:
            # Try camera path first if specified
            if camera_path:
                logger.info(f"Opening camera: {camera_path}")
                self.camera = cv2.VideoCapture(camera_path)
            else:
                logger.info(f"Opening camera index: {camera_index}")
                self.camera = cv2.VideoCapture(camera_index)
            
            if not self.camera.isOpened():
                logger.error(f"Failed to open camera")
                return False
            
            # Set camera properties for better performance
            width = self.config.get('camera_width', 640)
            height = self.config.get('camera_height', 480)
            fps = self.config.get('camera_fps', 30)
            
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.camera.set(cv2.CAP_PROP_FPS, fps)
            
            # Verify settings
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.camera.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False
    
    def release_camera(self):
        """Release camera resources"""
        if self.camera:
            self.camera.release()
            logger.info("Camera released")
    
    def detect_face(self, image):
        """Detect faces in the image using MediaPipe"""
        try:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.face_detection.process(rgb_image)
            
            if results.detections:
                for detection in results.detections:
                    # Check if face is facing forward (confidence-based)
                    if detection.score[0] > self.config.get('face_detection_confidence', 0.7):
                        return True
            return False
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return False
    
    def set_source_visibility_global(self, source_name, visible, exclude_scene=None):
        """Set OBS source visibility across all scenes, with optional scene exclusion"""
        if not self.obs_ws:
            return False
        
        try:
            if not source_name:
                logger.warning("Source name not configured")
                return False
            
            # Get all scenes
            scenes_response = self.obs_ws.call(obs_requests.GetSceneList())
            all_scenes = scenes_response.getScenes()
            
            changes_made = 0
            
            for scene in all_scenes:
                scene_name = scene['sceneName']
                
                # Skip excluded scene
                if exclude_scene and scene_name == exclude_scene:
                    logger.debug(f"Skipping excluded scene: {scene_name}")
                    continue
                
                # Get scene items
                scene_items = self.obs_ws.call(obs_requests.GetSceneItemList(sceneName=scene_name))
                
                for item in scene_items.getSceneItems():
                    if item['sourceName'] == source_name:
                        self.obs_ws.call(obs_requests.SetSceneItemEnabled(
                            sceneName=scene_name,
                            sceneItemId=item['sceneItemId'],
                            sceneItemEnabled=visible
                        ))
                        changes_made += 1
                        logger.debug(f"Set {source_name} to {visible} in scene '{scene_name}'")
            
            if changes_made > 0:
                action = "shown" if visible else "hidden"
                logger.info(f"✓ {source_name} {action} in {changes_made} scene(s)")
                return True
            else:
                logger.debug(f"Source '{source_name}' not found in any scenes")
                return False
                
        except Exception as e:
            logger.error(f"Failed to toggle OBS source globally: {e}")
            return False
    
    def run(self):
        """Main execution loop"""
        logger.info("="*60)
        logger.info("FS Source Native - Local Camera Mode")
        logger.info("="*60)
        
        # Initialize camera first
        if not self.init_camera():
            logger.error("Cannot continue without camera")
            return
        
        # Connect to OBS (only for source switching)
        if not self.connect_obs():
            logger.error("Cannot continue without OBS connection")
            self.release_camera()
            return
        
        # Get configuration
        show_source = self.config.get('show_source_name')
        hide_source = self.config.get('hide_source_name')
        
        logger.info("Face detection active (using local camera)")
        if show_source:
            logger.info(f"Will show: {show_source} when face detected")
        if hide_source:
            logger.info(f"Will hide: {hide_source} when face detected")
        logger.info("Press Ctrl+C to quit")
        
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        try:
            while True:
                # Read frame from local camera
                ret, frame = self.camera.read()
                
                if not ret:
                    consecutive_errors += 1
                    logger.warning(f"Failed to read from camera (attempt {consecutive_errors}/{max_consecutive_errors})")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("Too many consecutive camera errors")
                        break
                    
                    time.sleep(0.5)
                    continue
                
                consecutive_errors = 0
                
                # Detect face
                current_face_detected = self.detect_face(frame)
                
                # Toggle sources if face detection state changed
                if current_face_detected != self.face_detected:
                    self.face_detected = current_face_detected
                    self.last_detection_time = time.time()
                    
                    # Get exclusion scene
                    exclude_scene = self.config.get('detection_scene_name')
                    
                    if self.face_detected:
                        logger.info("👤 Face detected!")
                        # Show source in ALL scenes (no exclusions when showing)
                        if show_source:
                            self.set_source_visibility_global(show_source, True, exclude_scene=None)
                        # Hide other source in ALL scenes (no exclusions)
                        if hide_source:
                            self.set_source_visibility_global(hide_source, False, exclude_scene=None)
                    else:
                        logger.info("❌ Face gone")
                        # Hide source in ALL scenes EXCEPT the exclusion scene
                        if show_source:
                            self.set_source_visibility_global(show_source, False, exclude_scene=exclude_scene)
                        # Show other source in ALL scenes (no exclusions)
                        if hide_source:
                            self.set_source_visibility_global(hide_source, True, exclude_scene=None)
                
                # Optional: Show preview window (for debugging)
                if self.config.get('show_preview', False):
                    status = "FACE DETECTED" if self.face_detected else "NO FACE"
                    color = (0, 255, 0) if self.face_detected else (0, 0, 255)
                    cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                               1, color, 2, cv2.LINE_AA)
                    cv2.imshow('FS Source Native - Face Detection', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Sleep to control check interval
                time.sleep(self.config.get('check_interval', 0.1))
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Runtime error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cv2.destroyAllWindows()
            self.release_camera()
            self.disconnect_obs()

def load_config():
    """Load configuration from JSON file"""
    config_path = Path('config/obs_config.json')
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info("Configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    config = load_config()
    
    # Validate required config keys
    required_keys = ['obs_host', 'obs_port']
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        logger.error(f"Missing required configuration keys: {missing_keys}")
        logger.info("Run setup.py to configure the application")
        sys.exit(1)
    
    # At least one action source should be configured
    if not config.get('show_source_name') and not config.get('hide_source_name'):
        logger.warning("Neither show_source_name nor hide_source_name configured")
        logger.warning("No sources will be toggled when face is detected")
    
    native = FaceDetectionNative(config)
    native.run()

if __name__ == "__main__":
    main()
