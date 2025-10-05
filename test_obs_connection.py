#!/usr/bin/env python3
"""
Test OBS WebSocket connection and list available sources
"""

import json
import sys
from pathlib import Path
from obswebsocket import obsws, requests as obs_requests

def load_config():
    """Load configuration"""
    config_path = Path('config/obs_config.json')
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("Run setup.py first to create configuration")
        return None
    
    with open(config_path, 'r') as f:
        return json.load(f)

def test_connection(config):
    """Test OBS WebSocket connection"""
    print("Testing OBS WebSocket connection...")
    print(f"Host: {config['obs_host']}")
    print(f"Port: {config['obs_port']}")
    
    try:
        ws = obsws(
            config['obs_host'], 
            config['obs_port'], 
            config.get('obs_password', '')
        )
        ws.connect()
        print("✅ Successfully connected to OBS!")
        
        # Get OBS version
        version = ws.call(obs_requests.GetVersion())
        print(f"OBS Version: {version.getObsVersion()}")
        print(f"WebSocket Version: {version.getObsWebSocketVersion()}")
        
        return ws
    except Exception as e:
        print(f"❌ Failed to connect to OBS: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure OBS Studio is running")
        print("2. Enable WebSocket server: Tools → WebSocket Server Settings")
        print("3. Check host/port/password in config/obs_config.json")
        return None

def list_scenes(ws):
    """List all scenes"""
    print("\n" + "="*50)
    print("Available Scenes:")
    print("="*50)
    
    try:
        scenes = ws.call(obs_requests.GetSceneList())
        current_scene = scenes.getCurrentProgramSceneName()
        
        for scene in scenes.getScenes():
            scene_name = scene['sceneName']
            marker = " ← CURRENT" if scene_name == current_scene else ""
            print(f"  • {scene_name}{marker}")
        
        return current_scene
    except Exception as e:
        print(f"❌ Failed to list scenes: {e}")
        return None

def list_sources_in_scene(ws, scene_name):
    """List all sources in a scene"""
    print(f"\n" + "="*50)
    print(f"Sources in Scene: {scene_name}")
    print("="*50)
    
    try:
        scene_items = ws.call(obs_requests.GetSceneItemList(sceneName=scene_name))
        
        if not scene_items.getSceneItems():
            print("  (No sources in this scene)")
            return
        
        for item in scene_items.getSceneItems():
            source_name = item['sourceName']
            source_type = item.get('sourceType', 'unknown')
            enabled = item.get('sceneItemEnabled', True)
            status = "✓ Visible" if enabled else "✗ Hidden"
            print(f"  • {source_name}")
            print(f"    Type: {source_type} | Status: {status}")
            print(f"    ID: {item['sceneItemId']}")
        
    except Exception as e:
        print(f"❌ Failed to list sources: {e}")

def test_screenshot(ws, source_name):
    """Test getting a screenshot from a source"""
    print(f"\n" + "="*50)
    print(f"Testing Screenshot from: {source_name}")
    print("="*50)
    
    try:
        response = ws.call(obs_requests.GetSourceScreenshot(
            sourceName=source_name,
            imageFormat='png',
            imageWidth=320,
            imageHeight=240
        ))
        
        img_data = response.getImageData()
        img_size = len(img_data) if img_data else 0
        print(f"✅ Successfully captured screenshot")
        print(f"   Data size: {img_size:,} bytes")
        
    except Exception as e:
        print(f"❌ Failed to capture screenshot: {e}")

def main():
    print("FS Source - OBS Connection Test")
    print("="*50)
    
    # Load config
    config = load_config()
    if not config:
        sys.exit(1)
    
    # Test connection
    ws = test_connection(config)
    if not ws:
        sys.exit(1)
    
    # List scenes
    current_scene = list_scenes(ws)
    
    # List sources in configured scene
    scene_name = config.get('scene_name', current_scene)
    if scene_name:
        list_sources_in_scene(ws, scene_name)
    
    # Test screenshot if monitor source is configured
    monitor_source = config.get('monitor_source_name')
    if monitor_source:
        print(f"\nConfigured monitor source: {monitor_source}")
        response = input(f"Test screenshot capture from '{monitor_source}'? (y/n): ").lower()
        if response in ['y', 'yes']:
            test_screenshot(ws, monitor_source)
    
    # Disconnect
    ws.disconnect()
    print("\n✅ All tests completed!")
    print("\nIf you see your configured sources above, you're ready to run ./fs_source.py")

if __name__ == "__main__":
    main()
