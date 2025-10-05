#!/usr/bin/env python3
"""
Test script to verify camera and face detection functionality
"""

import cv2
import mediapipe as mp
import sys

def test_camera():
    """Test camera access"""
    print("Testing camera access...")
    
    # Try different camera indices
    camera_indices = [0, 1, 2, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]
    
    for i in camera_indices:
        print(f"Trying camera index {i}...")
        camera = cv2.VideoCapture(i)
        
        if camera.isOpened():
            ret, frame = camera.read()
            if ret:
                print(f"✅ Camera {i} working - Frame size: {frame.shape}")
                camera.release()
                return True, i
            else:
                print(f"  Camera {i} opened but failed to read frame")
        
        camera.release()
    
    print("❌ No working camera found")
    return False, None

def test_face_detection():
    """Test MediaPipe face detection"""
    print("Testing MediaPipe face detection...")
    
    try:
        mp_face_detection = mp.solutions.face_detection
        face_detection = mp_face_detection.FaceDetection(
            model_selection=0, 
            min_detection_confidence=0.7
        )
        print("✅ MediaPipe face detection initialized")
        return True
    except Exception as e:
        print(f"❌ MediaPipe face detection failed: {e}")
        return False

def test_live_detection():
    """Test live face detection with camera"""
    print("Testing live face detection (press 'q' to quit)...")
    
    # Find working camera
    camera_found, camera_index = test_camera()
    if not camera_found:
        print("❌ Cannot open camera for live test")
        return False
    
    camera = cv2.VideoCapture(camera_index)
    if not camera.isOpened():
        print("❌ Cannot open camera for live test")
        return False
    
    mp_face_detection = mp.solutions.face_detection
    mp_drawing = mp.solutions.drawing_utils
    face_detection = mp_face_detection.FaceDetection(
        model_selection=0, 
        min_detection_confidence=0.7
    )
    
    print("Live detection active. Press 'q' to quit.")
    
    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                break
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_frame)
            
            # Draw face detections
            if results.detections:
                for detection in results.detections:
                    mp_drawing.draw_detection(frame, detection)
                    print(f"Face detected with confidence: {detection.score[0]:.2f}")
            
            cv2.imshow('Face Detection Test', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        camera.release()
        cv2.destroyAllWindows()
        print("✅ Live detection test completed")

def main():
    print("FS Source - Camera and Face Detection Test")
    print("=" * 50)
    
    # Test camera
    camera_found, camera_index = test_camera()
    if not camera_found:
        print("Camera test failed. Check camera connection.")
        sys.exit(1)
    
    print(f"Found working camera at index: {camera_index}")
    
    # Test face detection
    if not test_face_detection():
        print("Face detection test failed. Check MediaPipe installation.")
        sys.exit(1)
    
    # Ask user if they want to run live test
    response = input("\nRun live face detection test? (y/n): ").lower()
    if response in ['y', 'yes']:
        test_live_detection()
    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    main()