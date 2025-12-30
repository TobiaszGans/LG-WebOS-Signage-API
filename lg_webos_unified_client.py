#!/usr/bin/env python3
"""
LG WebOS Signage Unified Client
Automatically detects display type and uses appropriate API

Usage:
    from lg_webos_unified_client import LGWebOSClient
    
    client = LGWebOSClient("10.0.30.2", "your_password")
    if client.login():
        client.play_playlist("MyPlaylist.pls")
"""

import requests
import hashlib
import time
import json
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class LGWebOSClient:
    """Unified client for both modern and legacy LG WebOS Signage displays"""
    
    def __init__(self, host, password, port=None, display_type=None):
        """
        Initialize the client
        
        Args:
            host (str): IP address or hostname
            password (str): Display password
            port (int, optional): Port number (auto-detected if not provided)
            display_type (str, optional): 'modern' or 'legacy' (auto-detected if not provided)
        """
        self.host = host
        self.password = password
        self.port = port
        self.display_type = display_type
        self.session = requests.Session()
        self.session.verify = False
        self._authenticated = False
        
        # Will be set after detection
        self.base_url = None
        self._use_socketio = False
    
    def _detect_display_type(self, verbose=False):
        """
        Auto-detect display type by trying specific endpoints
        
        Returns:
            tuple: (display_type, port) where display_type is 'modern' or 'legacy'
        """
        if verbose:
            print("Auto-detecting display type...")
        
        # Test configurations to try
        test_configs = [
            (3777, 'modern'),
            (443, 'modern'),
            (443, 'legacy'),
        ]
        
        for port, potential_type in test_configs:
            try:
                # Test if we can reach the base URL
                base_url = f"https://{self.host}:{port}"
                
                # For modern displays, test the specific JSON captcha endpoint
                if potential_type == 'modern':
                    # Modern displays have /login/status endpoint
                    response = requests.get(f"{base_url}/login/status", verify=False, timeout=3)
                    if response.status_code != 200:
                        continue
                    
                    # Create a temporary session to test captcha endpoint
                    test_session = requests.Session()
                    test_session.verify = False
                    test_session.get(f"{base_url}/login/status", timeout=2)
                    
                    # Modern displays have a JSON captchaText endpoint
                    captcha_response = test_session.get(f"{base_url}/login/captchaText", timeout=2)
                    
                    # Modern display returns JSON with "status": 404, "message": "not exist captcha session"
                    # Legacy display returns HTML or different error
                    if captcha_response.status_code in [200, 404]:
                        try:
                            data = captcha_response.json()
                            # If it's valid JSON with 'status' field, it's modern
                            if 'status' in data and 'message' in data:
                                if verbose:
                                    print(f"  ✓ Detected: Modern display on port {port}")
                                return ('modern', port)
                        except:
                            # Not JSON, probably not modern
                            pass
                
                # For legacy displays, test the form-based login page
                else:
                    response = requests.get(f"{base_url}/login", verify=False, timeout=3)
                    if response.status_code == 200:
                        # Check if it's an HTML page (legacy)
                        content_type = response.headers.get('Content-Type', '')
                        if 'text/html' in content_type:
                            # Also check for captcha endpoint
                            captcha_test = requests.get(f"{base_url}/request/captchapng", verify=False, timeout=2)
                            if captcha_test.status_code in [200, 404]:
                                if verbose:
                                    print(f"  ✓ Detected: Legacy display on port {port}")
                                return ('legacy', port)
                
            except Exception as e:
                if verbose:
                    print(f"  Test failed for port {port} ({potential_type}): {e}")
                continue
        
        # If all detection failed, default to modern on 3777
        if verbose:
            print("  ? Could not detect, defaulting to modern display on port 3777")
        return ('modern', 3777)
    
    def login(self, verbose=False, max_retry_attempts=5):
        """
        Login to the display (auto-detects type if needed)
        
        Args:
            verbose (bool): Print detailed info
            max_retry_attempts (int): For legacy displays with OCR
            
        Returns:
            bool: True if successful
        """
        # Auto-detect if not specified
        if self.display_type is None or self.port is None:
            self.display_type, self.port = self._detect_display_type(verbose)
        
        self.base_url = f"https://{self.host}:{self.port}"
        
        if verbose:
            print(f"Using {self.display_type} display API on port {self.port}")
        
        # Use appropriate login method
        if self.display_type == 'modern':
            return self._login_modern(verbose)
        else:
            return self._login_legacy(verbose, max_retry_attempts)
    
    def _login_modern(self, verbose=False):
        """Login for modern displays (JSON API with captcha text)"""
        try:
            # Initialize session
            response = self.session.get(f"{self.base_url}/login/status")
            if response.status_code != 200:
                return False
            
            # Check if already logged in
            response = self.session.get(f"{self.base_url}/login/checkLoginStatus")
            data = response.json()
            if data.get('data', False):
                self._authenticated = True
                if verbose:
                    print("Already logged in")
                return True
            
            # Get captcha
            timestamp = int(time.time() * 1000)
            self.session.get(f"{self.base_url}/login/captcha?time={timestamp}")
            
            response = self.session.get(f"{self.base_url}/login/captchaText")
            if response.status_code != 200:
                return False
            
            data = response.json()
            if data.get('status') != 200:
                return False
            
            captcha_data = data.get('data')
            captcha_text = captcha_data.get('text') if isinstance(captcha_data, dict) else captcha_data
            
            # Encode password: SHA512(SHA512(password) + captcha)
            first_hash = hashlib.sha512(self.password.encode()).hexdigest()
            final_hash = hashlib.sha512((first_hash + captcha_text).encode()).hexdigest()
            
            # Login
            response = self.session.post(
                f"{self.base_url}/login/login",
                json={"pwd": final_hash},
                headers={'Content-Type': 'application/json'}
            )
            
            data = response.json()
            if data.get('status') == 200 and data.get('data', {}).get('result'):
                self._authenticated = True
                if verbose:
                    print("✓ Login successful (modern API)")
                return True
            
            return False
            
        except Exception as e:
            if verbose:
                print(f"Modern login error: {e}")
            return False
    
    def _login_legacy(self, verbose=False, max_attempts=5):
        """Login for legacy displays (form-based with OCR)"""
        # Check available OCR engines
        ocr_engines = []
        
        try:
            import easyocr
            ocr_engines.append('easyocr')
        except ImportError:
            pass
        
        try:
            from PIL import Image
            import pytesseract
            import io
            ocr_engines.append('tesseract')
        except ImportError:
            pass
        
        if not ocr_engines:
            if verbose:
                print("No OCR available. Install with:")
                print("  pip install easyocr  (recommended)")
                print("  or")
                print("  pip install pytesseract pillow")
            use_ocr = False
        else:
            use_ocr = True
            if verbose:
                print(f"Available OCR engines: {', '.join(ocr_engines)}")
        
        # Initialize EasyOCR reader if available (only once, it's slow to init)
        reader = None
        if 'easyocr' in ocr_engines:
            try:
                if verbose:
                    print("Initializing EasyOCR (this may take a moment)...")
                import easyocr
                reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                if verbose:
                    print("✓ EasyOCR ready")
            except Exception as e:
                if verbose:
                    print(f"EasyOCR init failed: {e}")
                ocr_engines.remove('easyocr')
        
        for attempt in range(1, max_attempts + 1):
            if verbose and max_attempts > 1:
                print(f"\nAttempt {attempt}/{max_attempts}...")
            
            try:
                # Initialize session
                self.session.get(f"{self.base_url}/")
                self.session.get(f"{self.base_url}/login")
                
                # Get captcha
                timestamp = int(time.time() * 1000)
                response = self.session.get(f"{self.base_url}/request/captchapng?timestamp={timestamp}")
                if response.status_code != 200:
                    continue
                
                captcha_image = response.content
                captcha = None
                
                # Try OCR
                if use_ocr:
                    # Method 1: EasyOCR (best for stylized fonts)
                    if reader and 'easyocr' in ocr_engines:
                        try:
                            if verbose:
                                print("  Trying EasyOCR...")
                            
                            import numpy as np
                            import cv2
                            
                            # Decode image
                            img = cv2.imdecode(np.frombuffer(captcha_image, np.uint8), cv2.IMREAD_GRAYSCALE)
                            
                            # Simple preprocessing
                            _, img = cv2.threshold(img, 140, 255, cv2.THRESH_BINARY)
                            
                            # EasyOCR
                            results = reader.readtext(img, detail=0, allowlist='0123456789')
                            
                            if results:
                                text = ''.join(results)
                                captcha = ''.join(filter(str.isdigit, text))
                                
                                if len(captcha) == 4:
                                    if verbose:
                                        print(f"  ✓ EasyOCR detected: {captcha}")
                                else:
                                    if verbose:
                                        print(f"  EasyOCR result: {captcha} (not 4 digits)")
                                    captcha = None
                        except Exception as e:
                            if verbose:
                                print(f"  EasyOCR error: {e}")
                            captcha = None
                    
                    # Method 2: Tesseract (fallback)
                    if captcha is None and 'tesseract' in ocr_engines:
                        try:
                            if verbose:
                                print("  Trying Tesseract...")
                            
                            from PIL import Image
                            import pytesseract
                            import io
                            import sys
                            import os
                            
                            # Windows: Set tesseract path
                            if sys.platform == 'win32':
                                possible_paths = [
                                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                                ]
                                for path in possible_paths:
                                    if os.path.exists(path):
                                        pytesseract.pytesseract.tesseract_cmd = path
                                        break
                            
                            # Simple preprocessing
                            image = Image.open(io.BytesIO(captcha_image))
                            image = image.convert('L')
                            image = image.point(lambda p: 0 if p < 180 else 255)
                            
                            # Tesseract
                            config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
                            text = pytesseract.image_to_string(image, config=config)
                            captcha = ''.join(filter(str.isdigit, text))
                            
                            if len(captcha) == 4:
                                if verbose:
                                    print(f"  ✓ Tesseract detected: {captcha}")
                            else:
                                if verbose:
                                    print(f"  Tesseract result: {captcha} (not 4 digits)")
                                captcha = None
                        except Exception as e:
                            if verbose:
                                print(f"  Tesseract error: {e}")
                            captcha = None
                
                # OCR failed - retry with new captcha (up to 3 times before manual)
                if captcha is None:
                    if attempt < max_attempts - 2:  # Save last 2 attempts for manual entry
                        if verbose:
                            print("  OCR failed, retrying with fresh captcha...")
                        self.session = requests.Session()
                        self.session.verify = False
                        continue
                    else:
                        # Manual captcha entry
                        with open('captcha.png', 'wb') as f:
                            f.write(captcha_image)
                        print("\nCaptcha saved to captcha.png")
                        captcha = input("Enter 4-digit captcha: ").strip()
                        
                        if len(captcha) != 4:
                            continue
                
                # Submit login
                if verbose:
                    print(f"  Submitting with captcha: {captcha}")
                
                response = self.session.post(
                    f"{self.base_url}/login",
                    data={'password': self.password, 'captcha': captcha},
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                
                if response.text.strip() == "success":
                    self._authenticated = True
                    self._use_socketio = True
                    if verbose:
                        print(f"  ✓ Login successful!")
                    return True
                else:
                    if verbose:
                        print(f"  ✗ Login failed: {response.text.strip()}")
                
                # Retry with fresh session
                if attempt < max_attempts:
                    self.session = requests.Session()
                    self.session.verify = False
                    
            except Exception as e:
                if verbose:
                    print(f"  Error: {e}")
                continue
        
        return False
    
    def _connect_socketio_if_needed(self):
        """Connect Socket.io for legacy displays"""
        if not self._use_socketio:
            return True
        
        if hasattr(self, 'sio'):
            return True
        
        try:
            import socketio
            
            self.sio = socketio.Client(ssl_verify=False)
            self.sio.connect(
                self.base_url,
                transports=['websocket', 'polling'],
                headers={'Cookie': '; '.join([f"{c.name}={c.value}" for c in self.session.cookies])}
            )
            return True
        except ImportError:
            print("Socket.io support requires: pip install python-socketio websocket-client")
            return False
        except Exception as e:
            print(f"Socket.io connection error: {e}")
            return False
    
    def _request(self, method, endpoint, data=None, params=None):
        """Make authenticated API request (modern displays)"""
        if not self._authenticated:
            raise Exception("Not authenticated. Call login() first.")
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=data, params=params)
            elif method == 'PUT':
                response = self.session.put(url, json=data, params=params)
            elif method == 'DELETE':
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    def _palm_service_call(self, service_id, params):
        """Call Luna service via Socket.io (legacy displays)"""
        if not self._connect_socketio_if_needed():
            return None
        
        import uuid
        message = {
            "serviceId": service_id,
            "params": params,
            "eventId": str(uuid.uuid4())
        }
        
        try:
            self.sio.emit("PalmServiceBridge.call", message)
            return {"sent": True}
        except Exception as e:
            print(f"Service call error: {e}")
            return None
    
    # Unified API methods
    
    def get_media(self, filters=None):
        """Get media list (works on modern displays only)"""
        if self.display_type != 'modern':
            print("get_media() only available on modern displays")
            return None
        
        if filters is None:
            filters = ["VIDEO", "IMAGE", "TEMPLATE", "SUPER_SIGN", "PLAY_LIST"]
        
        # Get storage IDs
        req_param = {"deviceType": ["internal signage", "usb", "sdcard"]}
        params = {"reqParam": json.dumps(req_param)}
        response = self._request('GET', '/storage/list', params=params)
        
        if not response:
            return None
        
        storage_ids = [d.get('deviceId') for d in response.get('data', {}).get('payload', {}).get('devices', [])]
        
        # Get media
        req_param = {
            "from": "MEDIA",
            "orderBy": "FILE_NAME",
            "desc": False,
            "limit": 100,
            "where": [{"prop": "mediaType", "op": "=", "val": filters}],
            "filter": [{"prop": "udn", "op": "=", "val": storage_ids}],
            "page": ""
        }
        params = {"reqParam": json.dumps(req_param)}
        response = self._request('GET', '/content/list', params=params)
        
        if response:
            return response.get('data', {}).get('payload', {}).get('results')
        return None
    
    def play_playlist(self, playlist_name, verbose=False):
        """
        Play a playlist (works on both display types)
        
        Args:
            playlist_name (str): Playlist filename or full path
            verbose (bool): Print debug info
            
        Returns:
            bool: True if successful
        """
        if not self._authenticated:
            raise Exception("Not authenticated. Call login() first.")
        
        
        
        if verbose:
            print(f"Playing playlist: {playlist_name}")
        
        if self.display_type == 'modern':
            # Modern display: REST API

            media = self.get_media(filters=["PLAY_LIST"])
            #print(json.dumps(media, indent=2))
            selected_playlist = next((obj for obj in media if obj['fileName'] == playlist_name), None)

            req_param = {
                "id": "com.webos.app.dsmp",
                "params": {"type":selected_playlist['mediaType'], "src":selected_playlist['fullPath']}
            }
            params = {"reqParam": json.dumps(req_param)}
            response = self._request('PUT', '/content/play/dsmp', params=params)
            return response and response.get('status') == 200
        else:
            # Ensure full path
            if not playlist_name.startswith('/'):
                playlist_name = f"/mnt/lg/appstore/signage/{playlist_name}"
            # Legacy display: Socket.io
            result = self._palm_service_call(
                service_id="luna://com.webos.applicationManager/launch",
                params={
                    "id": "com.webos.app.dsmp",
                    "params": {"type": "playlist", "src": playlist_name}
                }
            )
            return result is not None


# Example usage
if __name__ == "__main__":
    HOST = "10.0.30.2"  # or 10.0.30.1 for legacy
    PASSWORD = "your_password"
    
    # Create unified client (auto-detects display type)
    client = LGWebOSClient(HOST, PASSWORD)
    
    if client.login(verbose=True):
        print(f"\n✓ Connected to {client.display_type} display\n")
        
        # Play a playlist (works on both types)
        if client.play_playlist("Niedziela.pls", verbose=True):
            print("✓ Playlist started!")
        
    else:
        print("✗ Login failed")