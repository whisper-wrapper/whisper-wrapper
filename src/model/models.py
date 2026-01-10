"""Data structures for transcription results."""

from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    language: str
    language_probability: float
    duration: float
