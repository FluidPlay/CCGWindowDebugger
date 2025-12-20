import re
import argparse
import math
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import random

def parse_matrix(matrix_str):
    """Parses an SVG matrix string 'matrix(a,b,c,d,e,f)' into a list of floats."""
    if not matrix_str or 'matrix' not in matrix_str:
        return [1, 0, 0, 1, 0, 0] # Identity
    
    content = matrix_str[matrix_str.find('(')+1 : matrix_str.find(')')]
    return [float(x) for x in content.split(',')]

def apply_matrix(x, y, matrix):
    """Applies the matrix to a point (x, y)."""
    a, b, c, d, e, f = matrix
    new_x = a * x + c * y + e
    new_y = b * x + d * y + f
    return new_x, new_y

def get_center(x, y, w, h):
    return x + w / 2, y + h / 2

def dist_sq(p1, p2):
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

def parse_float(val_str):
    """Parses a float string that might contain units like 'px'."""
    if not val_str:
        return 0.0
    val_str = str(val_str).strip()
    if val_str.endswith('px'):
        val_str = val_str[:-2]
    return float(val_str)

def parse_svg(filepath):
    """
    Parses the SVG to find rectangles and their closest text labels.
    Returns a list of dicts: {'name': text, 'UL': (x1, y1), 'LR': (x2, y2)}
    """
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    
    rects = []
    texts = []
    
    # Helper to traverse and keep track of transforms
    def traverse(node, current_matrix):
        # Update matrix if this node has a transform
        node_matrix = current_matrix
        if 'transform' in node.attrib:
            # We only handle matrix() for now as seen in the file
            m = parse_matrix(node.attrib['transform'])
            
            A, B, C, D, E, F = current_matrix
            a, b, c, d, e, f = m
            
            new_a = A*a + C*b
            new_c = A*c + C*d
            new_e = A*e + C*f + E
            
            new_b = B*a + D*b
            new_d = B*c + D*d
            new_f = B*e + D*f + F
            
            node_matrix = [new_a, new_b, new_c, new_d, new_e, new_f]

        # Check for rect
        if node.tag.endswith('rect'):
            try:
                x = parse_float(node.attrib.get('x', 0))
                y = parse_float(node.attrib.get('y', 0))
                w = parse_float(node.attrib.get('width', 0))
                h = parse_float(node.attrib.get('height', 0))
                
                # Transform the 4 corners to find the new bounding box
                corners = [
                    apply_matrix(x, y, node_matrix),
                    apply_matrix(x+w, y, node_matrix),
                    apply_matrix(x, y+h, node_matrix),
                    apply_matrix(x+w, y+h, node_matrix)
                ]
                
                xs = [p[0] for p in corners]
                ys = [p[1] for p in corners]
                
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                
                rects.append({
                    'x': min_x, 'y': min_y, 
                    'w': max_x - min_x, 'h': max_y - min_y,
                    'center': get_center(min_x, min_y, max_x - min_x, max_y - min_y)
                })
            except ValueError:
                pass

        # Check for text
        if node.tag.endswith('text'):
            # Text position is usually the anchor point.
            text_content = "".join(node.itertext()).strip()
            if text_content:
                try:
                    x = parse_float(node.attrib.get('x', 0))
                    y = parse_float(node.attrib.get('y', 0))
                    
                    # Apply transform
                    tx, ty = apply_matrix(x, y, node_matrix)
                    
                    texts.append({
                        'text': text_content,
                        'x': tx, 'y': ty
                    })
                except ValueError:
                    pass

        for child in node:
            traverse(child, node_matrix)

    traverse(root, [1, 0, 0, 1, 0, 0])
    
    # Match rects to closest text
    results = []
    for rect in rects:
        closest_text = None
        min_dist = float('inf')
        
        for text in texts:
            d = dist_sq(rect['center'], (text['x'], text['y']))
            if d < min_dist:
                min_dist = d
                closest_text = text['text']
        
        if closest_text:
            # Round coordinates to integers
            results.append({
                'name': closest_text,
                'UL': (int(round(rect['x'])), int(round(rect['y']))),
                'LR': (int(round(rect['x'] + rect['w'])), int(round(rect['y'] + rect['h'])))
            })
            
    return results

def parse_mapped_images(filepath, target_image_name):
    """Parses HandCreatedMappedImages.txt to find the coordinates of the target image."""
    coords = None
    texture_file = None
    
    with open(filepath, 'r') as f:
        content = f.read()
        
    pattern = re.compile(r"MappedImage\s+" + re.escape(target_image_name) + r"\s+(.*?)End", re.DOTALL)
    match = pattern.search(content)
    
    if match:
        block = match.group(1)
        for line in block.split('\n'):
            line = line.strip()
            if line.startswith(';') or not line:
                continue
            if line.lower().startswith('texture') and '=' in line:
                key, value = line.split('=', 1)
                if key.strip().lower() == 'texture':
                    texture_file = value.strip()
                    break
            
        coords_match = re.search(r"Coords\s*=\s*Left:(\d+)\s+Top:(\d+)\s+Right:(\d+)\s+Bottom:(\d+)", block)
        if coords_match:
            coords = {
                'Left': int(coords_match.group(1)),
                'Top': int(coords_match.group(2)),
                'Right': int(coords_match.group(3)),
                'Bottom': int(coords_match.group(4))
            }
            
    return texture_file, coords

def parse_control_bar_scheme(filepath, scheme_name):
    """Parses ControlBarSchemeUSA.txt to find coordinates for the scheme."""
    offset = {'X': 0, 'Y': 0}
    screen_res = {'X': 800, 'Y': 600} # Default
    image_part_info = {'Position': {'X': 0, 'Y': 0}, 'Size': {'X': 0, 'Y': 0}}
    rects = []
    ul_coords = {}
    lr_coords = {}
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    in_scheme = False
    in_image_part = False
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith(';'):
            continue
            
        if line.startswith("ControlBarScheme") and scheme_name in line:
            in_scheme = True
            continue
            
        if in_scheme:
            if line.startswith("ScreenCreationRes"):
                res_match = re.search(r"X:(\d+)\s+Y:(\d+)", line)
                if res_match:
                    screen_res['X'] = int(res_match.group(1))
                    screen_res['Y'] = int(res_match.group(2))
                continue
            if line == "End":
                if in_image_part:
                    in_image_part = False
                    continue
                else:
                    in_scheme = False
                    break
            
            if line.startswith("ImagePart"):
                in_image_part = True
                continue
                
            if in_image_part:
                if line.lower().startswith("position"):
                    pos_match = re.search(r"X:(\d+)\s+Y:(\d+)", line, re.IGNORECASE)
                    if pos_match:
                        offset['X'] = int(pos_match.group(1))
                        offset['Y'] = int(pos_match.group(2))
                        image_part_info['Position']['X'] = offset['X']
                        image_part_info['Position']['Y'] = offset['Y']
                
                if line.lower().startswith("size"):
                    size_match = re.search(r"X:(\d+)\s+Y:(\d+)", line, re.IGNORECASE)
                    if size_match:
                        image_part_info['Size']['X'] = int(size_match.group(1))
                        image_part_info['Size']['Y'] = int(size_match.group(2))
            else:
                ul_match = re.search(r"(\w+)UL\s+X:(\d+)\s+Y:(\d+)", line)
                if ul_match:
                    name = ul_match.group(1)
                    ul_coords[name] = (int(ul_match.group(2)), int(ul_match.group(3)))
                    
                lr_match = re.search(r"(\w+)LR\s+X:(\d+)\s+Y:(\d+)", line)
                if lr_match:
                    name = lr_match.group(1)
                    lr_coords[name] = (int(lr_match.group(2)), int(lr_match.group(3)))
    
    for name, ul in ul_coords.items():
        if name in lr_coords:
            lr = lr_coords[name]
            rects.append({'name': name, 'UL': ul, 'LR': lr})
                
    return offset, rects, screen_res, image_part_info

def update_control_scheme(scheme_filepath, svg_filepath, output_filepath, scheme_name):
    """Updates the ControlBarScheme file with coordinates from the SVG."""
    
    # 1. Parse SVG to get new rects (absolute coordinates in the image)
    svg_rects = parse_svg(svg_filepath)
    print(f"Parsed {len(svg_rects)} rectangles from SVG.")
    
    # 2. Parse existing scheme to get the Offset
    offset, _, _, _ = parse_control_bar_scheme(scheme_filepath, scheme_name)
    print(f"Using Offset: {offset}")
    
    # 3. Create a map of updates
    updates = {}
    for rect in svg_rects:
        name = rect['name']
        # SVG coordinates are now absolute (0-800, 0-600)
        # Scheme coordinates are also absolute.
        # So we just take the SVG coordinates directly.
        
        ul_x = rect['UL'][0]
        ul_y = rect['UL'][1]
        lr_x = rect['LR'][0]
        lr_y = rect['LR'][1]
        
        if name == 'ImagePart':
             # Special handling for ImagePart: Store Position (UL) and Size (W, H)
             width = lr_x - ul_x
             height = lr_y - ul_y
             updates[name] = {'Position': (ul_x, ul_y), 'Size': (width, height)}
        else:
             updates[name] = {'UL': (ul_x, ul_y), 'LR': (lr_x, lr_y)}

    # 4. Read and Update the file content
    with open(scheme_filepath, 'r') as f:
        lines = f.readlines()
        
    new_lines = []
    in_scheme = False
    in_image_part = False
    
    for line in lines:
        original_line = line
        line = line.strip()
        
        if line.startswith("ControlBarScheme") and scheme_name in line:
            in_scheme = True
            new_lines.append(original_line)
            continue
            
        if in_scheme and line == "End":
            if in_image_part:
                in_image_part = False
                new_lines.append(original_line)
                continue
            else:
                in_scheme = False
                new_lines.append(original_line)
                continue
            
        if in_scheme:
            if line.startswith("ImagePart"):
                in_image_part = True
                new_lines.append(original_line)
                continue
            
            if in_image_part:
                if 'ImagePart' in updates:
                    upd = updates['ImagePart']
                    if line.strip().lower().startswith("position"):
                        indent = original_line[:original_line.lower().find("position")]
                        new_lines.append(f"{indent}Position X:{int(upd['Position'][0])} Y:{int(upd['Position'][1])}\n")
                        continue
                    if line.strip().lower().startswith("size"):
                        indent = original_line[:original_line.lower().find("size")]
                        new_lines.append(f"{indent}Size X:{int(upd['Size'][0])} Y:{int(upd['Size'][1])}\n")
                        continue
            
            # Check for UL/LR lines to update
            ul_match = re.search(r"(\w+)UL\s+X:(\d+)\s+Y:(\d+)", line)
            if ul_match:
                name = ul_match.group(1)
                if name in updates:
                    new_x, new_y = updates[name]['UL']
                    # Preserve indentation
                    indent = original_line[:original_line.find(name)]
                    new_lines.append(f"{indent}{name}UL X:{new_x} Y:{new_y}\n")
                    continue

            lr_match = re.search(r"(\w+)LR\s+X:(\d+)\s+Y:(\d+)", line)
            if lr_match:
                name = lr_match.group(1)
                if name in updates:
                    new_x, new_y = updates[name]['LR']
                    indent = original_line[:original_line.find(name)]
                    new_lines.append(f"{indent}{name}LR X:{new_x} Y:{new_y}\n")
                    continue
        
        new_lines.append(original_line)
        
    with open(output_filepath, 'w') as f:
        f.writelines(new_lines)
    print(f"Updated scheme written to {output_filepath}")

def generate_overlay(mapped_images_file, control_scheme_file, scheme_name, target_image_name):
    # 1. Parse Mapped Images
    texture_file, texture_coords = parse_mapped_images(mapped_images_file, target_image_name)
    if not texture_file or not texture_coords:
        print("Failed to find texture info.")
        return

    base_image_path = texture_file.replace(".tga", ".png")
    try:
        img = Image.open("sacommandbar.png")
    except FileNotFoundError:
        try:
            img = Image.open(base_image_path)
        except FileNotFoundError:
             print(f"Could not find image file: {base_image_path}")
             return

    # 2. Parse Control Scheme
    offset, rects, screen_res, image_part_info = parse_control_bar_scheme(control_scheme_file, scheme_name)
    
    # 3. Crop
    crop_box = (
        texture_coords['Left'],
        texture_coords['Top'],
        texture_coords['Right'] + 1,
        texture_coords['Bottom'] + 1
    )
    cropped_img = img.crop(crop_box)
    
    # 4. Prepare Data
    draw_data = []
    for rect in rects:
        ul = rect['UL']
        lr = rect['LR']
        
        # For PNG (cropped), we still need relative coordinates to the crop
        x1_png = ul[0] - offset['X']
        y1_png = ul[1] - offset['Y']
        x2_png = lr[0] - offset['X']
        y2_png = lr[1] - offset['Y']
        
        # For SVG, we use absolute coordinates
        x1_svg = ul[0]
        y1_svg = ul[1]
        x2_svg = lr[0]
        y2_svg = lr[1]
        
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
        
        draw_data.append({
            'name': rect['name'],
            'x1_png': x1_png, 'y1_png': y1_png, 'x2_png': x2_png, 'y2_png': y2_png,
            'x1_svg': x1_svg, 'y1_svg': y1_svg, 'x2_svg': x2_svg, 'y2_svg': y2_svg,
            'color': color
        })

    # 5. Draw PNG
    draw = ImageDraw.Draw(cropped_img)
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except IOError:
        font = ImageFont.load_default()
        
    for item in draw_data:
        x1, y1, x2, y2 = item['x1_png'], item['y1_png'], item['x2_png'], item['y2_png']
        color = item['color']
        text = item['name']
        
        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
        
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        if hasattr(draw, 'textbbox'):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = draw.textsize(text, font=font)
            
        text_x = center_x - (text_width / 2)
        text_y = center_y - (text_height / 2)
        
        draw.text((text_x, text_y), text, fill="white", font=font)

    cropped_img.save("output_overlay.png")
    print("Saved output_overlay.png")

    # 6. Generate SVG
    svg_width = screen_res['X']
    svg_height = screen_res['Y']
    
    svg_lines = [
        f'<svg width="{svg_width}px" height="{svg_height}px" viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">',
        '  <style>',
        '    text { font-family: Arial, sans-serif; font-size: 12px; fill: black; text-anchor: middle; dominant-baseline: middle; }',
        '    rect { stroke: none; }',
        '  </style>'
    ]
    
    # Add ImagePart rectangle FIRST (bottom of Z-order)
    if image_part_info:
        ip_x = image_part_info['Position']['X']
        ip_y = image_part_info['Position']['Y']
        ip_w = image_part_info['Size']['X']
        ip_h = image_part_info['Size']['Y']
        
        svg_lines.append(f'  <g id="ImagePart">')
        svg_lines.append(f'    <rect x="{ip_x}" y="{ip_y}" width="{ip_w}" height="{ip_h}" fill="rgb(128,128,128)" fill-opacity="0.15" />')
        svg_lines.append(f'    <text x="{ip_x + ip_w/2}" y="{ip_y + ip_h/2}" fill="rgb(128,128,128)" fill-opacity="0.5">ImagePart</text>')
        svg_lines.append('  </g>')

    for item in draw_data:
        x1, y1, x2, y2 = item['x1_svg'], item['y1_svg'], item['x2_svg'], item['y2_svg']
        color = item['color']
        text = item['name']
        rgb_color = f"rgb({color[0]},{color[1]},{color[2]})"
        
        width = x2 - x1
        height = y2 - y1
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Group for each item to keep them organized
        svg_lines.append(f'  <g id="{text}">')
        svg_lines.append(f'    <rect x="{x1}" y="{y1}" width="{width}" height="{height}" fill="{rgb_color}" fill-opacity="0.25" />')
        svg_lines.append(f'    <text x="{center_x}" y="{center_y}">{text}</text>')
        svg_lines.append('  </g>')
        
        
        
    svg_lines.append('</svg>')
    
    with open("output_overlay.svg", "w") as f:
        f.write('\n'.join(svg_lines))
    print("Saved output_overlay.svg")

def main():
    parser = argparse.ArgumentParser(description="Bidirectional sync between ControlBarScheme and SVG.")
    parser.add_argument("--generate", action="store_true", help="Generate SVG from ControlBarScheme")
    parser.add_argument("--update", action="store_true", help="Update ControlBarScheme from SVG")
    parser.add_argument("--svg", default="output_overlay_new.svg", help="SVG file to read for update")
    parser.add_argument("--scheme", default="ControlBarSchemeUSA.txt", help="ControlBarScheme file")
    parser.add_argument("--output", default="ControlBarSchemeUSA-new.txt", help="Output ControlBarScheme file")
    
    args = parser.parse_args()
    
    mapped_images_file = "HandCreatedMappedImages.txt"
    target_image_name = "InGameUIAmericaBase"
    scheme_name = "America8x6"

    if args.update:
        update_control_scheme(args.scheme, args.svg, args.output, scheme_name)
    else:
        # Default to generate if no flag or --generate is passed
        generate_overlay(mapped_images_file, args.scheme, scheme_name, target_image_name)

if __name__ == "__main__":
    main()
