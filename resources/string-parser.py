import sys
import enum
from pathlib import Path
from typing import BinaryIO


class StringContainerType(enum.IntEnum):
    Strings = 0
    DLStrings = 1
    ILStrings = 2


def parse_strings_file(file_path: str):
    """Read and parse .strings/.dlstrings/.ilstrings file."""
    path = Path(file_path)

    # Determine file type by extension
    ext = path.suffix.lower()
    if ext == ".strings":
        type_ = StringContainerType.Strings
    elif ext == ".dlstrings":
        type_ = StringContainerType.DLStrings
    elif ext == ".ilstrings":
        type_ = StringContainerType.ILStrings
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    with open(file_path, "rb") as f:
        # Parse header
        count = int.from_bytes(f.read(4), byteorder="little")
        size = int.from_bytes(f.read(4), byteorder="little")

        # Read directory entries
        directory = []
        for _ in range(count):
            string_id = int.from_bytes(f.read(4), byteorder="little")
            offset = int.from_bytes(f.read(4), byteorder="little")
            directory.append((string_id, offset))

        # Read strings
        strings = {}
        for string_id, offset in directory:
            f.seek(8 + (count * 8) + offset)  # Header + directory + offset

            if type_ == StringContainerType.Strings:
                # Read null-terminated string
                chars = []
                while True:
                    char = f.read(1)
                    if char == b"\x00":
                        break
                    chars.append(char)
                string_bytes = b"".join(chars)
            else:  # DLStrings or ILStrings
                str_size = int.from_bytes(f.read(4), byteorder="little")
                string_bytes = f.read(str_size)

            # Try UTF-8 first, fallback to CP1252
            try:
                strings[string_id] = string_bytes.decode("utf-8")
            except UnicodeDecodeError:
                strings[string_id] = string_bytes.decode("cp1252")

        return strings


def main():
    if len(sys.argv) != 2:
        print("Usage: python strings_reader.py <path_to_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        strings = parse_strings_file(file_path)
        print(f"Found {len(strings)} strings in {file_path}:")
        for string_id, string in strings.items():
            print(f"{string_id}: {string}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
