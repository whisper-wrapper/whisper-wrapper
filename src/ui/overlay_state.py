"""Overlay state definitions."""

from enum import Enum, auto


class OverlayState(Enum):
    HIDDEN = auto()
    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()
    TRANSCRIBING = auto()
    DOWNLOADING = auto()
    ERROR = auto()
    SUCCESS = auto()


STATE_LABELS = {
    OverlayState.HIDDEN: "",
    OverlayState.IDLE: "Idle",
    OverlayState.RECORDING: "Recording...",
    OverlayState.PROCESSING: "Processing...",
    OverlayState.TRANSCRIBING: "Transcribing...",
    OverlayState.DOWNLOADING: "Loading model...",
    OverlayState.ERROR: "Error",
    OverlayState.SUCCESS: "Done",
}
