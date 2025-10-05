#!/usr/bin/env python3
"""
FS Source - OBS face detection source switcher
Monitors OBS video source for face detection and switches other sources visibility
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
import base64
from io import BytesIO
from PIL import Image

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FaceDetectionSwitcher:
    def __init__(self, config):
        self.config = config
        self.obs_ws = None
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
    
    def get_source_screenshot(self, source_name):
        """Get screenshot from OBS source"""
        try:
            # Get source screenshot
            response = self.obs_ws.call(obs_requests.GetSourceScreenshot(
                sourceName=source_name,
                imageFormat='png',
                imageWidth=640,
                imageHeight=480
            ))
            
            # Decode base64 image
            img_data = response.getImageData()
            if img_data.startswith('data:image/png;base64,'):
                img_data = img_data.split(',')[1]
            
            img_bytes = base64.b64decode(img_data)
            img = Image.open(BytesIO(img_bytes))
            
            # Convert to OpenCV format (BGR)
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            return frame
            
        except Exception as e:
            logger.error(f"Failed to get source screenshot: {e}")
            return None
    
    def detect_face(self, image):
        """Detect faces in the image using MediaPipe"""
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_image)
        
        if results.detections:
            for detection in results.detections:
                # Check if face is facing forward (confidence-based)
                if detection.score[0] > self.config.get('face_detection_confidence', 0.7):
                    return True
        return False
    
    def set_source_visibility_global(self, source_name, visible, exclude_scenes=None):
        """Set OBS source visibility across all scenes (with optional exclusions)"""
        if not self.obs_ws:
            return False
        
        if exclude_scenes is None:
            exclude_scenes = []
        
        try:
            if not source_name:
                logger.warning("Source name not configured")
                return False
            
            # Get list of all scenes
            scenes_response = self.obs_ws.call(obs_requests.GetSceneList())
            all_scenes = scenes_response.getScenes()
            
            scenes_modified = 0
            
            for scene in all_scenes:
                scene_name = scene['sceneName']
                
                # Skip excluded scenes
                if scene_name in exclude_scenes:
                    logger.debug(f"Skipping excluded scene: {scene_name}")
                    continue
                
                # Get scene items
                try:
                    scene_items = self.obs_ws.call(obs_requests.GetSceneItemList(sceneName=scene_name))
                    
                    for item in scene_items.getSceneItems():
                        if item['sourceName'] == source_name:
                            self.obs_ws.call(obs_requests.SetSceneItemEnabled(
                                sceneName=scene_name,
                                sceneItemId=item['sceneItemId'],
                                sceneItemEnabled=visible
                            ))
                            logger.debug(f"Set {source_name} to {visible} in '{scene_name}'")
                            scenes_modified += 1
                except Exception as e:
                    logger.debug(f"Could not modify {source_name} in scene '{scene_name}': {e}")
                    continue
            
            if scenes_modified > 0:
                excluded_note = f" (excluded: {', '.join(exclude_scenes)})" if exclude_scenes else ""
                logger.info(f"Set {source_name} visibility to {visible} in {scenes_modified} scene(s){excluded_note}")
                return True
            else:
                logger.warning(f"Source '{source_name}' not found in any scenes")
                return False
                
        except Exception as e:
            logger.error(f"Failed to toggle OBS source globally: {e}")
            return False
    
    def run(self):
        """Main execution loop"""
        logger.info("Starting FS Source face detection switcher...")
        
        # Connect to OBS
        if not self.connect_obs():
            logger.error("Cannot continue without OBS connection")
            return
        
        # Get configuration
        monitor_source = self.config.get('monitor_source_name')
        detection_scene = self.config.get('detection_scene_name')
        show_source = self.config.get('show_source_name')
        hide_source = self.config.get('hide_source_name')
        
        if not monitor_source:
            logger.error("monitor_source_name not configured")
            self.disconnect_obs()
            return
        
        # Build exclusion list for scenes where source should not be hidden
        exclude_scenes = []
        if detection_scene:
            exclude_scenes.append(detection_scene)
        
        logger.info(f"Monitoring source: {monitor_source}")
        if show_source:
            logger.info(f"Target source: {show_source}")
            logger.info(f"  • Face detected → Show {show_source} in ALL scenes")
            logger.info(f"  • No face → Hide {show_source} in all scenes")
            if exclude_scenes:
                logger.info(f"  • Exception: Keep {show_source} visible in: {', '.join(exclude_scenes)}")
        
        try:
            logger.info("Face detection active. Press Ctrl+C to quit.")
            
            while True:
                # Get screenshot from OBS source
                frame = self.get_source_screenshot(monitor_source)
                
                if frame is None:
                    logger.warning("Failed to get frame from source, retrying...")
                    time.sleep(self.config.get('check_interval', 0.5))
                    continue
                
                # Detect face
                current_face_detected = self.detect_face(frame)
                current_time = time.time()
                
                # Toggle sources if face detection state changed
                if current_face_detected != self.face_detected:
                    self.face_detected = current_face_detected
                    self.last_detection_time = current_time
                    
                    if self.face_detected:
                        logger.info("✓ Face detected - switching sources globally")
                        # Show the specified source in all scenes (no exclusions when showing)
                        if show_source:
                            self.set_source_visibility_global(show_source, True)
                    else:
                        logger.info("✗ No face detected - reverting sources globally")
                        # Hide the specified source (but keep it visible in detection scene)
                        if show_source:
                            self.set_source_visibility_global(show_source, False, exclude_scenes)
                
                # Optional: Show preview window (for debugging)
                if self.config.get('show_preview', False):
                    # Draw detection status on frame
                    status = "FACE DETECTED" if self.face_detected else "NO FACE"
                    color = (0, 255, 0) if self.face_detected else (0, 0, 255)
                    cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                               1, color, 2, cv2.LINE_AA)
                    cv2.imshow('FS Source - Face Detection', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Sleep to control check interval
                time.sleep(self.config.get('check_interval', 0.5))
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Runtime error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cv2.destroyAllWindows()
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
    required_keys = ['obs_host', 'obs_port', 'monitor_source_name']
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        logger.error(f"Missing required configuration keys: {missing_keys}")
        logger.info("Run setup.py to configure the application")
        sys.exit(1)
    
    # At least one action source should be configured
    if not config.get('show_source_name') and not config.get('hide_source_name'):
        logger.warning("Neither show_source_name nor hide_source_name configured")
        logger.warning("No sources will be toggled when face is detected")
    
    switcher = FaceDetectionSwitcher(config)
    switcher.run()

if __name__ == "__main__":
    main()
