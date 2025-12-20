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
                            coords[k] = int(v)
                    current_image['coords'] = coords

    return mapped_images

def parse_control_scheme(filepath):
    """Parses the ControlBarScheme file."""
    base_image = None
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    button_mappings = {} # ButtonName -> {State: ImageName}
    button_positions = {} # ButtonName -> {UL: (x,y), LR: (x,y)}
    
    current_scheme = None
    in_image_part = False
    
    # Parse ScreenCreationRes
    screen_res = {'x': 800, 'y': 600} # Default

    for line in lines:
        line = line.strip()
        if not line or line.startswith(';'):
            continue
            
        if line.startswith('ControlBarScheme'):
            current_scheme = line.split()[1]
        
        if line.startswith('ScreenCreationRes'):
             match = re.search(r"X:(\d+)\s+Y:(\d+)", line)
             if match:
                 screen_res['x'] = int(match.group(1))
                 screen_res['y'] = int(match.group(2))

        # Parse Button Mappings
        # Look for *Button*
        if 'Button' in line and len(line.split()) >= 2:
            parts = line.split()
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
        if line.endswith('UL') or 'UL ' in line:
             match = re.search(r"(\w+)UL\s+X:(\d+)\s+Y:(\d+)", line)
             if match:
                 name = match.group(1)
                 if name not in button_positions: button_positions[name] = {}
                 button_positions[name]['UL'] = (int(match.group(2)), int(match.group(3)))

        if line.endswith('LR') or 'LR ' in line:
             match = re.search(r"(\w+)LR\s+X:(\d+)\s+Y:(\d+)", line)
             if match:
                 name = match.group(1)
                 if name not in button_positions: button_positions[name] = {}
                 button_positions[name]['LR'] = (int(match.group(2)), int(match.group(3)))

        # Parse Base Image
        if line == 'ImagePart':
            in_image_part = True
            base_image = {}
        elif line == 'End' and in_image_part:
            in_image_part = False
        elif in_image_part:
            if line.startswith('Position'):
                match = re.search(r"X:(\d+)\s+Y:(\d+)", line)
                if match:
                    base_image['x'] = int(match.group(1))
                    base_image['y'] = int(match.group(2))
            elif line.startswith('Size'):
                match = re.search(r"X:(\d+)\s+Y:(\d+)", line)
                if match:
                    base_image['width'] = int(match.group(1))
                    base_image['height'] = int(match.group(2))
            elif line.startswith('ImageName'):
                base_image['name'] = line.split()[1]
                
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
    # Handle extension mismatch or missing files
    if not os.path.exists(texture_file):
        base, ext = os.path.splitext(texture_file)
        if ext.lower() == '.tga':
            png_file = base + '.png'
            if os.path.exists(png_file):
                texture_file = png_file
            elif os.path.exists(png_file.lower()):
                 texture_file = png_file.lower()
            elif os.path.exists(texture_file.lower()):
                texture_file = texture_file.lower()
            elif 'sacommandbar' in texture_file.lower():
                if os.path.exists('sacommandbar.png'):
                    texture_file = 'sacommandbar.png'
            elif 'sacontrolbar512_001' in texture_file.lower():
                if os.path.exists('sacontrolbar512_001.tga'):
                    texture_file = 'sacontrolbar512_001.tga'
    
    if not os.path.exists(texture_file):
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

def random_color():
    """Generates a random RGB color string."""
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return f"rgb({r},{g},{b})"

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

def update_control_scheme_from_svg(svg_path, scheme_path):
    """Updates the ControlBarScheme file based on SVG rect coordinates."""
    if not os.path.exists(svg_path):
        print(f"Error: SVG file {svg_path} not found.")
        return
        
    if not os.path.exists(scheme_path):
        print(f"Error: Scheme file {scheme_path} not found.")
        return

    # Parse SVG
    # We need to handle namespaces if they exist, but usually simple parsing works for basic SVGs
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
    svg_width = root.get('width', '800')
    svg_height = root.get('height', '600')
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
    in_image_part = False
    
    for line in lines:
        original_line = line
        line = line.strip()
        
        if line.startswith('ScreenCreationRes'):
             # Preserve indentation if any (though usually top level)
             indent = original_line[:original_line.find('ScreenCreationRes')]
             new_lines.append(f"{indent}ScreenCreationRes X:{int(float(svg_width))} Y:{int(float(svg_height))}\n")
             continue
        
        if line == 'ImagePart':
            in_image_part = True
            new_lines.append(original_line)
            continue
        elif line == 'End' and in_image_part:
            in_image_part = False
            new_lines.append(original_line)
            continue
            
        if in_image_part and 'ImagePart' in updated_coords:
            img_part_data = updated_coords['ImagePart']
            if line.startswith('Position'):
                 match = re.search(r"X:(\d+)\s+Y:(\d+)", line)
                 if match:
                      # keep indentation
                      indent = original_line[:original_line.find('Position')]
                      new_lines.append(f"{indent}Position X:{img_part_data['UL'][0]} Y:{img_part_data['UL'][1]}\n")
                 else:
                      new_lines.append(original_line)
                 continue
            elif line.startswith('Size'):
                 match = re.search(r"X:(\d+)\s+Y:(\d+)", line)
                 if match:
                      indent = original_line[:original_line.find('Size')]
                      new_lines.append(f"{indent}Size X:{img_part_data['w']} Y:{img_part_data['h']}\n")
                 else:
                      new_lines.append(original_line)
                 continue

        # Check for UL/LR lines
        # MinMaxUL X:646 Y:432
        ul_match = re.search(r"(\w+)UL\s+X:(\d+)\s+Y:(\d+)", line)
        if ul_match:
            name = ul_match.group(1)
            if name in updated_coords:
                new_ul = updated_coords[name]['UL']
                # Preserve indentation
                indent = original_line[:original_line.find(name)]
                new_lines.append(f"{indent}{name}UL X:{new_ul[0]} Y:{new_ul[1]}\n")
                continue
                
        lr_match = re.search(r"(\w+)LR\s+X:(\d+)\s+Y:(\d+)", line)
        if lr_match:
            name = lr_match.group(1)
            if name in updated_coords:
                new_lr = updated_coords[name]['LR']
                indent = original_line[:original_line.find(name)]
                new_lines.append(f"{indent}{name}LR X:{new_lr[0]} Y:{new_lr[1]}\n")
                continue
                
        new_lines.append(original_line)
        
    # Save Updated File
    base, ext = os.path.splitext(scheme_path)
    output_path = f"{base}-updated{ext}"
    
    with open(output_path, 'w') as f:
        f.writelines(new_lines)
        
    print(f"Saved updated scheme to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Overlay Generator and Updater")
    parser.add_argument('--generate', action='store_true', help="Generate SVG from INI/TXT")
    parser.add_argument('--update', action='store_true', help="Update TXT from SVG")
    parser.add_argument('--svg', default="output_overlay_with_images.svg", help="SVG file path")
    parser.add_argument('--scheme', default="ControlBarSchemeUSA.txt", help="Control Bar Scheme file path")
    
    args = parser.parse_args()
    
    # Default to generate if no args provided
    if not args.generate and not args.update:
        args.generate = True
    
    if args.generate:
        output_dir = "extracted_images"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        print("Parsing INI files...")
        mapped_images = parse_ini("SAControlBar512.INI")
        mapped_images.update(parse_ini("HandCreatedMappedImages.txt"))
        
        print(f"Parsing Control Scheme {args.scheme}...")
        print(f"Parsing Control Scheme {args.scheme}...")
        rects, base_image_info, screen_res = parse_control_scheme(args.scheme)
        
        generate_svg(rects, base_image_info, mapped_images, output_dir, args.svg, screen_res)
        
    if args.update:
        print(f"Updating {args.scheme} from {args.svg}...")
        update_control_scheme_from_svg(args.svg, args.scheme)

if __name__ == "__main__":
    main()
