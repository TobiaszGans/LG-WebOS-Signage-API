#!/usr/bin/env python3
"""
LG WebOS Signage API Client (Legacy/Older Models)
For older LG WebOS Signage displays that use form-based authentication

Compatible with displays using:
- Port 443 (default HTTPS)
- Express.js session management
- PNG captcha images
- Socket.io communication

Usage:
    from lg_webos_legacy_client import LGWebOSLegacyClient
    
    client = LGWebOSLegacyClient("10.0.30.1", "your_password")
    if client.login():
        # Make API calls
        pass
"""

import requests
import time
import io
from urllib3.exceptions import InsecureRequestWarning
from PIL import Image

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class LGWebOSLegacyClient:
    """Client for older LG WebOS Signage displays"""
    
    def __init__(self, host, password, port=443, use_ocr=True):
        """
        Initialize the client
        
        Args:
            host (str): IP address or hostname of the display
            password (str): Display password (plain text, no encoding needed)
            port (int): Port number (default: 443)
            use_ocr (bool): Attempt OCR on captcha (default: True)
        """
        self.base_url = f"https://{host}:{port}"
        self.password = password
        self.use_ocr = use_ocr
        self.session = requests.Session()
        self.session.verify = False
        self._authenticated = False
        self._captcha_image = None
    
    def _ocr_captcha(self, image_bytes):
        """
        Use OCR to read captcha text from image
        
        Args:
            image_bytes: PNG image bytes
            
        Returns:
            str: Detected text or None if failed
        """
        if not self.use_ocr:
            return None
        
        try:
            import pytesseract
            import sys
            
            # Windows: Set tesseract path if not in PATH
            if sys.platform == 'win32':
                import os
                possible_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                    r'C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME'))
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
            
            # Open image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert directly to grayscale
            image = image.convert('L')
            
            # Apply binary threshold (180 works best for LG captcha)
            # Keep it simple - no padding, no scaling
            threshold = 180
            image = image.point(lambda p: 0 if p < threshold else 255)
            
            # Configure tesseract
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
            
            # Extract text
            text = pytesseract.image_to_string(image, config=custom_config)
            
            # Clean the result
            text = ''.join(filter(str.isdigit, text))
            
            # Captcha should be exactly 4 digits
            if len(text) == 4:
                return text
            
            return None
            
        except ImportError:
            print("Warning: pytesseract not installed. Install with: pip install pytesseract")
            print("Also ensure Tesseract OCR is installed on your system")
            return None
        except Exception as e:
            print(f"OCR error: {e}")
            return None
    
    def _show_captcha_image(self, image_bytes):
        """
        Display captcha image to user
        
        Args:
            image_bytes: PNG image bytes
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.show()
            print("Captcha image opened in default viewer")
        except Exception as e:
            print(f"Could not display image: {e}")
            print("Captcha image saved to 'captcha.png'")
    
    def _save_captcha_image(self, image_bytes, filename='captcha.png'):
        """
        Save captcha image to file
        
        Args:
            image_bytes: PNG image bytes
            filename: Output filename
        """
        try:
            with open(filename, 'wb') as f:
                f.write(image_bytes)
            print(f"Captcha saved to {filename}")
        except Exception as e:
            print(f"Could not save image: {e}")
    
    def login(self, captcha=None, verbose=False, show_captcha=False, save_captcha=False):
        """
        Authenticate with the display
        
        Args:
            captcha (str): Pre-provided captcha (optional, for automation)
            verbose (bool): Print detailed login information
            show_captcha (bool): Display captcha image to user
            save_captcha (bool): Save captcha image to file
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Step 1: Initialize session
            if verbose:
                print("Step 1: Initializing session...")
            response = self.session.get(f"{self.base_url}/")
            if response.status_code != 200:
                if verbose:
                    print(f"Failed to initialize session: {response.status_code}")
                return False
            
            # Step 2: Load login page
            if verbose:
                print("Step 2: Loading login page...")
            response = self.session.get(f"{self.base_url}/login")
            if response.status_code != 200:
                if verbose:
                    print(f"Failed to load login page: {response.status_code}")
                return False
            
            # Step 3: Get captcha image
            if verbose:
                print("Step 3: Getting captcha...")
            timestamp = int(time.time() * 1000)
            response = self.session.get(f"{self.base_url}/request/captchapng?timestamp={timestamp}")
            if response.status_code != 200:
                if verbose:
                    print(f"Failed to get captcha: {response.status_code}")
                return False
            
            captcha_image_bytes = response.content
            self._captcha_image = captcha_image_bytes
            
            # Step 4: Solve captcha
            if captcha is None:
                # Try OCR first
                if self.use_ocr:
                    if verbose:
                        print("Step 4: Attempting OCR...")
                    captcha = self._ocr_captcha(captcha_image_bytes)
                    if captcha:
                        if verbose:
                            print(f"  OCR detected: {captcha}")
                    else:
                        if verbose:
                            print("  OCR failed")
                        return False
                else:
                    # Manual captcha
                    if save_captcha:
                        self._save_captcha_image(captcha_image_bytes)
                    if show_captcha:
                        self._show_captcha_image(captcha_image_bytes)
                    
                    captcha = input("Enter 4-digit captcha: ").strip()
                    
                    if len(captcha) != 4 or not captcha.isdigit():
                        print("Invalid captcha format. Must be 4 digits.")
                        return False
            
            # Step 5: Submit login
            if verbose:
                print(f"Step 5: Submitting login with captcha: {captcha}")
            
            login_data = {
                'password': self.password,
                'captcha': captcha
            }
            
            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                if verbose:
                    print(f"  Login request failed: {response.status_code}")
                return False
            
            # Check response
            response_text = response.text.strip()
            
            if response_text == "success":
                self._authenticated = True
                if verbose:
                    print("  ✓ Login successful!")
                return True
            else:
                if verbose:
                    print(f"  ✗ Login failed: {response_text}")
                return False
                
        except Exception as e:
            if verbose:
                print(f"  Login error: {e}")
            return False
    
    def login_with_retry(self, max_attempts=10, verbose=False):
        """
        Keep trying to login until successful (handles OCR errors)
        
        Each captcha is random, so we'll eventually get one without the problematic "1"
        
        Args:
            max_attempts (int): Maximum number of attempts (default: 10)
            verbose (bool): Print progress
            
        Returns:
            bool: True if login successful, False if all attempts failed
        """
        if verbose:
            print(f"Attempting login (up to {max_attempts} attempts)...")
        
        for attempt in range(1, max_attempts + 1):
            if verbose:
                print(f"\nAttempt {attempt}/{max_attempts}:")
            
            # Each attempt gets a fresh captcha
            if self.login(verbose=verbose):
                if verbose:
                    print(f"\n✓ Success on attempt {attempt}!")
                return True
            
            # Reset session for next attempt
            if attempt < max_attempts:
                self.session = requests.Session()
                self.session.verify = False
                self._authenticated = False
                if verbose:
                    print(f"  Retrying with fresh captcha...")
        
        if verbose:
            print(f"\n✗ Failed after {max_attempts} attempts")
        return False
        """
        Authenticate with the display
        
        Args:
            captcha (str): Pre-provided captcha (optional, for automation)
            verbose (bool): Print detailed login information
            show_captcha (bool): Display captcha image to user
            save_captcha (bool): Save captcha image to file
            retry_on_fail (bool): If OCR login fails and last digit is 7, try with 1
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Step 1: Initialize session
            if verbose:
                print("Step 1: Initializing session...")
            response = self.session.get(f"{self.base_url}/")
            if response.status_code != 200:
                if verbose:
                    print(f"Failed to initialize session: {response.status_code}")
                return False
            
            # Step 2: Load login page
            if verbose:
                print("Step 2: Loading login page...")
            response = self.session.get(f"{self.base_url}/login")
            if response.status_code != 200:
                if verbose:
                    print(f"Failed to load login page: {response.status_code}")
                return False
            
            # Step 3: Get captcha image
            if verbose:
                print("Step 3: Getting captcha...")
            timestamp = int(time.time() * 1000)
            response = self.session.get(f"{self.base_url}/request/captchapng?timestamp={timestamp}")
            if response.status_code != 200:
                if verbose:
                    print(f"Failed to get captcha: {response.status_code}")
                return False
            
            captcha_image_bytes = response.content
            self._captcha_image = captcha_image_bytes
            
            # Step 4: Solve captcha
            if captcha is None:
                # Try OCR first
                if self.use_ocr:
                    if verbose:
                        print("Step 4a: Attempting OCR...")
                    captcha = self._ocr_captcha(captcha_image_bytes)
                    if captcha:
                        if verbose:
                            print(f"OCR detected: {captcha}")
                    else:
                        if verbose:
                            print("OCR failed or low confidence")
                
                # If OCR failed or disabled, ask user
                if captcha is None:
                    if verbose:
                        print("Step 4b: Manual captcha entry required")
                    
                    # Save/show captcha if requested
                    if save_captcha:
                        self._save_captcha_image(captcha_image_bytes)
                    if show_captcha:
                        self._show_captcha_image(captcha_image_bytes)
                    
                    # Get captcha from user
                    captcha = input("Enter 4-digit captcha: ").strip()
                    
                    if len(captcha) != 4 or not captcha.isdigit():
                        print("Invalid captcha format. Must be 4 digits.")
                        return False
            
            # Step 5: Submit login
            if verbose:
                print(f"Step 5: Submitting login with captcha: {captcha}")
            
            login_data = {
                'password': self.password,
                'captcha': captcha
            }
            
            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,  # Form data, not JSON
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                if verbose:
                    print(f"Login request failed: {response.status_code}")
                return False
            
            # Check response
            response_text = response.text.strip()
            if verbose:
                print(f"Login response: {response_text}")
            
            if response_text == "success":
                self._authenticated = True
                if verbose:
                    print("✓ Login successful!")
                return True
            elif "fail" in response_text.lower() and retry_on_fail and self.use_ocr:
                # Login failed - try alternative if last digit is 7
                if captcha and len(captcha) == 4 and captcha[-1] == '7':
                    if verbose:
                        print(f"✗ Login failed with {captcha}")
                        print(f"  Retrying with alternative (1 instead of 7)...")
                    
                    # Try with 1 instead of 7
                    alt_captcha = captcha[:-1] + '1'
                    
                    # Need to get a fresh captcha image
                    timestamp = int(time.time() * 1000)
                    response = self.session.get(f"{self.base_url}/request/captchapng?timestamp={timestamp}")
                    if response.status_code == 200:
                        # Try OCR again on new captcha
                        captcha_image_bytes = response.content
                        new_captcha = self._ocr_captcha(captcha_image_bytes)
                        if new_captcha and new_captcha[-1] == '7':
                            # Same issue, try with 1
                            new_captcha = new_captcha[:-1] + '1'
                        
                        if new_captcha:
                            return self.login(captcha=new_captcha, verbose=verbose, 
                                            show_captcha=show_captcha, save_captcha=save_captcha,
                                            retry_on_fail=False)  # Don't recurse infinitely
                
                if verbose:
                    print(f"✗ Login failed: {response_text}")
                return False
            elif "restricted" in response_text.lower():
                if verbose:
                    print(f"✗ Login restricted: {response_text}")
                return False
            else:
                if verbose:
                    print(f"Unknown response: {response_text}")
                return False
                
        except Exception as e:
            if verbose:
                print(f"Login error: {e}")
            return False
    
    def logout(self):
        """
        Logout from the display
        
        Returns:
            bool: True if successful
        """
        try:
            response = self.session.get(f"{self.base_url}/logout")
            self._authenticated = False
            return response.status_code == 200
        except Exception as e:
            print(f"Logout error: {e}")
            return False
    
    def is_authenticated(self):
        """
        Check if currently authenticated
        
        Returns:
            bool: Authentication status
        """
        return self._authenticated
    
    def connect_socketio(self):
        """
        Connect to Socket.io server for API communication
        
        Returns:
            bool: True if connected successfully
        """
        try:
            import socketio
            
            # Create Socket.io client
            self.sio = socketio.Client(ssl_verify=False)
            
            @self.sio.event
            def connect():
                if hasattr(self, '_verbose') and self._verbose:
                    print("Socket.io connected")
            
            @self.sio.event
            def disconnect():
                if hasattr(self, '_verbose') and self._verbose:
                    print("Socket.io disconnected")
            
            # Connect to Socket.io endpoint
            self.sio.connect(
                self.base_url,
                transports=['websocket', 'polling'],
                headers={'Cookie': '; '.join([f"{c.name}={c.value}" for c in self.session.cookies])}
            )
            
            return True
            
        except ImportError:
            print("Socket.io support requires: pip install python-socketio")
            return False
        except Exception as e:
            print(f"Socket.io connection error: {e}")
            return False
    
    def _palm_service_call(self, service_id, params, verbose=False):
        """
        Call a webOS Luna service via Socket.io
        
        Args:
            service_id (str): Luna service URI (e.g., "luna://com.webos.service.cbox/...")
            params (dict): Service parameters
            verbose (bool): Print debug info
            
        Returns:
            dict: Response data or None
        """
        if not hasattr(self, 'sio'):
            if verbose:
                print("Socket.io not connected, attempting connection...")
            if not self.connect_socketio():
                return None
        
        import uuid
        event_id = str(uuid.uuid4())
        
        message = {
            "serviceId": service_id,
            "params": params,
            "eventId": event_id
        }
        
        if verbose:
            print(f"Calling Luna service: {service_id}")
            print(f"  Params: {params}")
        
        try:
            # Send via Socket.io
            self.sio.emit("PalmServiceBridge.call", message)
            
            # Note: For async responses, would need to handle events
            # For now, just send the command
            return {"sent": True, "eventId": event_id}
            
        except Exception as e:
            if verbose:
                print(f"Error calling service: {e}")
            return None
    
    def play_playlist(self, playlist_path, verbose=False):
        """
        Play a playlist file
        
        Args:
            playlist_path (str): Path to playlist file
                Examples:
                - "/mnt/lg/appstore/signage/Niedziela.pls"
                - "Niedziela.pls" (will prepend path automatically)
            verbose (bool): Print debug info
            
        Returns:
            bool: True if command sent successfully
        """
        # Ensure full path
        if not playlist_path.startswith('/'):
            playlist_path = f"/mnt/lg/appstore/signage/{playlist_path}"
        
        if verbose:
            print(f"Playing playlist: {playlist_path}")
        
        # Use applicationManager to launch DSMP with playlist
        result = self._palm_service_call(
            service_id="luna://com.webos.applicationManager/launch",
            params={
                "id": "com.webos.app.dsmp",
                "params": {
                    "type": "playlist",
                    "src": playlist_path
                }
            },
            verbose=verbose
        )
        
        return result is not None
    
    def list_playlists(self, verbose=False):
        """
        List available playlists
        
        Note: This is a placeholder - actual implementation would need
        to query the content database via Socket.io
        
        Returns:
            list: Playlist information
        """
        # This would require implementing content list query via Socket.io
        # For now, return None to indicate not implemented
        if verbose:
            print("Playlist listing via Socket.io not yet implemented")
            print("Playlists are typically at: /mnt/lg/appstore/signage/*.pls")
        return None
    
    def _request(self, method, endpoint, data=None, params=None):
        """
        Make an authenticated request
        
        Args:
            method (str): HTTP method
            endpoint (str): API endpoint
            data (dict): Request body
            params (dict): URL parameters
            
        Returns:
            requests.Response: Response object
        """
        if not self._authenticated:
            raise Exception("Not authenticated. Call login() first.")
        
        url = f"{self.base_url}{endpoint}"
        
        if method == 'GET':
            return self.session.get(url, params=params)
        elif method == 'POST':
            return self.session.post(url, data=data, params=params)
        elif method == 'PUT':
            return self.session.put(url, data=data, params=params)
        elif method == 'DELETE':
            return self.session.delete(url, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")
    
    # Add API methods here as you discover them
    # These will likely use Socket.io events rather than REST endpoints
    # Example placeholder:
    
    def get_status(self):
        """
        Get login status
        
        Returns:
            str: Status response
        """
        try:
            response = self._request('GET', '/getLoginStatus')
            return response.text
        except Exception as e:
            print(f"Error getting status: {e}")
            return None


# Example usage
if __name__ == "__main__":
    HOST = "10.0.30.1"
    PASSWORD = "LifeHouse4God!"
    
    # Create client with OCR enabled
    client = LGWebOSLegacyClient(HOST, PASSWORD, use_ocr=True)
    
    print("Attempting login with OCR...")
    if client.login(verbose=True, save_captcha=True):
        print("\n✓ Authentication successful!")
        
        # Test status
        status = client.get_status()
        print(f"Status: {status}")
        
        # Add your API calls here
        
    else:
        print("\n✗ Authentication failed")
        print("\nTroubleshooting:")
        print("1. Check if pytesseract is installed: pip install pytesseract pillow")
        print("2. Install Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
        print("3. Try with show_captcha=True to see the image")