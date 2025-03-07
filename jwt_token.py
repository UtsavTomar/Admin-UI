import requests
import os

def get_clerk_sign_token_for_user(user_id, expires_in_seconds=20):
    """
    Fetch a sign token from the Clerk API for a specific user.
    Uses the CLERK_API_KEY environment variable for authentication.
    
    Args:
        user_id (str): The ID of the user to generate a sign token for.
        expires_in_seconds (int): Token expiration time in seconds (default: 1200).
            
    Returns:
        str: The sign token.
        
    Raises:
        ValueError: If the CLERK_API_KEY environment variable is not set.
        Exception: If the API call fails.
    """
    # Get API key from environment variable
    api_key = os.environ.get("CLERK_SECRET_KEY")
    if not api_key:
        raise ValueError(
            "CLERK_API_KEY environment variable is not set. "
            "Set it using `export CLERK_API_KEY='your_api_key'` in Unix or `set CLERK_API_KEY=your_api_key` in Windows."
        )
    
    # Set up the request headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Prepare the request body
    body = {
        "user_id": user_id,
        "expires_in_seconds": expires_in_seconds
    }
    
    try:
        # Make the API request to Clerk
        response = requests.post(
            "https://api.clerk.dev/v1/sign_in_tokens",  # Use the correct endpoint
            headers=headers,
            json=body
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        return data.get("token")  # Return just the token string
    
    except requests.exceptions.RequestException as e:
        error_message = f"Error fetching Clerk sign token: {str(e)}"
        
        if e.response is not None:
            try:
                error_data = e.response.json()
                error_message = f"Clerk API error: {error_data.get('message', str(error_data))}"
            except Exception:
                error_message = f"Clerk API returned non-JSON response: {e.response.text}"
        
        raise Exception(error_message)
