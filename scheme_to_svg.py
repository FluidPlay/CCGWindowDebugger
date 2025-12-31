import re
import os
import random
import argparse
import xml.etree.ElementTree as ET
from PIL import Image

def parse_ini(filepath):
    """Parses an INI file for MappedImage definitions."""
    mapped_images = {}
    if not os.path.exists(filepath):
        print(f"Warning: File {filepath} not found.")
        return mapped_images

    with open(filepath, 'r') as f:
        content = f.read()

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
                
                try:
                    if key == 'texture':
                        current_image['texture'] = value
                    elif key == 'texturewidth':
                        if value:
                            current_image['width'] = int(value)
                    elif key == 'textureheight':
                        if value:
                            current_image['height'] = int(value)
                    elif key == 'coords':
                        coords = {}
                        parts = value.split()
                        for part in parts:
                            if ':' in part:
                                k, v = part.split(':')
                                if v:
                                    coords[k] = int(v)
                        current_image['coords'] = coords
                except ValueError as e:
                    print(f"Warning: Error parsing line '{line}': {e}")

    return mapped_images

def parse_control_scheme(filepath, section_name):
    """Parses a specific ControlBarScheme section from the INI file."""
    base_image = None
    
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found.")
        return [], {}, {'x': 800, 'y': 600}

    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    button_mappings = {} # ButtonName -> {State: ImageName}
    button_positions = {} # ButtonName -> {UL: (x,y), LR: (x,y)}
    
    in_target_section = False
    in_image_part = False
    
    # Parse ScreenCreationRes
    screen_res = {'x': 800, 'y': 600} # Default

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith(';'):
            continue
            
        # Check for Section Start
        if stripped_line.lower().startswith('controlbarscheme'):
            parts = stripped_line.split()
            if len(parts) >= 2:
                current_scheme = parts[1]
                if current_scheme.lower() == section_name.lower():
                    in_target_section = True
                    print(f"Found section: {current_scheme}")
                    continue
                else:
                    in_target_section = False
        
        if not in_target_section:
            continue

        # Check for Section End
        if stripped_line.lower() == 'end' and not in_image_part:
            in_target_section = False
            break # We found and parsed our section, we are done
            
        if stripped_line.startswith('ScreenCreationRes'):
             match = re.search(r"X:(\d+)\s+Y:(\d+)", stripped_line)
             if match:
                 screen_res['x'] = int(match.group(1))
                 screen_res['y'] = int(match.group(2))

        # Parse Button Mappings
        # Look for *Button*
        if 'Button' in stripped_line and len(stripped_line.split()) >= 2:
            parts = stripped_line.split()
            key_part = parts[0]
            image_name = parts[1]
            
            # Split key_part into ButtonName and State
            if 'Button' in key_part:
                name, state = key_part.split('Button', 1)
                
                # Handle aliases/inconsistencies
                if name == 'IdleWorker':
                    name = 'Worker'
                elif name == 'Buddy':
                    name = 'Chat'
                
                if name not in button_mappings:
                    button_mappings[name] = {}
                button_mappings[name][state] = image_name
                
        # Parse Positions
        if stripped_line.endswith('UL') or 'UL ' in stripped_line:
             match = re.search(r"(\w+)UL\s+X:(\d+)\s+Y:(\d+)", stripped_line)
             if match:
                 name = match.group(1)
                 if name not in button_positions: button_positions[name] = {}
                 button_positions[name]['UL'] = (int(match.group(2)), int(match.group(3)))

        if stripped_line.endswith('LR') or 'LR ' in stripped_line:
             match = re.search(r"(\w+)LR\s+X:(\d+)\s+Y:(\d+)", stripped_line)
             if match:
                 name = match.group(1)
                 if name not in button_positions: button_positions[name] = {}
                 button_positions[name]['LR'] = (int(match.group(2)), int(match.group(3)))

        # Parse Base Image
        if stripped_line == 'ImagePart':
            in_image_part = True
            base_image = {}
        elif stripped_line == 'End' and in_image_part:
            in_image_part = False
        elif in_image_part:
            if stripped_line.startswith('Position'):
                match = re.search(r"X:(\d+)\s+Y:(\d+)", stripped_line)
                if match:
                    base_image['x'] = int(match.group(1))
                    base_image['y'] = int(match.group(2))
            elif stripped_line.startswith('Size'):
                match = re.search(r"X:(\d+)\s+Y:(\d+)", stripped_line)
                if match:
                    base_image['width'] = int(match.group(1))
                    base_image['height'] = int(match.group(2))
            elif stripped_line.startswith('ImageName'):
                parts = stripped_line.split()
                if len(parts) > 1:
                    base_image['name'] = parts[1]
                
    # Combine mappings and positions
    # We want ALL positions, even if they don't have button mappings
    final_rects = []
    for name, pos in button_positions.items():
        if 'UL' in pos and 'LR' in pos:
            rect_info = {
                'name': name,
                'x': pos['UL'][0],
                'y': pos['UL'][1],
                'width': pos['LR'][0] - pos['UL'][0],
                'height': pos['LR'][1] - pos['UL'][1],
                'states': button_mappings.get(name, {}) # Empty dict if no mappings
            }
            final_rects.append(rect_info)
            
    return final_rects, base_image, screen_res

def extract_and_save_image(image_info, output_dir):
    """Crops and saves the image."""
    texture_file = image_info['texture']
    
    # helper to find file with fallbacks
    def find_texture_path(path):
        candidates = [
            path,
            path.lower(),
            os.path.join("Art", "Textures", path),
            os.path.join("Art", "Textures", path).lower(),
            os.path.join("Art", "Textures", os.path.basename(path)),
            os.path.join("Art", "Textures", os.path.basename(path)).lower(),
        ]
        
        # Add .png and .dds fallback for .tga
        root, ext = os.path.splitext(path)
        if ext.lower() == '.tga':
            # Try PNG
            png_path = root + '.png'
            candidates.extend([
                png_path,
                png_path.lower(),
                os.path.join("Art", "Textures", png_path),
                os.path.join("Art", "Textures", png_path).lower(),
                os.path.join("Art", "Textures", os.path.basename(png_path)),
                os.path.join("Art", "Textures", os.path.basename(png_path)).lower(),
            ])
            # Try DDS
            dds_path = root + '.dds'
            candidates.extend([
                dds_path,
                dds_path.lower(),
                os.path.join("Art", "Textures", dds_path),
                os.path.join("Art", "Textures", dds_path).lower(),
                os.path.join("Art", "Textures", os.path.basename(dds_path)),
                os.path.join("Art", "Textures", os.path.basename(dds_path)).lower(),
            ])
            
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    found_file = find_texture_path(texture_file)
    
    # Specific hardcoded fallbacks if general search failed
    if not found_file:
        if 'sacommandbar' in texture_file.lower() and os.path.exists('sacommandbar.png'):
            found_file = 'sacommandbar.png'
        elif 'sacontrolbar512_001' in texture_file.lower() and os.path.exists('sacontrolbar512_001.tga'):
            found_file = 'sacontrolbar512_001.tga'

    if found_file:
        texture_file = found_file
    else:
        print(f"Error: Texture file {texture_file} not found for {image_info['name']}")
        return None

    try:
        img = Image.open(texture_file)
    except Exception as e:
        print(f"Error opening {texture_file}: {e}")
        return None
        
    ini_width = image_info['width']
    actual_width = img.width
    scale = actual_width / ini_width
    
    coords = image_info['coords']
    left = int(coords['Left'] * scale)
    top = int(coords['Top'] * scale)
    right = int(coords['Right'] * scale)
    bottom = int(coords['Bottom'] * scale)
    
    cropped = img.crop((left, top, right, bottom))
    
    output_filename = f"{image_info['name']}.png"
    output_path = os.path.join(output_dir, output_filename)
    cropped.save(output_path)
    return output_path

import colorsys

def random_color():
    """Generates a random RGB color string with high saturation (>= 70%)."""
    h = random.random()
    s = random.uniform(0.7, 1.0) # Saturation at least 70%
    l = random.uniform(0.4, 0.6) # Lightness around 50% for good visibility
    
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    
    return f"rgb({int(r*255)},{int(g*255)},{int(b*255)})"

def generate_svg(rects, base_image_info, mapped_images, output_dir, output_file, screen_res):
    """Generates the SVG file."""
    width = screen_res.get('x', 800)
    height = screen_res.get('y', 600)
    
    svg_lines = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '  <style>',
        '    text { font-family: Arial, sans-serif; font-size: 10px; fill: lightgray; text-anchor: middle; dominant-baseline: middle; pointer-events: none; }',
        '    rect { stroke: none; pointer-events: all; }',
        '  </style>'
    ]
    
    # Add Base Image
    if base_image_info:
        name = base_image_info.get('name')
        if name and name in mapped_images:
            print(f"Processing Base Image: {name}")
            saved_path = extract_and_save_image(mapped_images[name], output_dir)
            if saved_path:
                rel_path = saved_path.replace('\\', '/')
                # Use ImagePart Position for the image placement
                svg_lines.append(f'  <image href="{rel_path}" x="{base_image_info["x"]}" y="{base_image_info["y"]}" />')
        else:
            print(f"Warning: Base image {name} not found in mapped images or name is missing.")
            
        # Draw ImagePart Rect
        if 'width' in base_image_info and 'height' in base_image_info:
             svg_lines.append(f'  <g id="ImagePart">')
             svg_lines.append(f'    <rect id="ImagePart_rect" x="{base_image_info["x"]}" y="{base_image_info["y"]}" width="{base_image_info["width"]}" height="{base_image_info["height"]}" fill="rgb(128,128,128)" fill-opacity="0.15" />')
             center_x = base_image_info["x"] + base_image_info["width"] / 2
             center_y = base_image_info["y"] + base_image_info["height"] / 2
             svg_lines.append(f'    <text x="{center_x}" y="{center_y}" fill="red">ImagePart</text>')
             svg_lines.append(f'  </g>')

    # Add Rects (and their buttons if any)
    for rect in rects:
        print(f"Processing Rect: {rect['name']}")
        svg_lines.append(f'  <g id="{rect["name"]}">')
        
        # Process all states for associated buttons
        states = rect['states']
        if states:
            sorted_states = sorted(states.keys(), key=lambda s: 1 if s == 'Enable' else 0)
            
            for state in sorted_states:
                image_name = states[state]
                if image_name in mapped_images:
                    saved_path = extract_and_save_image(mapped_images[image_name], output_dir)
                    if saved_path:
                        rel_path = saved_path.replace('\\', '/')
                        visibility = 'visible' if state == 'Enable' else 'hidden'
                        svg_lines.append(f'    <image id="{rect["name"]}_{state}" href="{rel_path}" x="{rect["x"]}" y="{rect["y"]}" visibility="{visibility}" />')
                else:
                    print(f"Warning: Image {image_name} for button {rect['name']} state {state} not found.")
        else:
            # Orphan Rect - Add Label
            center_x = rect['x'] + rect['width'] / 2
            center_y = rect['y'] + rect['height'] / 2
            svg_lines.append(f'    <text x="{center_x}" y="{center_y}">{rect["name"]}</text>')

        # Add Rect on top with random color
        color = random_color()
        svg_lines.append(f'    <rect id="{rect["name"]}_rect" x="{rect["x"]}" y="{rect["y"]}" width="{rect["width"]}" height="{rect["height"]}" fill="{color}" fill-opacity="0.25" />')
        svg_lines.append('  </g>')
            
    svg_lines.append('</svg>')
    
    with open(output_file, "w") as f:
        f.write('\n'.join(svg_lines))
        
    print(f"Done. Saved {output_file}")

def update_control_scheme_from_svg(svg_path, scheme_path, section_name, output_path=None):
    """Updates the ControlBarScheme section in the INI file based on SVG rect coordinates."""
    if not os.path.exists(svg_path):
        print(f"Error: SVG file {svg_path} not found.")
        return
        
    if not os.path.exists(scheme_path):
        print(f"Error: Scheme file {scheme_path} not found.")
        return

    # Parse SVG
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        # Strip namespaces
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
    except Exception as e:
        print(f"Error parsing SVG: {e}")
        return

    # Find all rects with id ending in _rect
    updated_coords = {} # Name -> {UL: (x,y), LR: (x,y)}
    
    # Get SVG dimensions for ScreenCreationRes
    svg_width = root.get('width')
    svg_height = root.get('height')
    
    # Fallback to viewBox if width/height missing
    if not svg_width or not svg_height:
        viewbox = root.get('viewBox')
        if viewbox:
            vb_parts = viewbox.split()
            if len(vb_parts) == 4:
                svg_width = vb_parts[2]
                svg_height = vb_parts[3]

    # Default if still missing
    if not svg_width: svg_width = '800'
    if not svg_height: svg_height = '600'

    # Remove 'px' if present
    if svg_width.endswith('px'): svg_width = svg_width[:-2]
    if svg_height.endswith('px'): svg_height = svg_height[:-2]
    
    for rect in root.findall(".//rect"):
        rect_id = rect.get('id')
        if rect_id and rect_id.endswith('_rect'):
            name = rect_id.replace('_rect', '')
            x = float(rect.get('x'))
            y = float(rect.get('y'))
            width = float(rect.get('width'))
            height = float(rect.get('height'))
            
            ul = (int(x), int(y))
            lr = (int(x + width), int(y + height))
            updated_coords[name] = {'UL': ul, 'LR': lr, 'w': int(width), 'h': int(height)}
            
    print(f"Found {len(updated_coords)} rects in SVG to update.")
    
    # Read Scheme File
    with open(scheme_path, 'r') as f:
        lines = f.readlines()
        
    new_lines = []
    in_target_section = False
    in_image_part = False
    
    for line in lines:
        original_line = line
        stripped_line = line.strip()
        
        # Identify Section
        if stripped_line.lower().startswith('controlbarscheme'):
            parts = stripped_line.split()
            if len(parts) >= 2:
                current_scheme = parts[1]
                if current_scheme.lower() == section_name.lower():
                    in_target_section = True
                    print(f"Updating section: {current_scheme}")
                else:
                    in_target_section = False
        
        if not in_target_section:
            new_lines.append(original_line)
            continue
            
        # We are inside the target section
        
        # Check for End of Main Section (not nested End)
        if stripped_line.lower() == 'end' and not in_image_part:
            in_target_section = False
            new_lines.append(original_line)
            continue
            
        if stripped_line.lower() == 'imagepart':
            in_image_part = True
            new_lines.append(original_line)
            continue
        elif stripped_line.lower() == 'end' and in_image_part:
            in_image_part = False
            new_lines.append(original_line)
            continue

        if stripped_line.startswith('ScreenCreationRes'):
             # Preserve indentation if any (though usually top level)
             indent = original_line[:original_line.find('ScreenCreationRes')]
             new_lines.append(f"{indent}ScreenCreationRes X:{int(float(svg_width))} Y:{int(float(svg_height))}\n")
             continue
            
        if in_image_part and 'ImagePart' in updated_coords:
            img_part_data = updated_coords['ImagePart']
            if stripped_line.startswith('Position'):
                 match = re.search(r"X:(\d+)\s+Y:(\d+)", stripped_line)
                 if match:
                      # keep indentation
                      indent = original_line[:original_line.find('Position')]
                      new_lines.append(f"{indent}Position X:{img_part_data['UL'][0]} Y:{img_part_data['UL'][1]}\n")
                 else:
                      new_lines.append(original_line)
                 continue
            elif stripped_line.startswith('Size'):
                 match = re.search(r"X:(\d+)\s+Y:(\d+)", stripped_line)
                 if match:
                      indent = original_line[:original_line.find('Size')]
                      new_lines.append(f"{indent}Size X:{img_part_data['w']} Y:{img_part_data['h']}\n")
                 else:
                      new_lines.append(original_line)
                 continue

        # Check for UL/LR lines
        ul_match = re.search(r"(\w+)UL\s+X:(\d+)\s+Y:(\d+)", stripped_line)
        if ul_match:
            name = ul_match.group(1)
            if name in updated_coords:
                new_ul = updated_coords[name]['UL']
                # Preserve indentation
                indent = original_line[:original_line.find(name)]
                new_lines.append(f"{indent}{name}UL X:{new_ul[0]} Y:{new_ul[1]}\n")
                continue
                
        lr_match = re.search(r"(\w+)LR\s+X:(\d+)\s+Y:(\d+)", stripped_line)
        if lr_match:
            name = lr_match.group(1)
            if name in updated_coords:
                new_lr = updated_coords[name]['LR']
                indent = original_line[:original_line.find(name)]
                new_lines.append(f"{indent}{name}LR X:{new_lr[0]} Y:{new_lr[1]}\n")
                continue
                
        new_lines.append(original_line)
        
    # Save Updated File
    if output_path is None:
        base, ext = os.path.splitext(scheme_path)
        output_path = f"{base}-updated{ext}"
    
    with open(output_path, 'w') as f:
        f.writelines(new_lines)
        
    print(f"Saved updated scheme to {output_path}")

def load_all_mapped_images(root_dirs):
    """Recursively loads all MappedImages from INI files in the given directories."""
    all_mapped_images = {}
    
    for root_dir in root_dirs:
        if not os.path.exists(root_dir):
            continue
            
        # Walk through directory
        if os.path.isdir(root_dir):
            for dirpath, dirnames, filenames in os.walk(root_dir):
                for filename in filenames:
                    if filename.lower().endswith('.ini') or filename.lower().endswith('.txt'):
                        filepath = os.path.join(dirpath, filename)
                        # We try to parse everything that looks like an INI/TXT
                        # parse_ini handles the content check (looking for MappedImage)
                        try:
                            # optimization: quick check if file contains 'MappedImage' before full parse
                            with open(filepath, 'r', errors='ignore') as f:
                                if 'mappedimage' in f.read().lower():
                                    print(f"Loading images from {filepath}...")
                                    images = parse_ini(filepath)
                                    all_mapped_images.update(images)
                        except Exception as e:
                            print(f"Skipping {filepath}: {e}")
                            
        elif os.path.isfile(root_dir):
            # Single file
             try:
                print(f"Loading images from {root_dir}...")
                images = parse_ini(root_dir)
                all_mapped_images.update(images)
             except Exception as e:
                print(f"Skipping {root_dir}: {e}")

    return all_mapped_images

def main():
    parser = argparse.ArgumentParser(description="Overlay Generator and Updater")
    parser.add_argument('--generate', action='store_true', help="Generate SVG from INI/TXT")
    parser.add_argument('--update', action='store_true', help="Update TXT from SVG (Overwrites original file!)")
    parser.add_argument('--updatenew', action='store_true', help="Update TXT from SVG (Creates new file)")
    parser.add_argument('--svg', help="SVG file path")
    parser.add_argument('--scheme', required=True, help="ControlBarScheme Section Name (e.g. GLA8x6)")
    parser.add_argument('--scheme-file', default="INI/ControlBarScheme.ini", help="Control Bar Scheme file path (default: INI/ControlBarScheme.ini)")
    
    args = parser.parse_args()
    
    # Default SVG filename
    if not args.svg:
        args.svg = f"{args.scheme}_scheme.svg"
    
    # Default to generate if no args provided
    if not args.generate and not args.update and not args.updatenew:
        args.generate = True
    
    if args.generate:
        output_dir = "extracted_images"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        print("Scanning for Mapped Images...")
        # Explicitly load local HandCreatedMappedImages.txt if it exists
        mapped_images = {}
        if os.path.exists("HandCreatedMappedImages.txt"):
             print("Loading HandCreatedMappedImages.txt...")
             mapped_images.update(parse_ini("HandCreatedMappedImages.txt"))

        # Search INI and MappedImages directories
        search_dirs = []
        if os.path.exists('INI'):
            search_dirs.append('INI')
        if os.path.exists('MappedImages'):
            search_dirs.append('MappedImages')
            
        mapped_images.update(load_all_mapped_images(search_dirs))
        print(f"Loaded {len(mapped_images)} mapped images total.")
        
        print(f"Parsing Control Scheme Section '{args.scheme}' from {args.scheme_file}...")
        rects, base_image_info, screen_res = parse_control_scheme(args.scheme_file, args.scheme)
        
        if not rects and not base_image_info:
            print(f"No data found for section '{args.scheme}'. Please check the name.")
        else:
            generate_svg(rects, base_image_info, mapped_images, output_dir, args.svg, screen_res)
        
    if args.update or args.updatenew:
        output_path = None
        if args.updatenew:
             base, ext = os.path.splitext(args.scheme_file)
             output_path = f"{base}_updated{ext}"
        else:
             output_path = args.scheme_file
             
        print(f"Updating Section '{args.scheme}' in {args.scheme_file} from {args.svg}...")
        update_control_scheme_from_svg(args.svg, args.scheme_file, args.scheme, output_path)

if __name__ == "__main__":
    main()
