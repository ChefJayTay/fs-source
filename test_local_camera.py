#!/usr/bin/env python3
"""
Test script to find and test local cameras
Helps identify which camera index or path to use for native mode
"""

import cv2
import sys

def test_camera_index(index):
    """Test a specific camera index"""
    print(f"Testing camera index {index}...")
    
    camera = cv2.VideoCapture(index)
    
    if not camera.isOpened():
        print(f"  ❌ Cannot open camera {index}")
        return False
    
    ret, frame = camera.read()
    if not ret:
        print(f"  ❌ Camera {index} opened but failed to read frame")
        camera.release()
        return False
    
    width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(camera.get(cv2.CAP_PROP_FPS))
    
    print(f"  ✅ Camera {index} works!")
    print(f"     Resolution: {width}x{height}")
    print(f"     FPS: {fps}")
    print(f"     Frame shape: {frame.shape}")
    
    camera.release()
    return True

def test_camera_path(path):
    """Test a specific camera device path"""
    print(f"Testing camera path: {path}...")
    
    camera = cv2.VideoCapture(path)
    
    if not camera.isOpened():
        print(f"  ❌ Cannot open camera {path}")
        return False
    
    ret, frame = camera.read()
    if not ret:
        print(f"  ❌ Camera {path} opened but failed to read frame")
        camera.release()
        return False
    
    width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(camera.get(cv2.CAP_PROP_FPS))
    
    print(f"  ✅ Camera {path} works!")
    print(f"     Resolution: {width}x{height}")
    print(f"     FPS: {fps}")
    print(f"     Frame shape: {frame.shape}")
    
    camera.release()
    return True

def live_preview(camera_ref):
    """Show live preview from camera"""
    print(f"\nStarting live preview from {camera_ref}...")
    print("Press 'q' to quit")
    
    camera = cv2.VideoCapture(camera_ref)
    
    if not camera.isOpened():
        print("❌ Cannot open camera for preview")
        return
    
    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print("Failed to read frame")
                break
            
            cv2.imshow('Camera Preview - Press Q to quit', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        print("\nPreview stopped")
    finally:
        camera.release()
        cv2.destroyAllWindows()

def main():
    print("FS Source - Local Camera Finder")
    print("="*50)
    print()
    
    # Test common camera indices
    print("Testing camera indices...")
    print("-" * 50)
    working_cameras = []
    
    for i in range(10):
        if test_camera_index(i):
            working_cameras.append(i)
        print()
    
    # Test video device paths (Linux)
    print("Testing video device paths...")
    print("-" * 50)
    import os
    if os.path.exists('/dev'):
        video_devices = [f'/dev/video{i}' for i in range(20, 30)]
        for device in video_devices:
            if os.path.exists(device):
                if test_camera_path(device):
                    working_cameras.append(device)
                print()
    
    # Summary
    print("="*50)
    print("Summary")
    print("="*50)
    
    if working_cameras:
        print(f"✅ Found {len(working_cameras)} working camera(s):")
        for cam in working_cameras:
            print(f"   - {cam}")
        
        print("\nTo use in native mode, set in config/obs_config.json:")
        if isinstance(working_cameras[0], int):
            print(f'   "camera_index": {working_cameras[0]}')
        else:
            print(f'   "camera_path": "{working_cameras[0]}"')
        
        # Ask if user wants to preview
        print()
        response = input("Test live preview of first camera? (y/n): ").lower()
        if response in ['y', 'yes']:
            live_preview(working_cameras[0])
    else:
        print("❌ No working cameras found")
        print("\nTroubleshooting:")
        print("1. Make sure a camera is connected")
        print("2. Check camera permissions")
        print("3. Try: ls -la /dev/video*")
        print("4. For USB cameras, try unplugging and replugging")

if __name__ == "__main__":
    main()
