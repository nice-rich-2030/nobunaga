import http.server
import socketserver
import json
import os
import shutil
import time
import sys
from urllib.parse import urlparse, parse_qs

# Import pygame for image generation
try:
    import pygame
    os.environ['SDL_VIDEODRIVER'] = 'dummy'  # Run headless if possible
    pygame.init()
    pygame.font.init()
except ImportError:
    print("Warning: pygame not found. Image generation will fail.")

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DIRECTORY)

# Load environment variables
def load_env():
    env_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(env_path):
        try:
            # Try utf-8-sig to handle BOM which is common on Windows
            encoding = 'utf-8-sig'
            try:
                with open(env_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                # Fallback to system default (often cp932 on Japanese Windows)
                with open(env_path, 'r', encoding='cp932') as f:
                    lines = f.readlines()

            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key:
                        os.environ[key] = value
        except Exception as e:
            print(f"Warning: Failed to load .env file: {e}")

load_env()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Debug prints for User
print("-" * 40)
print(f"Server Startup Debug Info:")
print(f"Current Directory: {os.getcwd()}")
print(f"Script Directory: {DIRECTORY}")
print(f"Project Root: {PROJECT_ROOT}")
env_path = os.path.join(PROJECT_ROOT, '.env')
print(f"Looking for .env at: {env_path}")
print(f".env exists: {os.path.exists(env_path)}")
if GOOGLE_API_KEY:
    print(f"GOOGLE_API_KEY status: LOADED (Length: {len(GOOGLE_API_KEY)})")
else:
    print(f"GOOGLE_API_KEY status: NOT LOADED")
print("-" * 40)

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            data = {
                "daimyo": [],
                "generals": [],
                "backgrounds": [
                    {"id": "main", "name": "メイン画面", "file": "main_background.png"},
                    {"id": "power_map", "name": "勢力図", "file": "power_map_background.png"},
                    {"id": "battle_vs", "name": "戦闘開始", "file": "battle_vs_background.png"},
                    {"id": "battle_combat", "name": "戦闘中", "file": "battle_combat_background.png"},
                    {"id": "battle_result", "name": "戦闘結果", "file": "battle_result_background.png"}
                ]
            }
            
            try:
                with open(os.path.join(PROJECT_ROOT, 'data', 'daimyo.json'), 'r', encoding='utf-8') as f:
                    data['daimyo'] = json.load(f).get('daimyo', [])
                with open(os.path.join(PROJECT_ROOT, 'data', 'generals.json'), 'r', encoding='utf-8') as f:
                    data['generals'] = json.load(f).get('generals', [])
            except Exception as e:
                print(f"Error loading data: {e}")

            self.wfile.write(json.dumps(data).encode())
            return

        elif parsed_path.path == '/api/images':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            test_dir = os.path.join(PROJECT_ROOT, 'assets-test')
            metadata_file = os.path.join(test_dir, 'metadata.json')
            metadata = []
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except:
                    metadata = []

            # Map filenames to metadata
            meta_map = {m['filename']: m for m in metadata}
            
            response_data = []
            if os.path.exists(test_dir):
                # Sort by modification time (newest first)
                files = [os.path.join(test_dir, f) for f in os.listdir(test_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                files.sort(key=os.path.getmtime, reverse=True)
                
                for f in files:
                    basename = os.path.basename(f)
                    meta = meta_map.get(basename, {})
                    response_data.append({
                        "filename": basename,
                        "prompt": meta.get('prompt', ''),
                        "target_name": meta.get('target_name', ''),
                        "category": meta.get('category', ''),
                        "target_id": meta.get('target_id', '')
                    })
            
            self.wfile.write(json.dumps(response_data).encode())
            return
            
        elif parsed_path.path.startswith('/assets-test/'):
            # Manual serving of assets-test images
            file_path = os.path.join(PROJECT_ROOT, self.path.lstrip('/'))
            if os.path.exists(file_path):
                self.send_response(200)
                if file_path.endswith('.png'):
                    self.send_header('Content-type', 'image/png')
                else:
                    self.send_header('Content-type', 'image/jpeg')
                self.end_headers()
                try:
                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())
                except Exception as e:
                    print(f"Error serving image: {e}")
                return

        return super().do_GET()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/select-image':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data)
            
            src_file = params.get('file')
            target_type = params.get('type') # daimyo, general, background
            target_id = params.get('id')
            
            src_path = os.path.join(PROJECT_ROOT, 'assets-test', src_file)
            
            if target_type == 'daimyo':
                dest_dir = os.path.join(PROJECT_ROOT, 'assets', 'portraits', 'daimyo')
                # Ensure filename format matches README requirements
                dest_name = f"daimyo_{int(target_id):02d}.png"
            elif target_type == 'general':
                dest_dir = os.path.join(PROJECT_ROOT, 'assets', 'portraits', 'generals')
                dest_name = f"general_{int(target_id):02d}.png"
            elif target_type == 'background':
                dest_dir = os.path.join(PROJECT_ROOT, 'assets', 'backgrounds')
                dest_name = target_id # already full filename e.g. 'main_background.png'
            else:
                self.send_error(400, "Invalid type")
                return

            if not os.path.exists(src_path):
                self.send_error(404, "Source file not found")
                return

            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, dest_name)
            
            try:
                shutil.copy2(src_path, dest_path)
                print(f"Reflected image to: {dest_path}")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "dest": dest_path}).encode())
            except Exception as e:
                self.send_error(500, str(e))
            return

        elif parsed_path.path == '/api/generate':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data)
            
            print(f"\n[GENERATION STARTED]")
            target_name = params.get('target_name', 'Unknown')
            category = params.get('category', 'unknown')
            prompt = params.get('prompt', '')
            size_str = params.get('size', '256x256')
            target_id = params.get('target_id', '0')
            
            # Parse size
            try:
                width, height = map(int, size_str.lower().split('x'))
            except:
                width, height = 256, 256
            
            print(f"Target: {target_name} ({category})")
            print(f"Prompt: {prompt}")
            print(f"Size: {width}x{height}")
            
            # --- Image Generation Logic ---
            success = False
            filename = ""
            message = ""
            
            # 1. Try AI Generation if API Key is available
            if GOOGLE_API_KEY:
                print(f"Using AI API (Model: imagen-4.0-fast-generate-001)...")
                
                # Determine Aspect Ratio
                aspect_ratio = "1:1"
                if category == 'background':
                    aspect_ratio = "16:9"
                
                # Prepare filename
                timestamp = int(time.time())
                filename = f"gen_{timestamp}_{category}_{params.get('target_id', '0')}_ai.png"
                filepath = os.path.join(PROJECT_ROOT, 'assets-test', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # Call API
                try:
                    import ai_generator
                    success, result = ai_generator.generate_image_from_api(
                        prompt=prompt,
                        output_path=filepath,
                        api_key=GOOGLE_API_KEY,
                        model="imagen-4.0-fast-generate-001",
                        aspect_ratio=aspect_ratio,
                        sample_count=4
                    )
                    
                    if success:
                        # Result is a list of file paths
                        print(f"AI Generation Successful. Generated {len(result)} images.")
                        message = f"AI Image generated successfully ({len(result)} images)"
                        
                        # Save Metadata for ALL generated images
                        metadata_file = os.path.join(PROJECT_ROOT, 'assets-test', 'metadata.json')
                        metadata = []
                        if os.path.exists(metadata_file):
                            try:
                                with open(metadata_file, 'r', encoding='utf-8') as f:
                                    metadata = json.load(f)
                            except:
                                metadata = []
                        
                        # Add entries
                        for img_path in result:
                            # Parse parts for display if needed or just use current params
                            img_filename = os.path.basename(img_path)
                            meta_entry = {
                                "filename": img_filename,
                                "prompt": prompt,
                                "target_name": target_name,
                                "category": category,
                                "target_id": params.get('target_id', '0'), # Use raw param
                                "timestamp": timestamp
                            }
                            metadata.append(meta_entry)
                        
                        # Write back
                        with open(metadata_file, 'w', encoding='utf-8') as f:
                            json.dump(metadata, f, ensure_ascii=False, indent=2)

                        # Response (Return the first one as representative)
                        filename = os.path.basename(result[0])
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "status": "success", 
                            "message": message,
                            "file": filename
                        }).encode())
                        return

                    else:
                        print(f"AI Generation Failed: {result}")
                        print("Falling back to local pygame generation...")
                except Exception as e:
                    print(f"AI Module Error: {e}")
                    # traceback.print_exc()
                    print("Falling back to local pygame generation...")

            # 2. Fallback to Pygame Generation (Local Mock)
            if not success:
                try:
                    # Create surface
                    surf = pygame.Surface((width, height))
                    
                    # Dynamic background color based on category
                    if category == 'daimyo':
                        bg_color = (220, 200, 160) # Gold-ish
                    elif category == 'general':
                        bg_color = (200, 200, 220) # Blue-ish
                    elif category == 'background':
                        bg_color = (40, 30, 20)    # Dark
                    else:
                        bg_color = (100, 100, 100)
                    
                    surf.fill(bg_color)
                    
                    # Draw visual elements
                    # 1. Border
                    border_rect = pygame.Rect(4, 4, width-8, height-8)
                    pygame.draw.rect(surf, (50, 50, 50), border_rect, 2)
                    
                    # 2. Text (Target info)
                    font_size = 24 if width > 500 else 18
                    try:
                        font = pygame.font.SysFont("mspgothic", font_size) # Try Japanese font
                    except:
                        font = pygame.font.SysFont(None, font_size)
                    
                    # Render text Helper
                    def render_text_centered(text, y_pos, color=(20, 20, 20)):
                        text_surf = font.render(text, True, color)
                        text_rect = text_surf.get_rect(center=(width//2, y_pos))
                        surf.blit(text_surf, text_rect)

                    # Draw Info
                    render_text_centered(f"[{category.upper()}]", 30)
                    render_text_centered(target_name, 60, (0, 0, 0))
                    
                    # Draw Prompt (Word wrap simplistic)
                    prompt_y = 100
                    prompt_font_size = 16
                    try:
                        p_font = pygame.font.SysFont("meiryo", prompt_font_size)
                    except:
                        p_font = pygame.font.SysFont(None, prompt_font_size)
                    
                    # Simple wrapping for display
                    words = prompt.split()
                    line = ""
                    for word in words:
                        test_line = line + word + " "
                        if p_font.size(test_line)[0] < width - 20:
                            line = test_line
                        else:
                            text_s = p_font.render(line, True, (60, 60, 80))
                            surf.blit(text_s, (10, prompt_y))
                            prompt_y += 20
                            line = word + " "
                    if line:
                        text_s = p_font.render(line, True, (60, 60, 80))
                        surf.blit(text_s, (10, prompt_y))
                        
                    # 3. Add a visual indicator that this is "Generated"
                    gen_label = p_font.render("AI GENERATED (PREVIEW)", True, (200, 50, 50))
                    surf.blit(gen_label, (10, height - 25))

                    # Save
                    test_dir = os.path.join(PROJECT_ROOT, 'assets-test')
                    os.makedirs(test_dir, exist_ok=True)
                    
                    timestamp = int(time.time())
                    filename = f"gen_{timestamp}_{category}_{target_id}.png"
                    filepath = os.path.join(test_dir, filename)
                    
                    pygame.image.save(surf, filepath)
                    print(f"Saved to: {filepath}")
                    
                    success = True
                    message = "Image generated successfully (Local Preview)"
                    
                except Exception as e:
                    print(f"Generation error: {e}")
                    import traceback
                    traceback.print_exc()
                    self.send_error(500, f"Generation failed: {str(e)}")
                    return

            if success:
                # Save Metadata
                meta_entry = {
                    "filename": filename,
                    "prompt": prompt,
                    "target_name": target_name,
                    "category": category,
                    "target_id": target_id,
                    "timestamp": timestamp
                }
                
                metadata_file = os.path.join(PROJECT_ROOT, 'assets-test', 'metadata.json')
                metadata = []
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except:
                        metadata = []
                
                metadata.append(meta_entry)
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success", 
                    "message": message,
                    "file": filename
                }).encode())
            return

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()
