class FakeLLMResponse:
    def __init__(self, output_text: str = "", output=None):
        self.output_text = output_text
        self.output = output or []
