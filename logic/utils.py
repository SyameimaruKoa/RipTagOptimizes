def sanitize_foldername(name: str) -> str:
    replacements = {
        '\\': '¥',
        '/': '／',
        ':': '：',
        '*': '＊',
        '?': '？',
        '"': '"',
        '<': '＜',
        '>': '＞',
        '|': '｜'
    }
    for char, replacement in replacements.items():
        name = name.replace(char, replacement)
    return name

def sanitize_filename(filename: str) -> str:
    return sanitize_foldername(filename)
