# BitRanger

BitRanger is a Python script that parses custom `.btf` (Bitfield Text Format) files and renders them into visual bitfield diagrams (PNG or JPEG).

## Requirements
- Python 3.x
- Pillow (`pip install Pillow`)

## Usage
Run the script from the command line, passing the `.btf` file as an argument:
```bash
python bitranger.py <file.btf>
```

## `.btf` File Format

A `.btf` file consists of two main parts: an optional configuration block and one or more bitfield definitions. Comments can be added using `//`.

### Configuration
The `@config` block defines global settings for the output image. It is optional.

```text
@config {
    output: "png";          // Output format (png or jpeg, default: png)
    filename: "output";     // Output filename without extension (default: output)
    theme: "dark";          // "dark" or "grayscale" (default: grayscale)
    bits_per_row: 32;       // Number of bits per row before wrapping (default: 32)
}
```

### Bitfields
Each bitfield is defined with a name, a sequence of bit blocks, and a mapping of characters to labels and colors.

```text
! $BitfieldName: [block1][block2]\... {
    char: "Label" #COLOR
    _: "Reserved"
};
```
- Prefix the bitfield name with `$` to draw the title above the bitfield. Without the `$`, the bitfield will render without a title.
- Prefix the bitfield name with `! ` (with a space) to hide the legend. Without the `!`, the legend is drawn automatically.

**Bit Blocks:**
Blocks are enclosed in square brackets `[]`. Inside, you can specify:
- `char:length` (e.g., `[b:8]`) - Defines a block mapped to the character `b` with a length of 8 bits.
- `digits:length` (e.g., `[01:2]`) - If the character is a sequence of digits exactly matching the specified length, it creates a single combined field where each literal digit is visually aligned to its respective bit column.
- `string` (e.g., `[aaaa]`) - Defines a block where the length of the string is the block length, and the first character is used for mapping. Empty brackets `[]` default to `_`.
- `comma-separated numbers` (e.g., `[1, 0, 1]`) - Creates a single combined field where each literal bit value is visually aligned and spaced out to its respective bit column.
- `\` (outside brackets) - Forces a line break in the rendering, starting a new row of bits.

**Mapping:**
Inside the curly braces `{}`, you map the characters used in your blocks to a label and an optional hex color code.
- Format: `char: "Label" #HexColor`
- The underscore `_` is commonly used as the default character for reserved or undefined bits.

### Example
```text
@config {
    output: "png";
    filename: "example_bitfield";
    theme: "dark";
    bits_per_row: 16;
}

InstructionFormat: [op:6][rs:5][rt:5] \ [imm:16] {
    op: "Opcode" #FF5555
    rs: "Source Reg" #55FF55
    rt: "Target Reg" #5555FF
    imm: "Immediate" #FFFF55
};
```

This will generate `example_bitfield.png` displaying the `InstructionFormat` bitfield in a dark theme.
