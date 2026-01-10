"""Device detection for Whisper model execution."""

from typing import Tuple

from ..logging_utils import get_logger

logger = get_logger("transcriber.device")


def detect_device(preferred: str) -> Tuple[str, str]:
    if preferred == "cpu":
        return "cpu", "int8"

    if preferred in ("auto", "cuda"):
        try:
            import torch

            if torch.cuda.is_available():
                logger.info(f"CUDA via PyTorch: {torch.cuda.get_device_name(0)}")
                return "cuda", "float16"
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"PyTorch CUDA check failed: {e}")

        try:
            import ctranslate2

            cuda_types = ctranslate2.get_supported_compute_types("cuda")
            if cuda_types:
                compute_type = "float16" if "float16" in cuda_types else "int8"
                logger.info(f"CUDA via CTranslate2: {cuda_types}")
                return "cuda", compute_type
        except Exception as e:
            logger.debug(f"CTranslate2 CUDA check failed: {e}")

    logger.info("Using CPU with int8 quantization")
    return "cpu", "int8"
