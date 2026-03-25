from pathlib import Path

p = Path('file.txt')
text = p.read_text()
p.write_text('hello')
