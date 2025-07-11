import sys

import tree_sitter_python
from tree_sitter import Language, Parser, Query

PY_LANGUAGE = Language(tree_sitter_python.language())
parser = Parser(PY_LANGUAGE)


def update_module(inpath: str, outpath: str, oldmod: str, newmod: str) -> None:
    with open(inpath) as f:
        code = f.read()

    modified_code = change_module(code, oldmod, newmod)

    with open(outpath, "w") as f:
        f.write(modified_code)

def change_module(code: str, oldmod: str, newmod: str) -> str:

    query = Query(PY_LANGUAGE, f"""
      (
        (import_statement 
          name: (dotted_name) @module_name)
        (#eq? @module_name "{oldmod}")
      )

      (
        (call
          function: (attribute 
            object: (identifier) @module_name))
        (#eq? @module_name "{oldmod}")
      )
    """)

    tree = parser.parse(code.encode("utf-8"))
    matches = query.matches(tree.root_node)

    replacements = []
    for _, captures in matches:
        node = captures["module_name"][0]
        assert node.text == oldmod.encode("utf-8")
        replacements.append((node.start_byte, node.end_byte))

    replacements.sort(reverse=True)

    modified_code = code.encode("utf-8")
    for start, end in replacements:
        modified_code = modified_code[:start] + newmod.encode("utf-8") + modified_code[end:]

    return modified_code.decode("utf-8")


def main(*files):
    for file in files:
        update_module(file, file, "appdirs", "platformdirs")


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
