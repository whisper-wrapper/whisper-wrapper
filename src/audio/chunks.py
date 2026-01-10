"""Utilities for emitting audio chunks during recording."""

from typing import List, Tuple

import numpy as np


def emit_chunk_if_ready(
    buffers: List[np.ndarray],
    last_time: float,
    last_index: int,
    current_time: float,
    chunk_interval: float,
    sample_rate: int,
    on_audio_chunk,
) -> Tuple[float, int]:
    """
    Emit concatenated audio if enough time and samples have accumulated.

    Returns updated (last_time, last_index).
    """
    if current_time - last_time < chunk_interval:
        return last_time, last_index

    total_samples = sum(len(buf) for buf in buffers)
    if total_samples <= last_index + sample_rate:
        return last_time, last_index

    all_audio = np.concatenate(buffers)
    on_audio_chunk(all_audio.copy())
    return current_time, len(all_audio)
