import pytest
import numpy as np
from backend.detection.syncnet import SyncNet


def test_syncnet_perfect_correlation():
    syncnet = SyncNet(device="cpu")
    emb = np.random.randn(10, 128)
    score = syncnet.calculate_sync_score(emb, emb)
    assert score >= 0.9


def test_syncnet_no_correlation():
    syncnet = SyncNet(device="cpu")
    emb1 = np.random.randn(10, 128)
    emb2 = np.random.randn(10, 128)
    score = syncnet.calculate_sync_score(emb1, emb2)
    assert 0.3 <= score <= 0.7


def test_syncnet_offset_detection():
    syncnet = SyncNet(device="cpu")
    emb = np.random.randn(30, 128)
    audio_emb = np.roll(emb, 5, axis=0)
    offset, score = syncnet.detect_offset(emb, audio_emb, max_offset=10)
    assert offset == 5

