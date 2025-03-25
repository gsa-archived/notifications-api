import re

import markdown
from markdown.blockprocessors import BlockQuoteProcessor
from markdown.extensions import Extension


class NotificationRenderer(markdown.treeprocessor.Treeprocessor):
    def run(self, root):
        for element in root.iter():
            if element.tag == "pre" and len(element) > 0 and element[0].tag == "code":
                element.clear()
                element.text = markdown.util.AtomicString(element[0].text)
                element[0].tag = "code"
            elif element.tag == "blockquote":
                pass
            elif element.tag in ("ul", "ol"):
                pass
            elif element.tag == "li":
                pass
            elif element.tag == "p":
                pass
            elif element.tag == "strong":
                pass
            elif element.tag == "em":
                pass
            elif element.tag == "a":
                element.set("href", markdown.util.escape(element.get("href")))
            elif element.tag == "code" and element.getparent().tag != "pre":
                element.text = markdown.util.AtomicString(
                    markdown.util.escape(element.text)
                )


class NotificationRendererExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(
            NotificationRenderer(md), "notification_renderer", 15
        )


class CustomBlockQuoteProcessor(BlockQuoteProcessor):
    RE = re.compile(r"^(>.*(?:\n$))+$", re.MULTILINE)

    def test(self, parent, block):
        return bool(self.RE.match(block))


class CustomBlockQuoteExtension(Extension):
    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(
            CustomBlockQuoteProcessor(md.parser), "quote", 70
        )


md = markdown.Markdown(
    extensions=[
        CustomBlockQuoteExtension(),
        NotificationRendererExtension(),
        "markdown.extensions.extra",  # for tables, fenced code, etc.
    ]
)


def render(text):
    return md.convert(text)
