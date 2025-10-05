#!/usr/bin/env python3
"""
Setup helper for FS Source - OBS Face Detection Switcher
"""

import json
import sys
from pathlib import Path

def setup_obs_config():
    """Interactive setup for OBS configuration"""
    print("FS Source - OBS Configuration Setup")
    print("=" * 40)
    
    config_path = Path('config/obs_config.json')
    
    # Load existing config if it exists
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        print("Found existing configuration. Current values will be shown in [brackets].")
    else:
        config = {}
    
    # OBS Connection Settings
    print("\n1. OBS WebSocket Connection Settings:")
    
    host = input(f"OBS Host [{config.get('obs_host', 'localhost')}]: ").strip()
    if host:
        config['obs_host'] = host
    elif 'obs_host' not in config:
        config['obs_host'] = 'localhost'
    
    port = input(f"OBS Port [{config.get('obs_port', 4455)}]: ").strip()
    if port:
        try:
            config['obs_port'] = int(port)
        except ValueError:
            print("Invalid port number, using default 4455")
            config['obs_port'] = 4455
    elif 'obs_port' not in config:
        config['obs_port'] = 4455
    
    password = input(f"OBS Password [{config.get('obs_password', 'YOUR_PASSWORD_HERE')}]: ").strip()
    if password:
        config['obs_password'] = password
    elif 'obs_password' not in config:
        config['obs_password'] = 'YOUR_PASSWORD_HERE'
    
    # OBS Scene and Source Settings
    print("\n2. OBS Source Settings:")
    print("Note: Source visibility changes will apply to the currently active scene in OBS")
    print("")
    
    monitor_source = input(f"Source to Monitor for faces (e.g., FS Source, 180° Camera) [{config.get('monitor_source_name', 'FS Source')}]: ").strip()
    if monitor_source:
        config['monitor_source_name'] = monitor_source
    elif 'monitor_source_name' not in config:
        config['monitor_source_name'] = 'FS Source'
    
    show_source = input(f"Source to Show when face detected [{config.get('show_source_name', 'Face Camera Source')}]: ").strip()
    if show_source:
        config['show_source_name'] = show_source
    elif 'show_source_name' not in config:
        config['show_source_name'] = 'Face Camera Source'
    
    hide_source = input(f"Source to Hide when face detected (optional) [{config.get('hide_source_name', '')}]: ").strip()
    if hide_source:
        config['hide_source_name'] = hide_source
    elif 'hide_source_name' not in config:
        config['hide_source_name'] = ''
    
    # Detection Settings
    print("\n3. Face Detection Settings:")
    
    confidence = input(f"Face Detection Confidence (0.0-1.0) [{config.get('face_detection_confidence', 0.7)}]: ").strip()
    if confidence:
        try:
            conf_val = float(confidence)
            if 0.0 <= conf_val <= 1.0:
                config['face_detection_confidence'] = conf_val
            else:
                print("Confidence must be between 0.0 and 1.0, using default 0.7")
                config['face_detection_confidence'] = 0.7
        except ValueError:
            print("Invalid confidence value, using default 0.7")
            config['face_detection_confidence'] = 0.7
    elif 'face_detection_confidence' not in config:
        config['face_detection_confidence'] = 0.7
    
    interval = input(f"Check Interval in seconds [{config.get('check_interval', 0.1)}]: ").strip()
    if interval:
        try:
            config['check_interval'] = float(interval)
        except ValueError:
            print("Invalid interval, using default 0.1")
            config['check_interval'] = 0.1
    elif 'check_interval' not in config:
        config['check_interval'] = 0.1
    
    # Additional Settings
    print("\n4. Additional Settings:")
    
    preview = input(f"Show preview window? (y/n) [{config.get('show_preview', False)}]: ").strip().lower()
    if preview in ['y', 'yes']:
        config['show_preview'] = True
    elif preview in ['n', 'no']:
        config['show_preview'] = False
    elif 'show_preview' not in config:
        config['show_preview'] = False
    
    # Save configuration
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"\n✅ Configuration saved to {config_path}")
    print("\nConfiguration Summary:")
    print(f"  - OBS Host: {config['obs_host']}:{config['obs_port']}")
    print(f"  - Monitor Source: {config['monitor_source_name']}")
    print(f"  - Show Source: {config.get('show_source_name', 'None') or 'None'}")
    print(f"  - Hide Source: {config.get('hide_source_name', 'None') or 'None'}")
    print("\nNext steps:")
    print("1. Make sure OBS Studio is running")
    print("2. Enable WebSocket server in OBS (Tools → WebSocket Server Settings)")
    print("3. Set the password in OBS to match your configuration")
    print("4. Make sure your sources exist:")
    print(f"   - {config['monitor_source_name']} (monitored for face detection)")
    if config.get('show_source_name'):
        print(f"   - {config['show_source_name']} (will be shown when face detected)")
    if config.get('hide_source_name'):
        print(f"   - {config['hide_source_name']} (will be hidden when face detected)")
    print("\n5. Test connection: python test_obs_connection.py")
    print("6. Run standard mode: ./run.sh")
    print("   OR daemon mode: ./run_daemon.sh")

def show_obs_setup_instructions():
    """Show OBS setup instructions"""
    print("\nOBS Studio Setup Instructions:")
    print("=" * 35)
    print("1. Open OBS Studio")
    print("2. Go to Tools → WebSocket Server Settings")
    print("3. Check 'Enable WebSocket server'")
    print("4. Set Server Port (default: 4455)")
    print("5. Set Server Password (match your config)")
    print("6. Click 'Show Connect Info' to verify settings")
    print("7. Create a Scene with your camera source")
    print("8. Make sure the source name matches your config")

def main():
    print("FS Source Setup Helper")
    print("=" * 25)
    print("1. Configure OBS settings")
    print("2. Show OBS setup instructions")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == '1':
        setup_obs_config()
    elif choice == '2':
        show_obs_setup_instructions()
    elif choice == '3':
        sys.exit(0)
    else:
        print("Invalid choice")
        sys.exit(1)

if __name__ == "__main__":
    main()