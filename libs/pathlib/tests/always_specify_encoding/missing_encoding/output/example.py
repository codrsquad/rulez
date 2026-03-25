from pathlib import Path

p = Path('file.txt')
text = p.read_text(encoding='utf-8')
p.write_text('hello', encoding='utf-8')
