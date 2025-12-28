import urllib.request
import json
import base64
import os
import sys

def generate_image_from_api(prompt, output_path, api_key, model="imagen-3.0-generate-001", aspect_ratio="1:1", sample_count=4):
    """
    Generates an image using the Google Generative AI API (Imagen) via REST.
    
    Args:
        prompt (str): The text prompt for image generation.
        output_path (str): Base path to save the generated image(s).
                           Actual files will have suffix if multiple.
        api_key (str): Your Google API Key.
        model (str): The model to use (default: imagen-3.0-generate-001).
                     User requested: imagen-4.0-fast-generate-001
        aspect_ratio (str): Aspect ratio for the image (e.g., "1:1", "16:9", "9:16").
        sample_count (int): Number of images to generate (default 4).
    """
    
    # URL for the Generative Language API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "instances": [
            {
                "prompt": prompt
            }
        ],
        "parameters": {
            "sampleCount": sample_count,
            "aspectRatio": aspect_ratio
        }
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if 'predictions' in result and len(result['predictions']) > 0:
                generated_files = []
                
                for i, prediction in enumerate(result['predictions']):
                    b64_data = prediction.get('bytesBase64Encoded')
                    
                    if not b64_data:
                        continue

                    # Decode
                    image_data = base64.b64decode(b64_data)
                    
                    # Construct individual filename
                    # If only 1 image, maybe keep original name? 
                    # But consistency is good. Let's append index if sample_count > 1 or just always to be safe?
                    # The user wants 4 images.
                    
                    base, ext = os.path.splitext(output_path)
                    final_path = f"{base}_{i}{ext}"
                    
                    with open(final_path, 'wb') as f:
                        f.write(image_data)
                    
                    generated_files.append(final_path)
                    
                if generated_files:
                    return True, generated_files
                else:
                    return False, "Failed to decode any images from response."
            else:
                return False, f"No predictions returned. Response: {str(result)[:100]}..."
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"API Error: {e.code} - {error_body}")
        return False, f"HTTP Error {e.code}: {error_body}"
    except Exception as e:
        print(f"General Error: {e}")
        return False, f"Error: {str(e)}"
