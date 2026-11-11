"""Pillar 4: Visual Diagram-to-Equation Multimodal Solver (`DiagramToEquationSolver`).

Combines:
  1. `NeuralImageClassifier` (`physics_vision`) to identify the physical diagram topology
     (`series_circuit`, `parallel_circuit`, `inclined_plane`, `projectile_trajectory`,
      `carnot_pv_cycle`, `snell_refraction`, `quantum_energy_levels`),
  2. Windows Native WinRT OCR (`Windows.Media.Ocr.OcrEngine`) to read numerical labels
     ($R_1, R_2, V, m_1, m_2, \theta, v_0, f, d_o$) directly off the schematic image, and
  3. `UniversalFormulaSolver` / `SymbolicCASEngine` to solve the resulting system of equations.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional

from PIL import Image, ImageDraw, ImageFont

from ..experts import VisionExpert
from .cas_engine import SymbolicCASEngine

PS_SINGLE_IMAGE_OCR = r"""
param([string]$ImagePath)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

Function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$res = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
Write-Output $res.Text
$stream.Dispose()
"""

DIAGRAM_TOPOLOGY_HINTS: Dict[str, str] = {
    "series_circuit": "Resistors connected in series across voltage source.",
    "parallel_circuit": "Resistors connected in parallel across voltage source.",
    "inclined_plane": "Block on a frictionless inclined plane ramp.",
    "projectile_trajectory": "Projectile launched at initial speed and angle.",
    "carnot_pv_cycle": "Carnot heat engine operating between hot and cold reservoirs.",
    "snell_refraction": "Thin lens or optical refraction system.",
    "quantum_energy_levels": "Quantum transition and matter-wave system.",
}


class DiagramToEquationSolver:
    """End-to-end multimodal solver: Schematic Image -> Vision Topology + WinRT OCR Labels -> Symbolic CAS Solution."""

    _VISION_CACHE: Optional[VisionExpert] = None

    @classmethod
    def _get_vision_expert(cls) -> Optional[VisionExpert]:
        if cls._VISION_CACHE is None:
            try:
                cls._VISION_CACHE = VisionExpert()
            except Exception:
                return None
        return cls._VISION_CACHE

    @staticmethod
    def ocr_image_labels(image_path: str | Path) -> str:
        """Extract text & numeric labels from a physics diagram image using Windows Native WinRT OCR."""
        img_p = Path(image_path).resolve()
        if not img_p.is_file():
            return ""
        win_ps = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        if not Path(win_ps).is_file():
            return ""
        with tempfile.TemporaryDirectory() as tmp:
            ps_file = Path(tmp) / "ocr_single.ps1"
            ps_file.write_text(PS_SINGLE_IMAGE_OCR, encoding="utf-8")
            try:
                out = subprocess.check_output(
                    [win_ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_file), "-ImagePath", str(img_p)],
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=20,
                )
                return " ".join(out.split()).strip()
            except Exception:
                return ""

    @staticmethod
    def render_labeled_physics_diagram_png(
        output_path: str | Path,
        diagram_type: str = "inclined_plane",
        label_text: str = "",
        labels_text: str = "",
    ) -> Path:
        """Render a clean, high-contrast schematic diagram with large readable engineering labels for OCR + Vision."""
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (680, 260), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        txt_to_draw = (labels_text or label_text or "").replace("\n", "   ")

        # Draw characteristic schematic geometry for VisionExpert + clear text banner for OCR
        if "series" in diagram_type:
            draw.line([(40, 180), (640, 180)], fill=(20, 40, 160), width=4)
            draw.rectangle([140, 160, 240, 200], outline=(200, 40, 40), width=3)
            draw.rectangle([360, 160, 460, 200], outline=(200, 40, 40), width=3)
        elif "parallel" in diagram_type:
            draw.line([(60, 140), (60, 230)], fill=(20, 140, 60), width=4)
            draw.line([(600, 140), (600, 230)], fill=(20, 140, 60), width=4)
            draw.line([(60, 155), (600, 155)], fill=(20, 140, 60), width=3)
            draw.line([(60, 215), (600, 215)], fill=(20, 140, 60), width=3)
        elif "incline" in diagram_type:
            draw.polygon([(60, 230), (540, 230), (540, 120)], outline=(60, 60, 60), width=3)
            draw.rectangle([260, 150, 320, 195], outline=(180, 60, 20), width=3)
        else:
            draw.arc([60, 120, 580, 240], start=180, end=360, fill=(30, 100, 200), width=4)

        try:
            font = ImageFont.truetype("arial.ttf", 26)
        except Exception:
            font = ImageFont.load_default()

        draw.text((28, 36), txt_to_draw, fill=(0, 0, 0), font=font)
        img.save(str(out_p))
        return out_p

    @classmethod
    def solve_diagram(
        cls,
        image_path: str | Path,
        user_question: str = "",
        vision_expert: Optional[Any] = None,
        diagram_type_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Classify diagram topology via `physics_vision`, extract schematic labels via WinRT OCR, and solve via CAS."""
        vision = vision_expert or cls._get_vision_expert()
        vision_pred: Dict[str, Any] = {}
        diagram_class = diagram_type_override or "series_circuit"

        if vision is not None and Path(image_path).is_file():
            try:
                vision_pred = vision.evaluate({"image": str(image_path), "query": user_question, "vision_domain": "physics"})
                pred_cls = vision_pred.get("diagram_class") or vision_pred.get("predicted_class")
                if pred_cls and not diagram_type_override:
                    diagram_class = pred_cls
            except Exception:
                pass

        ocr_text = cls.ocr_image_labels(image_path)
        topology_hint = DIAGRAM_TOPOLOGY_HINTS.get(diagram_class, "")
        synthesized_query = " ".join(part for part in (topology_hint, ocr_text, user_question) if part).strip()

        solution = SymbolicCASEngine.solve_numerical_word_problem(synthesized_query) or {}
        if "final_value" in solution and "result" not in solution:
            solution["result"] = solution["final_value"]
        return {
            "solved": bool(solution.get("solved")) and solution.get("final_value") is not None,
            "diagram_class": diagram_class,
            "vision_prediction": vision_pred,
            "ocr_extracted_labels": ocr_text,
            "synthesized_physics_query": synthesized_query,
            "numerical_solution": solution,
        }
