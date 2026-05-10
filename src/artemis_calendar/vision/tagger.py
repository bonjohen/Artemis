"""Image tagging using vision-language models (Qwen2.5-VL or mock for testing)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from artemis_calendar.config.settings import RAW_ROOT
from artemis_calendar.observe.logging import get_logger
from artemis_calendar.vision.attributes import AttributeVocabulary

logger = get_logger("artemis.vision.tagger")

THUMB_DIR = RAW_ROOT / "images" / "thumbs"

# Prompt template for structured attribute extraction
ATTRIBUTE_PROMPT = """\
You are analyzing an image from the NASA Artemis II mission photo collection.

Identify which of the following attributes are present in this image.
For each attribute, provide a confidence score between 0.0 and 1.0.

Attributes to check:
{attribute_list}

Respond ONLY with a JSON object mapping attribute codes to confidence scores.
Only include attributes with confidence > 0.05.
Example: {{"earth": 0.95, "moon": 0.88, "deep_space": 0.92}}
"""


def _build_prompt(vocab: AttributeVocabulary) -> str:
    """Build the tagging prompt from the attribute vocabulary."""
    lines = []
    for attr in vocab.base_attributes:
        lines.append(f"- {attr.code}: {attr.description}")
    return ATTRIBUTE_PROMPT.format(attribute_list="\n".join(lines))


def _parse_model_output(text: str, vocab: AttributeVocabulary) -> dict[str, float]:
    """Parse model text output into attribute confidence dict.

    Handles JSON wrapped in markdown code blocks or raw JSON.
    """
    # Strip markdown code block if present
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        # Try to find a JSON object directly
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to parse model output as JSON: {text[:200]}")
        return {}

    # Validate and filter to known base attributes
    result = {}
    for code, score in data.items():
        if code not in vocab.base_codes:
            continue
        try:
            score = float(score)
            if 0.0 <= score <= 1.0:
                result[code] = round(score, 4)
        except (ValueError, TypeError):
            continue
    return result


class VisionTagger:
    """Tag images with structured attributes using a vision-language model."""

    def __init__(
        self,
        vocab: AttributeVocabulary,
        model_name: str = "qwen2.5-vl-7b",
        model_version: str = "Qwen/Qwen2.5-VL-7B-Instruct",
        device: str = "auto",
    ):
        self.vocab = vocab
        self.model_name = model_name
        self.model_version = model_version
        self.device = device
        self.prompt = _build_prompt(vocab)
        self._model = None
        self._processor = None

    def _load_model(self) -> None:
        """Load the VLM model and processor. Lazy-loaded on first use."""
        if self._model is not None:
            return

        try:
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

            logger.info(f"Loading {self.model_version}...")
            self._processor = AutoProcessor.from_pretrained(self.model_version)
            self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.model_version,
                torch_dtype="auto",
                device_map=self.device,
            )
            logger.info(f"Model loaded: {self.model_version}")
        except ImportError as e:
            raise RuntimeError("Qwen2.5-VL requires: pip install transformers torch qwen-vl-utils") from e
        except Exception as e:
            raise RuntimeError(f"Failed to load {self.model_version}: {e}") from e

    def tag_image(self, image_path: Path) -> dict[str, float]:
        """Tag a single image. Returns base attribute confidence dict."""
        self._load_model()

        from qwen_vl_utils import process_vision_info

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": str(image_path)},
                    {"type": "text", "text": self.prompt},
                ],
            }
        ]

        text_input = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self._processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(self._model.device)

        import torch

        with torch.no_grad():
            output_ids = self._model.generate(**inputs, max_new_tokens=512)

        # Decode only the new tokens
        generated = output_ids[0][inputs.input_ids.shape[1] :]
        text = self._processor.decode(generated, skip_special_tokens=True)

        return _parse_model_output(text, self.vocab)

    def tag_batch(self, image_paths: list[Path], progress_callback=None) -> list[dict[str, float]]:
        """Tag a batch of images sequentially.

        Returns list of confidence dicts in same order as input.
        """
        results = []
        for i, path in enumerate(image_paths):
            try:
                confidences = self.tag_image(path)
            except Exception:
                logger.exception(f"Failed to tag {path.name}")
                confidences = {}
            results.append(confidences)
            if progress_callback:
                progress_callback(i + 1, len(image_paths))
        return results


class MockTagger:
    """Deterministic mock tagger for testing — no model needed."""

    def __init__(self, vocab: AttributeVocabulary):
        self.vocab = vocab
        self.model_name = "mock-tagger"
        self.model_version = "mock-v1"

    def tag_image(self, image_path: Path) -> dict[str, float]:
        """Generate deterministic attributes from filename hash."""
        import hashlib

        h = hashlib.sha256(image_path.name.encode()).hexdigest()
        result = {}
        for i, attr in enumerate(self.vocab.base_attributes):
            # Use hash bytes to generate deterministic confidences
            byte_val = int(h[(i * 2) : (i * 2 + 2)], 16) / 255.0
            if byte_val > 0.05:
                result[attr.code] = round(byte_val, 4)
        return result

    def tag_batch(self, image_paths: list[Path], progress_callback=None) -> list[dict[str, float]]:
        results = []
        for i, path in enumerate(image_paths):
            results.append(self.tag_image(path))
            if progress_callback:
                progress_callback(i + 1, len(image_paths))
        return results
