# bitranger
# kat
# 6/11/2026
# made after a sesh of ultra lock in!!!!!

import re
import sys
from PIL import Image, ImageDraw, ImageFont

def get_font(size):
    for font in ["arial.ttf", "calibri.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]:
        try:
            return ImageFont.truetype(font, size)
        except IOError:
            continue
    return ImageFont.load_default()


def parse_btf(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    content = re.sub(r'//.*', '', content)
    config = {'output': 'png', 'filename': 'output', 'theme': 'grayscale', 'bits_per_row': 32}

    cfg_match = re.search(r'@config\s*\{([^}]+)\}', content)
    if cfg_match:
        for line in cfg_match.group(1).split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                k = k.strip()
                v = v.strip().strip('";')
                if k == 'bits_per_row':
                    config[k] = int(v)
                else:
                    config[k] = v
        # Remove the config block so it doesn't interfere with bitfield parsing
        content = content[:cfg_match.start()] + content[cfg_match.end():]

    pattern = re.compile(r'(!\s*)?(\$?(\w+)):\s*(.*?)\s*\{([^}]+)\};?', re.DOTALL)
    matches = pattern.findall(content)

    bitfields = []
    for hide_legend, full_name, name, blocks_str, mapping_str in matches:
        show_title = full_name.startswith('$')
        show_legend = not bool(hide_legend)
        mapping = {}
        for line in mapping_str.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            m = re.match(r'(\w+):\s*"([^"]+)"\s*(#[0-9A-Fa-f]{6})?', line)
            if m:
                mapping[m.group(1)] = {
                    'label': m.group(2),
                    'color': m.group(3)
                }

        rows = []
        current_row = []
        current_bits = 0

        tokens = re.findall(r'\[.*?\]|\\', blocks_str)
        for tok in tokens:
            if tok == '\\':
                if current_row:
                    rows.append(current_row)
                    current_row = []
                    current_bits = 0
                continue

            inner = tok[1:-1].strip()
            if not inner:
                continue
            items = []
            if re.match(r'^[\d\s,]+$', inner):
                parts = [p.strip() for p in inner.replace(',', ' ').split() if p.strip()]
                items.append((inner, len(parts), parts))
            else:
                if ':' in inner:
                    char, length_str = inner.split(':')
                    length = int(length_str)
                    lits = None
                    if re.match(r'^\d+$', char) and len(char) == length:
                        lits = list(char)
                    items.append((char, length, lits))
                else:
                    char = inner[0] if inner else '_'
                    items.append((char, len(inner), None))

            for char, length, lits in items:
                label_info = mapping.get(char, {'label': char, 'color': None})
                if char == '_':
                    label_info = mapping.get('_', {'label': 'Reserved', 'color': None})
                if lits is not None and char not in mapping:
                    res_info = mapping.get('_', {'label': '', 'color': None})
                    label_info = {'label': '', 'color': res_info['color']}

                remaining_len = length
                remaining_lits = lits

                while config['bits_per_row'] > 0 and current_bits + remaining_len > config['bits_per_row']:
                    rem = config['bits_per_row'] - current_bits
                    if rem <= 0:
                        if current_row:
                            rows.append(current_row)
                            current_row = []
                        current_bits = 0
                        continue
                    
                    chunk_lits = remaining_lits[:rem] if remaining_lits else None
                    if remaining_lits:
                        remaining_lits = remaining_lits[rem:]

                    current_row.append({
                        "char": char,
                        "length": rem,
                        "label": label_info['label'],
                        "color": label_info['color'],
                        "literals": chunk_lits
                    })
                    remaining_len -= rem
                    
                    rows.append(current_row)
                    current_row = []
                    current_bits = 0

                if remaining_len > 0:
                    current_row.append({
                        "char": char,
                        "length": remaining_len,
                        "label": label_info['label'],
                        "color": label_info['color'],
                        "literals": remaining_lits
                    })
                    current_bits += remaining_len

        if current_row:
            rows.append(current_row)

        bitfields.append({
            "name": name,
            "rows": rows,
            "mapping": mapping,
            "show_title": show_title,
            "show_legend": show_legend
        })

    return config, bitfields


def render(config, bitfields):
    if not bitfields:
        return

    BIT_W = 40
    BOX_H = 50
    MAR_X = 50
    MAR_Y = 80
    TIT_H = 40

    max_bits = config['bits_per_row']
    if max_bits <= 0:
        max_bits = max(sum(f['length'] for f in r) for bf in bitfields for r in bf['rows'])

    img_w = max_bits * BIT_W + MAR_X * 2

    # Dummy draw for text measurements
    dummy_img = Image.new('RGB', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    l_font = get_font(16)

    def get_legend_lines(bf):
        if not bf.get('show_legend', True):
            return 0
        mapping = bf.get('mapping', {})
        if not mapping:
            return 0
        lines = 1
        x = MAR_X
        for char, info in mapping.items():
            text = f"{char}: {info['label']}"
            bb = dummy_draw.textbbox((0, 0), text, font=l_font)
            w = bb[2] - bb[0] + 30
            if x + w > img_w - MAR_X and x != MAR_X:
                lines += 1
                x = MAR_X
            x += w + 20
        return lines

    total_rows = sum(len(bf['rows']) for bf in bitfields)
    total_legend_lines = sum(get_legend_lines(bf) for bf in bitfields)
    legend_padding = sum(20 for bf in bitfields if bf.get('mapping') and bf.get('show_legend', True))
    titles_count = sum(1 for i, bf in enumerate(bitfields) if bf.get('show_title') and i > 0)
    
    img_h = MAR_Y + total_rows * (BOX_H + MAR_Y) + titles_count * TIT_H + total_legend_lines * 30 + legend_padding

    bg_color = '#FFFFFF'
    text_color = '#000000'
    theme_colors = ['#EAEAEA', '#FFFFFF']

    if config.get('theme') == 'dark':
        bg_color = '#333333'
        text_color = '#FFFFFF'
        theme_colors = ['#555555', '#777777']

    img = Image.new('RGB', (img_w, img_h), bg_color)
    draw = ImageDraw.Draw(img)

    t_font = get_font(24)
    l_font = get_font(16)
    n_font = get_font(12)

    y_off = MAR_Y

    for i, bf in enumerate(bitfields):
        if bf.get('show_title'):
            if i > 0:
                y_off += TIT_H
            draw.text((MAR_X, y_off - TIT_H - 10), bf['name'], fill=text_color, font=t_font)
        
        curr_bit = sum(f['length'] for r in bf['rows'] for f in r) - 1

        for row in bf['rows']:
            x_off = MAR_X
            c_idx = 0

            for f in row:
                w = f['length'] * BIT_W
                c = f['color'] if f['color'] else theme_colors[c_idx % len(theme_colors)]
                c_idx += 1

                draw.rectangle([x_off, y_off, x_off + w, y_off + BOX_H], fill=c, outline=text_color, width=1)

                for i in range(1, f['length']):
                    bx = x_off + i * BIT_W
                    draw.line([(bx, y_off), (bx, y_off + 6)], fill=text_color, width=1)
                    draw.line([(bx, y_off + BOX_H), (bx, y_off + BOX_H - 6)], fill=text_color, width=1)

                draw.text((x_off + 2, y_off - 16), str(curr_bit), fill=text_color, font=n_font)
                if f['length'] > 1:
                    lb = str(curr_bit - f['length'] + 1)
                    bb = draw.textbbox((0, 0), lb, font=n_font)
                    draw.text((x_off + w - (bb[2] - bb[0]) - 2, y_off - 16), lb, fill=text_color, font=n_font)

                if f.get('literals'):
                    for i, lit in enumerate(f['literals']):
                        bb = draw.textbbox((0, 0), lit, font=l_font)
                        tx = x_off + i * BIT_W + (BIT_W - (bb[2] - bb[0])) / 2
                        ty = y_off + (BOX_H - (bb[3] - bb[1])) / 2 - 2
                        draw.text((tx, ty), lit, fill=text_color, font=l_font)
                else:
                    lb = f['label']
                    bb = draw.textbbox((0, 0), lb, font=l_font)
                    if bb[2] - bb[0] > w - 8:
                        lb = f['char'] * f['length']
                        bb = draw.textbbox((0, 0), lb, font=l_font)

                    tx = x_off + (w - (bb[2] - bb[0])) / 2
                    ty = y_off + (BOX_H - (bb[3] - bb[1])) / 2 - 2
                    draw.text((tx, ty), lb, fill=text_color, font=l_font)

                x_off += w
                curr_bit -= f['length']

            y_off += BOX_H + MAR_Y

        mapping = bf.get('mapping', {})
        if mapping and bf.get('show_legend', True):
            leg_x = MAR_X
            for char, info in mapping.items():
                text = f"{char}: {info['label']}"
                bb = draw.textbbox((0, 0), text, font=l_font)
                w = bb[2] - bb[0] + 30
                if leg_x + w > img_w - MAR_X and leg_x != MAR_X:
                    y_off += 30
                    leg_x = MAR_X
                
                c = info['color'] if info['color'] else theme_colors[0]
                draw.rectangle([leg_x, y_off, leg_x + 20, y_off + 20], fill=c, outline=text_color, width=1)
                draw.text((leg_x + 30, y_off), text, fill=text_color, font=l_font)
                
                leg_x += w + 20
            
            y_off += 30 + 20

    ext = config.get('output', 'png')
    if ext not in ['jpeg', 'png']:
        ext = 'png'
        print(f"Format {config.get('output')} requested but only PNG/JPEG supported by core script. Defaulting to PNG.")

    out = f"{config.get('filename', 'output')}.{ext}"
    img.save(out)
    print(f"Generated {out}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        c, b = parse_btf(sys.argv[1])
        render(c, b)
    else:
        print("Usage: python bitfield_renderer.py <file.btf>")