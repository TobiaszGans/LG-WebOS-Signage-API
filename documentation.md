# LG WebOS Signage API Client

A Python library for automating and controlling LG WebOS Signage displays via their REST API.
\nPlease note this document discusses only the lg_webos_client library. The legacy and unified files are to launch playlists only as I need

## Quick Start

```python
from lg_webos_client import LGWebOSClient

# Create client
client = LGWebOSClient("10.0.30.2", "your_password")

# Login
if client.login():
    # Make API calls
    system_info = client.get_system_info()
    print(system_info)
```

## Installation

### Requirements
```bash
pip install requests
```

### Files
- `lg_webos_client.py` - Main client library
- `API_REFERENCE.md` - This documentation

## Authentication

The client handles authentication automatically using LG's double SHA512 algorithm:
```
pwd = SHA512(SHA512(password) + captcha)
```

### Login
```python
client = LGWebOSClient(host, password, port=3777)

# Login with verbose output
if client.login(verbose=True):
    print("Success!")
    
# Login silently
if client.login():
    # Make API calls
    pass
```

## Basic Usage

### Creating a Client
```python
client = LGWebOSClient(
    host="10.0.30.2",      # IP address of display
    password="your_pass",   # Display password
    port=3777               # Optional, defaults to 443
)
```

### Making API Calls

All API methods follow this pattern:
1. Login first
2. Call API methods
3. Handle responses

```python
if client.login():
    result = client.get_system_info()
    if result:
        print(result)
```

## Available API Methods

### System Information
```python
system_info = client.get_system_info()
```

**Returns:**
```json
{
  "payload": {
    "isLoad": true,
    "isHotel": false,
    "distributeEnabled": true,
    "tvChipType": "M16P3",
    "isOLED": false,
    ...
  }
}
```

---

## Adding New API Endpoints


| ❗  This portion is AI generated. All examples are just guesses of the LLM and probably are not valid endpoints!|
|----------------------------------------------|

When you discover new endpoints in the browser DevTools, add them to the client following this pattern:

### 1. Find the Endpoint in DevTools

Open browser DevTools (F12) → Network tab → Perform an action on the display → Find the API call

Example:
```
GET https://10.0.30.2:3777/api/content/list
POST https://10.0.30.2:3777/api/settings/update
```

### 2. Add Method to Client

Open `lg_webos_client.py` and add a new method at the bottom of the `LGWebOSClient` class:

#### For GET Requests:
```python
def get_content_list(self):
    """
    Get list of content on the display
    
    Returns:
        dict: List of content items
    """
    response = self._request('GET', '/api/content/list')
    return response.get('data') if response else None
```

#### For POST Requests:
```python
def update_settings(self, setting_name, setting_value):
    """
    Update a display setting
    
    Args:
        setting_name (str): Name of the setting
        setting_value: Value to set
    
    Returns:
        dict: Update result
    """
    data = {
        'name': setting_name,
        'value': setting_value
    }
    response = self._request('POST', '/api/settings/update', data=data)
    return response.get('data') if response else None
```

#### For PUT Requests:
```python
def update_content(self, content_id, updates):
    """
    Update content by ID
    
    Args:
        content_id (str): Content identifier
        updates (dict): Fields to update
    
    Returns:
        dict: Update result
    """
    response = self._request('PUT', f'/api/content/{content_id}', data=updates)
    return response.get('data') if response else None
```

#### For DELETE Requests:
```python
def delete_content(self, content_id):
    """
    Delete content by ID
    
    Args:
        content_id (str): Content identifier
    
    Returns:
        dict: Delete result
    """
    response = self._request('DELETE', f'/api/content/{content_id}')
    return response.get('data') if response else None
```

#### With Query Parameters:
```python
def get_content_by_type(self, content_type):
    """
    Get content filtered by type
    
    Args:
        content_type (str): Type of content (e.g., 'video', 'image')
    
    Returns:
        dict: Filtered content list
    """
    params = {'type': content_type}
    response = self._request('GET', '/api/content/list', params=params)
    return response.get('data') if response else None
```

### 3. Test Your New Method

```python
if client.login():
    # Test your new method
    content = client.get_content_list()
    print(content)
    
    # Update something
    result = client.update_settings('brightness', 80)
    print(result)
```

### 4. Document Your Method

Update this file with the new method:

```markdown
### Get Content List
\```python
content = client.get_content_list()
\```

**Returns:**
\```json
{
  "items": [...]
}
\```
```

## Method Template

Copy this template when adding new methods:

```python
def method_name(self, param1, param2=None):
    """
    Brief description of what this does
    
    Args:
        param1 (type): Description
        param2 (type, optional): Description. Defaults to None.
    
    Returns:
        dict: Description of return value
        
    Example:
        >>> result = client.method_name('value1', 'value2')
        >>> print(result)
    """
    # For simple GET
    response = self._request('GET', '/api/endpoint')
    return response.get('data') if response else None
    
    # For POST/PUT with data
    data = {'key': param1, 'key2': param2}
    response = self._request('POST', '/api/endpoint', data=data)
    return response.get('data') if response else None
    
    # For DELETE or GET with params
    params = {'filter': param1}
    response = self._request('DELETE', '/api/endpoint', params=params)
    return response.get('data') if response else None
```

## Error Handling

The client returns `None` when requests fail. Always check return values:

```python
result = client.get_system_info()
if result:
    print("Success:", result)
else:
    print("Failed to get system info")
```

For more detailed error handling:

```python
try:
    if not client.login():
        print("Login failed")
        return
    
    result = client.get_system_info()
    if result is None:
        print("API call failed")
    else:
        print("Success:", result)
        
except Exception as e:
    print(f"Error: {e}")
```

## Session Management

The client maintains a session automatically:
- Session cookies are stored in `client.session`
- Authentication state is tracked in `client._authenticated`
- Session persists across multiple API calls

```python
# Login once
client.login()

# Make multiple calls with the same session
info1 = client.get_system_info()
info2 = client.get_content_list()
info3 = client.get_settings()
```

## Advanced Usage

### Raw API Requests

If you need to make a custom request:

```python
# Direct access to _request method
response = client._request('GET', '/api/custom/endpoint')
if response:
    print(response)

# With data
response = client._request('POST', '/api/custom/endpoint', data={'key': 'value'})

# With params
response = client._request('GET', '/api/custom/endpoint', params={'filter': 'active'})
```

### Access Session Directly

```python
# Access the requests.Session object directly
client.session.get(f"{client.base_url}/custom/endpoint")
```

## Tips for Development

### 1. Finding API Endpoints

1. Open the display web interface in browser
2. Open DevTools (F12) → Network tab
3. Perform actions in the UI
4. Watch the Network tab for API calls
5. Note the:
   - Request URL (e.g., `/api/content/list`)
   - Method (GET/POST/PUT/DELETE)
   - Request payload (if any)
   - Response structure

### 2. Testing New Endpoints

```python
# Quick test script
if client.login(verbose=True):
    # Test new endpoint
    response = client._request('GET', '/api/new/endpoint')
    print(response)
```

### 3. Debugging

```python
# Enable verbose login
client.login(verbose=True)

# Print full response
import json
response = client.get_system_info()
print(json.dumps(response, indent=2))

# Check authentication status
print(f"Authenticated: {client._authenticated}")
```

### 4. Common Endpoint Patterns

Based on the system endpoint, likely patterns:
- `/api/system` - System information
- `/api/content` - Content management
- `/api/content/list` - List content
- `/api/content/{id}` - Specific content
- `/api/settings` - Display settings
- `/api/network` - Network configuration
- `/api/schedule` - Scheduling
- `/api/display` - Display controls

## Example: Complete Workflow

```python
from lg_webos_client import LGWebOSClient
import json

# Initialize
client = LGWebOSClient("10.0.30.2", "your_password")

# Login
if not client.login(verbose=True):
    print("Login failed")
    exit(1)

print("✓ Connected to display\n")

# Get system info
system_info = client.get_system_info()
if system_info:
    print("System Info:")
    print(json.dumps(system_info, indent=2))

# Add more API calls as you discover them...
# content = client.get_content_list()
# settings = client.get_settings()
# etc...
```

## Contributing

When you discover new endpoints:

1. Add the method to `lg_webos_client.py`
2. Document it in this file
3. Test it thoroughly
4. Keep methods organized by category (System, Content, Settings, etc.)

## API Discovery Checklist

- [ ] Found endpoint in DevTools
- [ ] Noted HTTP method (GET/POST/PUT/DELETE)
- [ ] Captured request payload structure
- [ ] Captured response structure
- [ ] Added method to client
- [ ] Tested method
- [ ] Documented method
- [ ] Added example usage

## Troubleshooting

### Login fails
- Verify IP address is correct
- Check password is correct
- Ensure display is accessible on network
- Try with `verbose=True` to see error details

### API call returns None
- Ensure you called `login()` first
- Check if endpoint exists (verify in browser)
- Check request payload matches what browser sends
- Use `verbose=True` during development

### Session expires
- Simply call `login()` again
- The client will re-authenticate automatically

## License

This client was reverse-engineered from the LG WebOS Signage web interface.
Use responsibly and in accordance with your display's terms of service.