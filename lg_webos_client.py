#!/usr/bin/env python3
"""
LG WebOS Signage API Client
A Python library for interacting with LG WebOS Signage displays

Usage:
    from lg_webos_client import LGWebOSClient
    
    client = LGWebOSClient("10.0.30.2", "your_password")
    if client.login():
        system_info = client.get_system_info()
        print(system_info)
"""

import requests
import hashlib
import time
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class LGWebOSClient:
    """Client for LG WebOS Signage API"""
    
    def __init__(self, host, password, port=443):
        """
        Initialize the client
        
        Args:
            host (str): IP address or hostname of the display
            password (str): Display password
            port (int): Port number (default: 3777)
        """
        self.base_url = f"https://{host}:{port}"
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self._authenticated = False
    
    def _encode_password(self, password, captcha):
        """
        Encode password using LG's algorithm: SHA512(SHA512(password) + captcha)
        
        Args:
            password (str): Display password
            captcha (str): Captcha text
            
        Returns:
            str: Encoded password hash
        """
        first_hash = hashlib.sha512(password.encode()).hexdigest()
        combined = first_hash + captcha
        final_hash = hashlib.sha512(combined.encode()).hexdigest()
        return final_hash
    
    def login(self, verbose=False):
        """
        Authenticate with the display
        
        Args:
            verbose (bool): Print detailed login information
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Step 1: Initialize session
            response = self.session.get(f"{self.base_url}/login/status")
            if response.status_code != 200:
                if verbose:
                    print(f"Failed to initialize session: {response.status_code}")
                return False
            
            # Step 2: Check if already logged in
            response = self.session.get(f"{self.base_url}/login/checkLoginStatus")
            data = response.json()
            if data.get('data', False):
                if verbose:
                    print("Already logged in")
                self._authenticated = True
                return True
            
            # Step 3: Get captcha
            timestamp = int(time.time() * 1000)
            captcha_img_response = self.session.get(f"{self.base_url}/login/captcha?time={timestamp}")
            if captcha_img_response.status_code != 200:
                if verbose:
                    print(f"Failed to get captcha image: {captcha_img_response.status_code}")
                return False
            
            response = self.session.get(f"{self.base_url}/login/captchaText")
            if response.status_code != 200:
                if verbose:
                    print(f"Failed to get captcha text: {response.status_code}")
                return False
            
            data = response.json()
            if data.get('status') != 200:
                if verbose:
                    print(f"Captcha request failed: {data}")
                return False
            
            captcha_data = data.get('data')
            captcha_text = captcha_data.get('text') if isinstance(captcha_data, dict) else captcha_data
            
            # Step 4: Login
            encoded_password = self._encode_password(self.password, captcha_text)
            payload = {"pwd": encoded_password}
            
            response = self.session.post(
                f"{self.base_url}/login/login",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            data = response.json()
            if data.get('status') == 200 and data.get('data', {}).get('result'):
                self._authenticated = True
                if verbose:
                    print("Login successful")
                return True
            else:
                if verbose:
                    print(f"Login failed: {data}")
                return False
                
        except Exception as e:
            if verbose:
                print(f"Login error: {e}")
            return False
    
    def _request(self, method, endpoint, data=None, params=None):
        """
        Make an authenticated API request
        
        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            endpoint (str): API endpoint
            data (dict): Request body data
            params (dict): URL parameters
            
        Returns:
            dict: Response JSON or None on failure
        """
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
            else:
                return None
                
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    # System API
    def get_system_info(self):
        """
        Get system information
        
        Returns:
            dict: System information
        """
        response = self._request('GET', '/api/system')
        return response.get('data') if response else None
    
    # Add more API methods below as you discover them
    # Example template:
    # def method_name(self, param1, param2=None):
    #     """
    #     Description of what this method does
    #     
    #     Args:
    #         param1: Description
    #         param2: Description (optional)
    #     
    #     Returns:
    #         dict: Description of return value
    #     """
    #     response = self._request('GET/POST/PUT/DELETE', '/api/endpoint', data={'key': 'value'})
    #     return response.get('data') if response else None


# Example usage
if __name__ == "__main__":
    # Configuration
    HOST = "10.0.30.2"
    PASSWORD = "Yourpassword!"  # Replace with your password
    
    # Create client and login
    client = LGWebOSClient(HOST, PASSWORD)
    
    if client.login(verbose=True):
        print("\n✓ Authentication successful!\n")
        
        # Example: Get system information
        system_info = client.get_system_info()
        if system_info:
            print("System Information:")
            print(f"  TV Chip Type: {system_info.get('payload', {}).get('tvChipType')}")
            print(f"  Hotel Mode: {system_info.get('payload', {}).get('isHotel')}")
            print(f"  OLED: {system_info.get('payload', {}).get('isOLED')}")
        
        # Add your API calls here
        
    else:
        print("✗ Authentication failed")