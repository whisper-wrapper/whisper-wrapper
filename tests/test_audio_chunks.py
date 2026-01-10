import numpy as np

from src.audio.chunks import emit_chunk_if_ready


def test_emit_chunk_if_ready_respects_interval():
    buffers = [np.zeros(100, dtype=np.float32)]
    emitted = []

    last_time, last_index = emit_chunk_if_ready(
        buffers=buffers,
        last_time=1.0,
        last_index=0,
        current_time=1.5,
        chunk_interval=1.0,
        sample_rate=16000,
        on_audio_chunk=lambda chunk: emitted.append(chunk),
    )

    assert emitted == []
    assert last_time == 1.0
    assert last_index == 0


def test_emit_chunk_if_ready_requires_samples():
    buffers = [np.zeros(100, dtype=np.float32)]
    emitted = []

    last_time, last_index = emit_chunk_if_ready(
        buffers=buffers,
        last_time=0.0,
        last_index=0,
        current_time=2.0,
        chunk_interval=1.0,
        sample_rate=16000,
        on_audio_chunk=lambda chunk: emitted.append(chunk),
    )

    assert emitted == []
    assert last_time == 0.0
    assert last_index == 0


def test_emit_chunk_if_ready_emits_concatenated_audio():
    buffers = [
        np.ones(16000, dtype=np.float32),
        np.ones(16000, dtype=np.float32) * 2.0,
    ]
    emitted = []

    last_time, last_index = emit_chunk_if_ready(
        buffers=buffers,
        last_time=0.0,
        last_index=0,
        current_time=2.5,
        chunk_interval=1.0,
        sample_rate=16000,
        on_audio_chunk=lambda chunk: emitted.append(chunk),
    )

    assert len(emitted) == 1
    assert emitted[0].shape[0] == 32000
    assert emitted[0][0] == 1.0
    assert emitted[0][16000] == 2.0
    assert last_time == 2.5
    assert last_index == 32000

    buffers[0][0] = 9.0
    assert emitted[0][0] == 1.0
