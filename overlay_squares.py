import re
from PIL import Image, ImageDraw, ImageFont
import random

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
        
        # Extract Texture (ignore lines starting with ;)
        # Look for a line that starts with whitespace, then Texture, and does NOT have a ; before it.
        # multiline mode might be needed if we iterate lines, or we can just split lines.
        for line in block.split('\n'):
            line = line.strip()
            if line.startswith(';') or not line:
                continue
            if line.lower().startswith('texture') and '=' in line:
                # Check if it's "Texture =" or "TextureWidth ="
                key, value = line.split('=', 1)
                if key.strip().lower() == 'texture':
                    texture_file = value.strip()
                    break # Found the active texture
            
        # Extract Coords
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
    rects = []
    ul_coords = {}
    lr_coords = {}
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    in_scheme = False
    in_image_part = False
    
    for line in lines:
        raw_line = line
        line = line.strip()
        if not line or line.startswith(';'):
            continue
            
        # Check for scheme start
        if line.startswith("ControlBarScheme") and scheme_name in line:
            in_scheme = True
            continue
            
        if in_scheme:
            if line == "End":
                if in_image_part:
                    in_image_part = False
                    continue
                else:
                    in_scheme = False
                    break # End of scheme
            
            if line.startswith("ImagePart"):
                in_image_part = True
                continue
                
            if in_image_part:
                # Parse Position
                # Position X:0 Y:408
                if line.lower().startswith("position"):
                    pos_match = re.search(r"X:(\d+)\s+Y:(\d+)", line, re.IGNORECASE)
                    if pos_match:
                        offset['X'] = int(pos_match.group(1))
                        offset['Y'] = int(pos_match.group(2))
            else:
                # Parse UL/LR
                # NameUL X:123 Y:456
                ul_match = re.search(r"(\w+)UL\s+X:(\d+)\s+Y:(\d+)", line)
                if ul_match:
                    name = ul_match.group(1)
                    ul_coords[name] = (int(ul_match.group(2)), int(ul_match.group(3)))
                    
                lr_match = re.search(r"(\w+)LR\s+X:(\d+)\s+Y:(\d+)", line)
                if lr_match:
                    name = lr_match.group(1)
                    lr_coords[name] = (int(lr_match.group(2)), int(lr_match.group(3)))
    
    # Pair them up
    for name, ul in ul_coords.items():
        if name in lr_coords:
            lr = lr_coords[name]
            rects.append({'name': name, 'UL': ul, 'LR': lr})
                
    return offset, rects

def main():
    mapped_images_file = "HandCreatedMappedImages.txt"
    control_scheme_file = "ControlBarSchemeUSA.txt"
    target_image_name = "InGameUIAmericaBase"
    scheme_name = "America8x6"
    
    # 1. Parse Mapped Images
    texture_file, texture_coords = parse_mapped_images(mapped_images_file, target_image_name)
    print(f"Texture File: {texture_file}")
    print(f"Texture Coords: {texture_coords}")
    
    if not texture_file or not texture_coords:
        print("Failed to find texture info.")
        return

    # The provided file is .png, but the text says .tga. We'll use the .png version if available.
    base_image_path = texture_file.replace(".tga", ".png")
    # Actually, the user said "The referred texture, SACommandBar.tga (converted to .png), is also provided."
    # So we should look for sacommandbar.png (case insensitive usually, but let's be careful)
    
    # Let's just try to open 'sacommandbar.png' as it is in the file list
    try:
        img = Image.open("sacommandbar.png")
    except FileNotFoundError:
        print("sacommandbar.png not found. Trying to use the name from the file...")
        try:
            img = Image.open(base_image_path)
        except FileNotFoundError:
             print(f"Could not find image file: {base_image_path}")
             return

    # 2. Parse Control Scheme
    offset, rects = parse_control_bar_scheme(control_scheme_file, scheme_name)
    print(f"Offset: {offset}")
    print(f"Found {len(rects)} rectangles.")

    # 3. Crop the base image
    # Coords = Left:0 Top:64 Right:799 Bottom:255
    # The Coords are inclusive? Usually Left/Top is inclusive, Right/Bottom is inclusive or exclusive?
    # In many game engines, Right/Bottom are inclusive coordinates of the last pixel.
    # PIL crop takes (left, top, right, bottom) where right and bottom are exclusive.
    # So if Right is 799, width is 800 (0 to 799). PIL needs 800.
    # So we add 1 to Right and Bottom.
    
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
        
        # Calculate relative coordinates
        x1 = ul[0] - offset['X']
        y1 = ul[1] - offset['Y']
        x2 = lr[0] - offset['X']
        y2 = lr[1] - offset['Y']
        
        # Generate a random color for outline
        # Make it fully opaque for the outline
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
        
        draw_data.append({
            'name': rect['name'],
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'color': color
        })

    # 5. Draw PNG
    draw = ImageDraw.Draw(cropped_img)
    
    try:
        # Try to load a standard font
        font = ImageFont.truetype("arial.ttf", 12)
    except IOError:
        # Fallback to default font if arial is not found
        font = ImageFont.load_default()
        
    for item in draw_data:
        x1, y1, x2, y2 = item['x1'], item['y1'], item['x2'], item['y2']
        color = item['color']
        text = item['name']
        
        # Draw hollow rectangle (outline only)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
        
        # Calculate center
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Use textbbox to get text size
        if hasattr(draw, 'textbbox'):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = draw.textsize(text, font=font)
            
        text_x = center_x - (text_width / 2)
        text_y = center_y - (text_height / 2)
        
        # Draw text
        draw.text((text_x, text_y), text, fill="white", font=font)

    # Save PNG Output
    cropped_img.save("output_overlay.png")
    print("Saved output_overlay.png")

    # 6. Generate SVG
    svg_width = cropped_img.width
    svg_height = cropped_img.height
    
    svg_lines = [
        f'<svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">',
        '  <style>',
        '    text { font-family: Arial, sans-serif; font-size: 12px; fill: black; text-anchor: middle; dominant-baseline: middle; }',
        '    rect { fill: none; stroke-width: 2; }',
        '  </style>'
    ]
    
    for item in draw_data:
        x1, y1, x2, y2 = item['x1'], item['y1'], item['x2'], item['y2']
        color = item['color']
        text = item['name']
        
        # Convert color tuple to rgb string
        rgb_color = f"rgb({color[0]},{color[1]},{color[2]})"
        
        width = x2 - x1
        height = y2 - y1
        
        # Center for text
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        svg_lines.append(f'  <rect x="{x1}" y="{y1}" width="{width}" height="{height}" stroke="{rgb_color}" />')
        svg_lines.append(f'  <text x="{center_x}" y="{center_y}">{text}</text>')
        
    svg_lines.append('</svg>')
    
    with open("output_overlay.svg", "w") as f:
        f.write('\n'.join(svg_lines))
    print("Saved output_overlay.svg")

if __name__ == "__main__":
    main()
