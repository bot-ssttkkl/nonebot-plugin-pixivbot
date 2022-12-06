class CardBuilder:
    def __init__(self):
        self.modules = []

    def build(self):
        return [
            {
                "type": "card",
                "theme": "secondary",
                "size": "lg",
                "modules": self.modules
            }
        ]

    def header(self, content):
        self.modules.append({
            "type": "header",
            "text": {
                "type": "plain-text",
                "content": content
            }
        })
        return self

    def image_container(self, src):
        self.modules.append({
            "type": "container",
            "elements": [
                {
                    "type": "image",
                    "src": src
                }
            ]
        })
        return self

    def section(self, content, type="plain-text"):
        self.modules.append({
            "type": "section",
            "text": {
                "type": type,
                "content": content
            }
        })
        return self
