import re
import argparse
import random
import os
import xml.etree.ElementTree as ET
from PIL import Image

def random_color():
    """Generates a random RGB color string."""
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return f"rgb({r},{g},{b})"

def parse_ini_file(filepath, mapped_images):
    """Parses a single INI file and updates the mapped_images dict."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading INI {filepath}: {e}")
        return

    current_image = None
    
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith(';'):
            continue
            
        if line.lower().startswith('mappedimage'):
            parts = line.split()
            if len(parts) >= 2:
                image_name = parts[1]
                current_image = {'name': image_name}
        elif line.lower() == 'end':
            if current_image:
                mapped_images[current_image['name']] = current_image
                current_image = None
        elif current_image:
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'texture':
                    current_image['texture'] = value
                elif key == 'texturewidth':
                    current_image['width'] = int(value)
                elif key == 'textureheight':
                    current_image['height'] = int(value)
                elif key == 'coords':
                    coords = {}
                    parts = value.split()
                    for part in parts:
                        if ':' in part:
                            k, v = part.split(':')
                            try:
                                coords[k] = int(v)
                            except ValueError:
                                # Silently ignore or print debug if needed, but don't crash
                                pass
                    current_image['coords'] = coords

def scan_mapped_images(root_dir):
    """Recursively scans for INI files and parses MappedImage definitions."""
    mapped_images = {}
    if not os.path.exists(root_dir):
        print(f"Warning: MappedImages directory {root_dir} not found.")
        return mapped_images

    print(f"Scanning for INI files in {root_dir}...")
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.ini'):
                parse_ini_file(os.path.join(root, file), mapped_images)
    
    print(f"Loaded {len(mapped_images)} mapped images.")
    return mapped_images

def scan_textures(root_dir):
    """Recursively scans for textures and returns a map of lowercased-name -> path."""
    texture_map = {}
    if not os.path.exists(root_dir):
        print(f"Warning: Textures directory {root_dir} not found.")
        # Fallback to current directory for loose files if Art/Textures implies strictness?
        # User said "The actual images... should be searched within the "Art/Textures" project folder".
        # I'll stick to that, but maybe add current dir as fallback if user has loose files.
        # Let's strictly follow "recursive search within Art/Textures".
        return texture_map

    print(f"Scanning for textures in {root_dir}...")
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            texture_map[file.lower()] = os.path.join(root, file)
            
    print(f"Found {len(texture_map)} textures.")
    return texture_map

def extract_and_save_image(image_info, output_dir, texture_map):
    """Crops and saves the image."""
    texture_name = image_info['texture']
    
    # Try to find the texture in our map
    texture_path = texture_map.get(texture_name.lower())
    
    if not texture_path:
        # Fallback: sometimes extension might differ (tga vs png vs dds)
        base, ext = os.path.splitext(texture_name)
        # Try .png if .tga demanded
        texture_path = texture_map.get((base + ".png").lower())
        
    if not texture_path:
        # Try .dds
        texture_path = texture_map.get((base + ".dds").lower())
        
    if not texture_path:
        # Final check: Maybe it's in the current directory (legacy support for single file runs)
        if os.path.exists(texture_name):
            texture_path = texture_name
        elif os.path.exists(base + ".png"):
            texture_path = base + ".png"
        elif os.path.exists(base + ".dds"):
            texture_path = base + ".dds"

    if not texture_path:
        print(f"Texture not found: {texture_name}")
        return None

    try:
        img = Image.open(texture_path)
    except Exception as e:
        print(f"Error opening {texture_path}: {e}")
        return None
        
    ini_width = image_info.get('width', img.width)
    actual_width = img.width
    scale = actual_width / ini_width if ini_width > 0 else 1.0
    
    coords = image_info['coords']
    left = int(coords['Left'] * scale)
    top = int(coords['Top'] * scale)
    right = int(coords['Right'] * scale)
    bottom = int(coords['Bottom'] * scale)
    
    if left >= right or top >= bottom:
         return None

    cropped = img.crop((left, top, right, bottom))
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_filename = f"{image_info['name']}.png"
    output_path = os.path.join(output_dir, output_filename)
    cropped.save(output_path)
    return output_path

def parse_wnd_and_generate_svg(wnd_path, mapped_images_dir, textures_dir, output_dir):
    if not os.path.exists(wnd_path):
        print(f"Error: File {wnd_path} not found.")
        return

    # Scan resources
    mapped_images = scan_mapped_images(mapped_images_dir)
    texture_map = scan_textures(textures_dir)
    
    with open(wnd_path, 'r') as f:
        content = f.read()

    # Find Creation Resolution (First one)
    res_match = re.search(r"CREATIONRESOLUTION:\s*(\d+)\s+(\d+)", content)
    if res_match:
        width = int(res_match.group(1))
        height = int(res_match.group(2))
    else:
        print("Warning: CREATIONRESOLUTION not found, defaulting to 800x600.")
        width = 800
        height = 600

    windows = []
    
    blocks = content.split("WINDOW")
    
    for block in blocks:
        block = block.strip()
        if not block: continue
        
        # Check if this block has SCREENRECT and NAME
        rect_match = re.search(r"SCREENRECT\s*=\s*UPPERLEFT:\s*(\d+)\s+(\d+),\s*BOTTOMRIGHT:\s*(\d+)\s+(\d+)", block, re.DOTALL)
        name_match = re.search(r"NAME\s*=\s*\"([^\"]+)\"", block)
        
        if rect_match and name_match:
            x1 = int(rect_match.group(1))
            y1 = int(rect_match.group(2))
            x2 = int(rect_match.group(3))
            y2 = int(rect_match.group(4))
            name = name_match.group(1)
            
            rect_width = x2 - x1
            rect_height = y2 - y1
            
            window = {
                'name': name,
                'x': x1,
                'y': y1,
                'width': rect_width,
                'height': rect_height,
                'images': []
            }
            
            # Find ENABLEDDRAWDATA
            draw_data_match = re.search(r"ENABLEDDRAWDATA\s*=\s*(.*?);", block, re.DOTALL)
            if draw_data_match:
                draw_str = draw_data_match.group(1)
                items = draw_str.split(',')
                for item in items:
                    item = item.strip()
                    img_match = re.search(r"IMAGE:\s*(\w+)", item)
                    if img_match:
                        img_name = img_match.group(1)
                        if img_name != "NoImage":
                            window['images'].append(img_name)
                            
            windows.append(window)

    print(f"Found {len(windows)} windows.")

    # Generate SVG
    svg_lines = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '  <style>',
        '    rect { stroke: none; fill-opacity: 0.25; }',
        '    text { font-family: Arial, sans-serif; font-size: 10px; fill: black; text-anchor: middle; dominant-baseline: middle; pointer-events: none; }',
        '  </style>'
    ]

    for win in windows:
        color = random_color()
        svg_lines.append(f'  <g id="{win["name"]}">')
        svg_lines.append(f'    <rect x="{win["x"]}" y="{win["y"]}" width="{win["width"]}" height="{win["height"]}" fill="{color}" />')
        
        # Add Images
        for img_name in win['images']:
            if img_name in mapped_images:
                saved_path = extract_and_save_image(mapped_images[img_name], output_dir, texture_map)
                if saved_path:
                    # Convert to forward slashes for SVG
                    rel_path = saved_path.replace('\\', '/')
                    svg_lines.append(f'    <image href="{rel_path}" x="{win["x"]}" y="{win["y"]}" width="{win["width"]}" height="{win["height"]}" />')
            else:
                pass 
                # print(f"Warning: Mapped image {img_name} not found in INI.")
                
        svg_lines.append('  </g>')

    svg_lines.append('</svg>')
    
    output_filename = os.path.splitext(os.path.basename(wnd_path))[0] + ".svg"
    with open(output_filename, 'w') as f:
        f.write('\n'.join(svg_lines))
        
    print(f"Saved SVG to {output_filename}")

def update_wnd_from_svg(wnd_path, svg_path, output_path):
    """Updates the WND file using coordinates from the SVG."""
    if not os.path.exists(wnd_path):
        print(f"Error: WND file {wnd_path} not found.")
        return
    if not os.path.exists(svg_path):
        print(f"Error: SVG file {svg_path} not found.")
        return
        
    # Parse SVG
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        # Namespace handling
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
                
        # Get global resolution from SVG root
        svg_width = root.get('width')
        svg_height = root.get('height')
        
    except Exception as e:
        print(f"Error parsing SVG: {e}")
        return

    updates = {} # Name -> {x, y, w, h}
    
    # We look for groups <g id="..."> which contain <rect ...>
    # The ID is the Window Name
    for group in root.findall(".//g"):
        group_id = group.get('id')
        if not group_id: continue
        
        # Find the rect inside
        rect = group.find("rect")
        if rect is not None:
             try:
                x = float(rect.get('x'))
                y = float(rect.get('y'))
                w = float(rect.get('width'))
                h = float(rect.get('height'))
                updates[group_id] = {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
             except ValueError:
                 continue

    print(f"Found {len(updates)} updates from SVG.")
    
    # Process WND file
    with open(wnd_path, 'r') as f:
        lines = f.readlines()
        
    new_lines = []
    buffer = []
    
    # Map to track occurrences of ambiguous names
    # Key: NAME string (including the :), Value: integer count
    from collections import defaultdict
    ambiguous_counters = defaultdict(int)

    def process_block(block_lines):
        if not block_lines:
            return []
            
        block_str = "".join(block_lines)
        
        # 1. Update CREATIONRESOLUTION if present
        if svg_width and svg_height:
            res_pattern = r"(CREATIONRESOLUTION:\s*)(\d+)(\s+)(\d+)"
            block_str = re.sub(res_pattern, f"\\g<1>{svg_width}\\g<3>{svg_height}", block_str)
            
        # 2. Update SCREENRECT if we have a matching NAME
        name_match = re.search(r"NAME\s*=\s*\"([^\"]+)\"", block_str)
        if name_match:
            name = name_match.group(1)
            
            # Determine which ID to look up
            update_id = name
            
            # Check if ambiguous (ends in :)
            if name.endswith(':'):
                ambiguous_counters[name] += 1
                count = ambiguous_counters[name]
                # Construct fallback ID: NameAutoLabel_Count
                fallback_id = f"{name}AutoLabel_{count}"
                
                # If the exact name isn't in updates, but the fallback is, use fallback
                if name not in updates and fallback_id in updates:
                    update_id = fallback_id
            
            if update_id in updates:
                u = updates[update_id]
                new_x2 = u['x'] + u['w']
                new_y2 = u['y'] + u['h']
                
                rect_pattern = r"(SCREENRECT\s*=\s*UPPERLEFT:\s*)(\d+)(\s+)(\d+)((?:,\s*|\s+)BOTTOMRIGHT:\s*)(\d+)(\s+)(\d+)"
                
                def replace_coords(m):
                    return f"{m.group(1)}{u['x']}{m.group(3)}{u['y']}{m.group(5)}{new_x2}{m.group(7)}{new_y2}"
                
                block_str = re.sub(rect_pattern, replace_coords, block_str, flags=re.DOTALL)
        
        # Convert back to lines
        import io
        return io.StringIO(block_str).readlines()

    for line in lines:
        stripped = line.strip()
        
        # Start of a new block triggers processing of the previous buffer
        if stripped == "WINDOW" or stripped == "CHILD": 
            new_lines.extend(process_block(buffer))
            buffer = []
            
        buffer.append(line)
        
    # Process final buffer
    new_lines.extend(process_block(buffer))
    
    with open(output_path, 'w') as f:
        f.writelines(new_lines)
    print(f"Saved updated WND to {output_path}")

def preprocess_wnd_if_needed(wnd_path):
    """
    Checks for ambiguous window names (ending in :) and creates a labeled copy if found.
    """
    if not os.path.exists(wnd_path):
        return wnd_path

    with open(wnd_path, 'r') as f:
        content = f.read()

    # Fast detection
    # Look for NAME = "Something:" with nothing after the colon inside the quotes
    # Regex: NAME\s*=\s*"[^"]+:"
    if not re.search(r'NAME\s*=\s*"[^"]+:"', content):
        return wnd_path

    print(f"Detected ambiguous window names in {wnd_path}. Pre-processing...")

    new_lines = []
    lines = content.splitlines()
    
    # Counter for uniqueness
    # We'll stick to a simple global counter or per-file-prefix counter?
    # Simple global counter appended to the name is safest.
    # Format: "OriginalName:AutoLabel_1"
    
    counter = 1
    
    for line in lines:
        # Capture optional leading whitespace
        match = re.search(r'^(\s*NAME\s*=\s*")([^"]+:)"', line)
        if match:
            # group 1: whitespace + NAME = "
            # group 2: name content ending in :
            prefix = match.group(1)
            name_content = match.group(2)
            
            # Append label
            new_line = f'{prefix}{name_content}AutoLabel_{counter}";'
            new_lines.append(new_line)
            counter += 1
        else:
            new_lines.append(line)
            
    base_name = os.path.splitext(wnd_path)[0]
    new_path = f"{base_name}_labeled.wnd"
    
    with open(new_path, 'w') as f:
        f.write('\n'.join(new_lines))
        
    print(f"Warning: Ambiguous window names found. Created pre-processed file: {new_path}")
    return new_path

def main():
    parser = argparse.ArgumentParser(description="Convert .wnd file to SVG.")
    parser.add_argument("wnd_file", help="Path to the .wnd file")
    # Updated arguments
    parser.add_argument("--mapped_images_dir", default="MappedImages", help="Folder containing INI files with Mapped Images")
    parser.add_argument("--textures_dir", default="Art/Textures", help="Folder containing textures")
    parser.add_argument("--outdir", default="extracted_images", help="Directory to save extracted images")
    parser.add_argument("--update", action="store_true", help="Update WND file from SVG")
    parser.add_argument("--updatenew", action="store_true", help="Update WND file from SVG and save as [basename]_NEW.wnd")
    parser.add_argument("--svg", help="SVG file to read updates from (required if --update)")
    parser.add_argument("--output", help="Output WND file (default: overwrite input)")
    args = parser.parse_args()
    
    if args.updatenew:
        args.update = True
        if not args.output:
            args.output = os.path.splitext(args.wnd_file)[0] + "_NEW.wnd"
    
    if args.update:
        if not args.svg:
            base = os.path.splitext(args.wnd_file)[0]
            args.svg = base + ".svg"
            if not os.path.exists(args.svg):
                print("Error: --svg required for update mode.")
                return
        
        output = args.output if args.output else args.wnd_file
        update_wnd_from_svg(args.wnd_file, args.svg, output)
    else:
        # Pre-process for generation only
        wnd_to_process = preprocess_wnd_if_needed(args.wnd_file)
        parse_wnd_and_generate_svg(wnd_to_process, args.mapped_images_dir, args.textures_dir, args.outdir)

if __name__ == "__main__":
    main()
