import json

from class_quality.extractors import OllamaTranscriptExtractor
from class_quality.vtt import parse_vtt_text


class FakeOllamaClient:
    def __init__(self):
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "message": {
                "content": json.dumps(
                    {
                        "events": [
                            {
                                "dimension": "rapport",
                                "kind": "rapport_exchange",
                                "start_sec": 0,
                                "end_sec": 3,
                                "evidence_quote": "Hello class",
                                "observation": "The transcript shows a welcome exchange.",
                            }
                        ]
                    }
                )
            }
        }


def test_ollama_extractor_uses_full_transcript_and_fixed_settings():
    client = FakeOllamaClient()
    segments = parse_vtt_text("WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nHello class\n")
    events = OllamaTranscriptExtractor(model="qwen-local", client=client).extract(segments)
    assert len(events) == 1
    assert len(client.calls) == 1
    assert "Hello class" in client.calls[0]["messages"][0]["content"]
    assert client.calls[0]["options"] == {"temperature": 0, "num_ctx": 32768, "num_predict": 2000}
