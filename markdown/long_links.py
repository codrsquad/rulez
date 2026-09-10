import sys
from pathlib import Path

from tree_sitter_markdown import language, inline_language
from tree_sitter import Language, Parser, Query, QueryCursor

block_language = Language(language())
block_parser = Parser(block_language)

link_reference_def = Query(block_language, "(link_reference_definition) @node")
inline = Query(block_language, "(inline) @node")

inline_language = Language(inline_language())
inline_parser = Parser(inline_language)
inline_link = Query(inline_language, "(inline_link) @node")

MAX_INLINE_LINK_DESTINATION_BYTES = 80


def node_matches(query, node):
    for idx, match in QueryCursor(query).matches(node):
        yield match["node"][0]

def child_for_type(node, typ):
    for c in node.children:
        if c.type == typ:
            return c
    raise IndexError(typ)

def main(filenames: list[str]) -> int:
    exit_code = 0
    for f in filenames:
        edits = []
        link_references = {}
        lines_to_add = []

        buf = Path(f).read_bytes()
        tree = block_parser.parse(buf)
        # .root_node = document
        # .children[] = section
        for node in node_matches(link_reference_def, tree.root_node):
            link_references[child_for_type(node, "link_label").text] = child_for_type(node, "link_destination").text

        for inline_node in node_matches(inline, tree.root_node):
            inline_tree = inline_parser.parse(inline_node.text)

            for link in node_matches(inline_link, inline_tree.root_node):
                dest = child_for_type(link, "link_destination")
                if len(dest.text) > MAX_INLINE_LINK_DESTINATION_BYTES:
                    link_text = b"[" + child_for_type(link, "link_text").text + b"]"
                    if link_text in link_references:
                        if link_references[link_text] != dest.text:
                            continue
                    else:
                        link_references[link_text] = dest.text
                        # TODO link_text might have newlines, should replace with single space?
                        lines_to_add.append(link_text + b": " + dest.text)
                    edits.append((link.start_byte + inline_node.start_byte, link.end_byte + inline_node.start_byte, link_text + b"[]"))

        if edits:
            for i, j, new_bytes in sorted(edits, reverse=True):
                buf = buf[:i] + new_bytes + buf[j:]

            while not buf.endswith(b"\n\n"):
                buf += b"\n"

            for line_to_add in lines_to_add:
                buf += line_to_add + b"\n"

            # print(buf.decode())
            Path(f).write_bytes(buf)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
