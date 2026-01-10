from src.ui.overlay_state import OverlayState, STATE_LABELS


def test_overlay_state_labels_complete():
    assert set(STATE_LABELS.keys()) == set(OverlayState)
