import os
import json
import shutil
import subprocess
from typing import Dict, Any, List, Optional

class VideoAudioIngestor:
    """
    Tier 5 Knowledge Engine: Video Keyframe Extraction & Audio Transcription Pipeline.
    
    Features:
    - Slices field demonstration videos using local ffmpeg.
    - Extracts visual keyframes into the Visual Atlas directory.
    - Indexes timestamped demonstration techniques for physical farmer guidance.
    """

    _sources_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "sources", "demonstrations", "field_demonstration_catalog.json"
    )
    _legacy_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "books", "demonstrations", "field_demonstration_catalog.json"
    )
    DEFAULT_CATALOG = _sources_path if os.path.exists(_sources_path) else _legacy_path

    def __init__(self, catalog_file: Optional[str] = None):
        self.catalog_file = catalog_file or self.DEFAULT_CATALOG
        self.demonstrations: List[Dict[str, Any]] = self._load_catalog()
        self.ffmpeg_path = self._detect_ffmpeg()

    def _detect_ffmpeg(self) -> Optional[str]:
        # Check environment or scoop shims
        found = shutil.which("ffmpeg")
        if found:
            return found
        default_scoop = r"C:\Users\ankus\scoop\shims\ffmpeg.exe"
        if os.path.exists(default_scoop):
            return default_scoop
        return None

    def _load_catalog(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.catalog_file):
            return []
        try:
            with open(self.catalog_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def find_demonstration(
        self,
        crop: Optional[str] = None,
        disease: Optional[str] = None,
        query: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves a verified field video demonstration with timestamp and frame plate.
        """
        q_lower = query.lower()
        c_lower = crop.lower() if crop else ""
        d_lower = disease.lower() if disease else ""

        for d in self.demonstrations:
            t_crop = d.get("crop", "").lower()
            t_dis = d.get("disease", "").lower()

            crop_match = (t_crop and t_crop in q_lower) or (c_lower and t_crop in c_lower)
            disease_match = (t_dis and t_dis in q_lower) or (d_lower and t_dis in d_lower)

            if crop_match and disease_match:
                return d

        if d_lower:
            for d in self.demonstrations:
                if d.get("disease", "").lower() in d_lower:
                    return d

        return None

    def extract_keyframes_from_video(
        self,
        video_path: str,
        output_dir: str,
        interval_seconds: int = 5
    ) -> List[str]:
        """
        Uses ffmpeg to sample keyframes from a video file into output_dir.
        """
        if not self.ffmpeg_path or not os.path.exists(video_path):
            return []

        os.makedirs(output_dir, exist_ok=True)
        out_pattern = os.path.join(output_dir, "frame_%04d.jpg")
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video_path,
            "-vf", f"fps=1/{interval_seconds}",
            "-q:v", "2",
            out_pattern
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            frames = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith("frame_") and f.endswith(".jpg")]
            return sorted(frames)
        except Exception:
            return []
