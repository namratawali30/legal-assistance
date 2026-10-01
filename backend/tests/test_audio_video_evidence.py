import hashlib
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from app.core.evidence_validation import (
    EvidenceSignatureError,
    validate_file_signature,
)
from app.core.evidence_policy import determine_evidence_type
from app.services.transcription_service import (
    extract_audio_from_video,
    transcribe_audio,
)
from app.services.evidence_text_extraction_service import (
    extract_evidence_text,
)


def test_audio_video_evidence_types():
    assert determine_evidence_type(".mp3") == "audio"
    assert determine_evidence_type(".wav") == "audio"
    assert determine_evidence_type(".m4a") == "audio"
    assert determine_evidence_type(".mp4") == "video"
    assert determine_evidence_type(".webm") == "video"
    assert determine_evidence_type(".pdf") == "document"
    assert determine_evidence_type(".jpg") == "image"


def test_mp3_signature_validation(tmp_path):
    # Valid ID3 MP3 mock
    valid_mp3 = tmp_path / "valid.mp3"
    valid_mp3.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x00Header mock audio data")
    validate_file_signature(valid_mp3, ".mp3")  # Should pass

    # Fake MP3 (EXE header)
    fake_mp3 = tmp_path / "fake.mp3"
    fake_mp3.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00Executable binary data")
    with pytest.raises(EvidenceSignatureError):
        validate_file_signature(fake_mp3, ".mp3")


def test_wav_signature_validation(tmp_path):
    valid_wav = tmp_path / "test.wav"
    valid_wav.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00")
    validate_file_signature(valid_wav, ".wav")  # Should pass

    fake_wav = tmp_path / "fake.wav"
    fake_wav.write_bytes(b"<html><body>Not a wav</body></html>")
    with pytest.raises(EvidenceSignatureError):
        validate_file_signature(fake_wav, ".wav")


def test_bmff_mp4_m4a_signature_validation(tmp_path):
    valid_mp4 = tmp_path / "test.mp4"
    valid_mp4.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41")
    validate_file_signature(valid_mp4, ".mp4")
    validate_file_signature(valid_mp4, ".m4a")

    fake_mp4 = tmp_path / "fake.mp4"
    fake_mp4.write_bytes(b"PK\x03\x04ZipArchiveData")
    with pytest.raises(EvidenceSignatureError):
        validate_file_signature(fake_mp4, ".mp4")


def test_webm_signature_validation(tmp_path):
    valid_webm = tmp_path / "test.webm"
    valid_webm.write_bytes(b"\x1A\x45\xDF\xA3\x99\x42\x86\x81\x01\x42\xF7\x81\x01")
    validate_file_signature(valid_webm, ".webm")

    fake_webm = tmp_path / "fake.webm"
    fake_webm.write_bytes(b"NOT WEBM DATA")
    with pytest.raises(EvidenceSignatureError):
        validate_file_signature(fake_webm, ".webm")


def test_transcribe_audio_success(tmp_path):
    audio_file = tmp_path / "speech.wav"
    audio_file.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00Sample speech audio content bytes")
    res = transcribe_audio(audio_file)
    assert res["status"] == "ready"
    assert res["transcript"] is not None
    assert res["character_count"] > 0
    assert res["sha256"] is not None


def test_transcribe_audio_no_speech(tmp_path):
    silent_audio = tmp_path / "silent.wav"
    silent_audio.write_bytes(b"no_speech_marker_audio_content")
    res = transcribe_audio(silent_audio)
    assert res["status"] == "no_text"
    assert res["transcript"] is None


def test_extract_evidence_text_audio(tmp_path):
    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x00Sample MP3 recording content")
    sha256 = hashlib.sha256(audio_path.read_bytes()).hexdigest()

    evidence = {
        "storage_path": f"evidence/user1/{audio_path.name}",
        "file_extension": ".mp3",
        "size_bytes": audio_path.stat().st_size,
        "sha256": sha256,
    }

    with patch("app.services.evidence_text_extraction_service.resolve_storage_path", return_value=audio_path), \
         patch("app.services.evidence_text_extraction_service.calculate_file_sha256", return_value=sha256):
        res = extract_evidence_text(evidence)
        assert res["status"] == "ready"
        assert res["method"] == "audio_transcription"
        assert len(res["text"]) > 0


def test_extract_evidence_text_video(tmp_path):
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41Sample MP4 content")
    sha256 = hashlib.sha256(video_path.read_bytes()).hexdigest()

    evidence = {
        "storage_path": f"evidence/user1/{video_path.name}",
        "file_extension": ".mp4",
        "size_bytes": video_path.stat().st_size,
        "sha256": sha256,
    }

    # Mock audio extraction to succeed
    def mock_extract(v_path, out_path):
        out_path.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00Extracted WAV audio content")
        return True

    with patch("app.services.evidence_text_extraction_service.resolve_storage_path", return_value=video_path), \
         patch("app.services.evidence_text_extraction_service.calculate_file_sha256", return_value=sha256), \
         patch("app.services.transcription_service.extract_audio_from_video", side_effect=mock_extract):
        res = extract_evidence_text(evidence)
        assert res["status"] == "ready"
        assert res["method"] == "video_audio_transcription"
        assert len(res["text"]) > 0
        # Verify original video hash remains unchanged
        assert hashlib.sha256(video_path.read_bytes()).hexdigest() == sha256


def test_requires_ocr_image_behavior_unchanged(tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00")
    sha256 = hashlib.sha256(img_path.read_bytes()).hexdigest()

    evidence = {
        "storage_path": f"evidence/user1/{img_path.name}",
        "file_extension": ".jpg",
        "size_bytes": img_path.stat().st_size,
        "sha256": sha256,
    }

    with patch("app.services.evidence_text_extraction_service.resolve_storage_path", return_value=img_path), \
         patch("app.services.evidence_text_extraction_service.calculate_file_sha256", return_value=sha256):
        res = extract_evidence_text(evidence)
        assert res["status"] == "requires_ocr"
