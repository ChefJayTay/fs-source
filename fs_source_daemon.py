#!/usr/bin/env python3
"""
FS Source Daemon - Always-running version with OBS state monitoring
Monitors OBS video source for face detection and switches other sources visibility
Activates when OBS is running and connected
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
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fs_source_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FaceDetectionDaemon:
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
        self.is_active = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
    def connect_obs(self):
        """Connect to OBS WebSocket with retry logic"""
        try:
            self.obs_ws = obsws(
                self.config['obs_host'], 
                self.config['obs_port'], 
                self.config.get('obs_password', '')
            )
            self.obs_ws.connect()
            logger.info(f"Connected to OBS at {self.config['obs_host']}:{self.config['obs_port']}")
            self.reconnect_attempts = 0
            return True
        except Exception as e:
            self.reconnect_attempts += 1
            # Only log first few attempts to avoid spam
            if self.reconnect_attempts <= 3:
                logger.error(f"Failed to connect to OBS (attempt {self.reconnect_attempts}): {e}")
            elif self.reconnect_attempts % 12 == 0:  # Log every minute (5s * 12)
                logger.warning(f"Still unable to connect to OBS (attempt {self.reconnect_attempts})")
            
            # Clean up failed connection
            if self.obs_ws:
                try:
                    self.obs_ws.disconnect()
                except:
                    pass
                self.obs_ws = None
            return False
    
    def disconnect_obs(self):
        """Disconnect from OBS WebSocket"""
        if self.obs_ws:
            try:
                self.obs_ws.disconnect()
                logger.info("Disconnected from OBS")
            except:
                pass
            self.obs_ws = None
    
    def is_obs_active(self):
        """Check if OBS is running and connected"""
        if not self.obs_ws:
            return False
        
        try:
            # Just check if we can get version info (confirms OBS is responsive)
            version = self.obs_ws.call(obs_requests.GetVersion())
            return True
            
        except Exception as e:
            # Connection is broken, disconnect and let standby mode reconnect
            logger.debug(f"OBS not responsive: {e}")
            self.disconnect_obs()
            return False
    
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
    
    def standby_mode(self):
        """Standby mode - wait for OBS to become active"""
        logger.info("⏸️  STANDBY MODE - Waiting for OBS to start...")
        standby_check_interval = self.config.get('standby_check_interval', 5)
        
        while True:
            # Try to connect if not connected
            if not self.obs_ws:
                if self.connect_obs():
                    logger.info("OBS connection established")
            
            # Check if OBS is active
            if self.obs_ws and self.is_obs_active():
                logger.info("▶️  OBS is now active - Starting face detection")
                return True
            
            time.sleep(standby_check_interval)
    
    def active_mode(self):
        """Active mode - monitor and switch sources"""
        logger.info("🔍 ACTIVE MODE - Face detection enabled")
        
        # Get configuration
        monitor_source = self.config.get('monitor_source_name')
        show_source = self.config.get('show_source_name')
        hide_source = self.config.get('hide_source_name')
        
        if not monitor_source:
            logger.error("monitor_source_name not configured")
            return False
        
        logger.info(f"Monitoring source: {monitor_source}")
        if show_source:
            logger.info(f"Will show: {show_source} when face detected")
        if hide_source:
            logger.info(f"Will hide: {hide_source} when face detected")
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            while True:
                # Check if OBS is still active
                if not self.is_obs_active():
                    logger.info("OBS stopped or disconnected - Returning to standby")
                    # Reset sources to default state
                    if show_source:
                        self.set_source_visibility_global(show_source, False)
                    if hide_source:
                        self.set_source_visibility_global(hide_source, True)
                    self.face_detected = False
                    return True
                
                # Get screenshot from OBS source
                frame = self.get_source_screenshot(monitor_source)
                
                if frame is None:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("Too many consecutive errors, returning to standby")
                        return False
                    time.sleep(self.config.get('check_interval', 0.5))
                    continue
                
                consecutive_errors = 0
                
                # Detect face
                current_face_detected = self.detect_face(frame)
                
                # Toggle sources if face detection state changed
                if current_face_detected != self.face_detected:
                    self.face_detected = current_face_detected
                    self.last_detection_time = time.time()
                    
                    # Get exclusion scene (where monitoring source lives)
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
                    cv2.imshow('FS Source Daemon - Face Detection', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Sleep to control check interval
                time.sleep(self.config.get('check_interval', 0.5))
                
        except Exception as e:
            logger.error(f"Runtime error in active mode: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run(self):
        """Main daemon loop"""
        logger.info("="*60)
        logger.info("FS Source Daemon Starting...")
        logger.info("Daemon mode: Always running, smart standby")
        logger.info("="*60)
        
        try:
            while True:
                # Standby mode - wait for OBS to be active
                if not self.standby_mode():
                    logger.error("Standby mode failed, waiting before retry...")
                    time.sleep(30)
                    continue
                
                # Active mode - monitor and switch
                if not self.active_mode():
                    logger.warning("Active mode exited with error")
                    self.disconnect_obs()
                    time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("Daemon shutdown requested by user")
        except Exception as e:
            logger.error(f"Fatal error in daemon: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cv2.destroyAllWindows()
            self.disconnect_obs()
            logger.info("Daemon stopped")

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
    # Ensure logs directory exists
    Path('logs').mkdir(exist_ok=True)
    
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
    
    # Set default standby check interval
    if 'standby_check_interval' not in config:
        config['standby_check_interval'] = 5
    
    daemon = FaceDetectionDaemon(config)
    daemon.run()

if __name__ == "__main__":
    main()
