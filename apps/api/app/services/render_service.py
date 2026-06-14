"""
キャラクターアニメーション + FFmpegレンダリングサービス
"""
import os
import subprocess
import json
import tempfile
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from app.core.config import settings


class BaseCharacterAnimationService(ABC):
    """将来的にLive2D、SadTalker、Wav2Lip、HeyGenなどに差し替え可能なインターフェース"""

    @abstractmethod
    async def generate_scene_video(
        self,
        character_image_path: str,
        audio_path: str,
        expression: str,
        background_path: Optional[str],
        subtitle: str,
        duration_seconds: float,
        output_path: str,
    ) -> Dict[str, Any]:
        pass


class FFmpegCharacterAnimationService(BaseCharacterAnimationService):
    """FFmpegによる疑似キャラクターアニメーション（MVP実装）"""

    async def generate_scene_video(
        self,
        character_image_path: str,
        audio_path: str,
        expression: str,
        background_path: Optional[str],
        subtitle: str,
        duration_seconds: float,
        output_path: str,
    ) -> Dict[str, Any]:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # キャラクター画像のパス解決
            if not character_image_path or not os.path.exists(character_image_path):
                character_image_path = self._get_default_character_image()

            if not background_path or not os.path.exists(background_path):
                background_path = self._get_default_background()

            # FFmpegコマンド構築
            cmd = self._build_ffmpeg_command(
                character_image_path=character_image_path,
                audio_path=audio_path,
                background_path=background_path,
                subtitle=subtitle,
                duration_seconds=duration_seconds,
                expression=expression,
                output_path=output_path,
            )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "output_path": output_path,
                    "duration_seconds": duration_seconds,
                    "provider": "ffmpeg",
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "provider": "ffmpeg",
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "FFmpeg タイムアウト", "provider": "ffmpeg"}
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "ffmpeg"}

    def _build_ffmpeg_command(
        self,
        character_image_path: str,
        audio_path: str,
        background_path: str,
        subtitle: str,
        duration_seconds: float,
        expression: str,
        output_path: str,
    ) -> List[str]:
        """FFmpegコマンドを構築する"""
        # 表情によるズーム量の変化
        zoom_map = {
            "normal": "1.0",
            "smile": "1.02",
            "surprise": "1.05",
            "troubled": "1.01",
            "serious": "1.0",
        }
        zoom = zoom_map.get(expression, "1.0")

        # フィルターグラフの構築
        # 1. 背景をスケール
        # 2. キャラクター画像をオーバーレイ（口パク疑似演出: sin波でY軸移動）
        # 3. 字幕テロップを追加
        filter_complex = (
            f"[0:v]scale=1920:1080,setsar=1[bg];"
            f"[1:v]scale=800:-1,setsar=1[char_raw];"
            f"[char_raw]zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration_seconds*25)}:s=800x900:fps=25[char_zoomed];"
            f"[bg][char_zoomed]overlay=x=560:y=100[with_char];"
        )

        # 字幕がある場合は追加
        if subtitle and subtitle.strip():
            safe_subtitle = subtitle.replace("'", "\\'").replace(":", "\\:")[:50]
            filter_complex += (
                f"[with_char]drawtext="
                f"fontsize=36:"
                f"fontcolor=white:"
                f"borderw=3:"
                f"bordercolor=black:"
                f"x=(w-tw)/2:"
                f"y=h-th-50:"
                f"text='{safe_subtitle}'[out]"
            )
        else:
            filter_complex += "[with_char]copy[out]"

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", background_path,
            "-loop", "1", "-i", character_image_path,
        ]

        # 音声ファイルがある場合
        if audio_path and os.path.exists(audio_path):
            cmd.extend(["-i", audio_path])
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-map", "2:a",
                "-t", str(duration_seconds),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-r", "25",
                "-b:v", "2M",
                output_path,
            ])
        else:
            cmd.extend([
                "-filter_complex", filter_complex.replace("[with_char]", "[with_char]").replace("[out]", "[out]"),
                "-map", "[out]",
                "-t", str(duration_seconds),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", "25",
                "-b:v", "2M",
                output_path,
            ])

        return cmd

    def _get_default_character_image(self) -> str:
        """デフォルトキャラクター画像を生成または取得"""
        path = os.path.join(settings.UPLOAD_DIR, "defaults", "character_default.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            self._create_placeholder_image(path, 800, 900, color="pink", text="VTuber")
        return path

    def _get_default_background(self) -> str:
        """デフォルト背景画像を生成"""
        path = os.path.join(settings.UPLOAD_DIR, "defaults", "background_default.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            self._create_placeholder_image(path, 1920, 1080, color="navy", text="")
        return path

    def _create_placeholder_image(self, path: str, width: int, height: int, color: str, text: str):
        """PILでプレースホルダー画像を生成"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            color_map = {
                "pink": (255, 182, 193),
                "navy": (25, 25, 112),
                "gray": (128, 128, 128),
            }
            bg_color = color_map.get(color, (128, 128, 128))
            img = Image.new("RGB", (width, height), bg_color)
            if text:
                draw = ImageDraw.Draw(img)
                draw.text((width//2 - 50, height//2), text, fill=(255, 255, 255))
            img.save(path)
        except Exception:
            # PILが使えない場合はFFmpegでプレースホルダー生成
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"color=c=navy:size={width}x{height}:duration=1",
                "-frames:v", "1", path
            ], capture_output=True)


class RenderService:
    """動画全体のレンダリングサービス"""

    def __init__(self):
        self.animation_service = FFmpegCharacterAnimationService()

    async def render_full_video(
        self,
        sections_data: List[Dict[str, Any]],
        output_path: str,
        bgm_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """複数シーンを結合して完全な動画を生成"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        scene_paths = []
        render_log = []

        for i, section in enumerate(sections_data):
            scene_output = output_path.replace(".mp4", f"_scene_{i:03d}.mp4")
            render_log.append(f"[シーン{i+1}] {section.get('title', '')} 開始")

            result = await self.animation_service.generate_scene_video(
                character_image_path=section.get("character_image_path", ""),
                audio_path=section.get("audio_path", ""),
                expression=section.get("expression", "normal"),
                background_path=section.get("background_path", ""),
                subtitle=section.get("subtitle", ""),
                duration_seconds=section.get("duration_seconds", 30),
                output_path=scene_output,
            )

            if result["success"]:
                scene_paths.append(scene_output)
                render_log.append(f"[シーン{i+1}] 完了")
            else:
                render_log.append(f"[シーン{i+1}] 失敗: {result.get('error')}")
                # 失敗シーンはスキップして続行

        if not scene_paths:
            return {
                "success": False,
                "error": "レンダリング可能なシーンがありません",
                "render_log": "\n".join(render_log),
            }

        # シーンを結合
        concat_result = await self._concatenate_scenes(scene_paths, output_path, bgm_path)
        render_log.append(f"結合{'完了' if concat_result['success'] else '失敗'}")

        # 一時ファイルを削除
        for path in scene_paths:
            try:
                os.remove(path)
            except Exception:
                pass

        return {
            "success": concat_result["success"],
            "output_path": output_path if concat_result["success"] else None,
            "render_log": "\n".join(render_log),
            "error": concat_result.get("error"),
        }

    async def _concatenate_scenes(
        self,
        scene_paths: List[str],
        output_path: str,
        bgm_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """FFmpegでシーンを結合"""
        if len(scene_paths) == 1:
            # 1シーンのみの場合はそのままコピー
            import shutil
            shutil.copy(scene_paths[0], output_path)
            return {"success": True}

        # concat リストファイル作成
        concat_list_path = output_path + ".txt"
        with open(concat_list_path, "w") as f:
            for path in scene_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            output_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            os.remove(concat_list_path)

            if result.returncode == 0:
                # BGMを追加
                if bgm_path and os.path.exists(bgm_path):
                    await self._add_bgm(output_path, bgm_path)
                return {"success": True}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _add_bgm(self, video_path: str, bgm_path: str) -> bool:
        """BGMをミックス"""
        temp_path = video_path + ".tmp.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", bgm_path,
            "-filter_complex",
            "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2:weights=1 0.3[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            temp_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            import shutil
            shutil.move(temp_path, video_path)
            return True
        return False

    async def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        timestamp_seconds: float = 5.0,
    ) -> Dict[str, Any]:
        """動画からサムネイルを生成"""
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp_seconds),
            "-i", video_path,
            "-frames:v", "1",
            "-vf", "scale=1280:720",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return {
            "success": result.returncode == 0,
            "output_path": output_path,
            "error": result.stderr if result.returncode != 0 else None,
        }


def get_animation_service() -> BaseCharacterAnimationService:
    """将来的に外部APIに差し替えられるファクトリー関数"""
    provider = settings.VIDEO_GENERATION_PROVIDER.lower()
    # 将来: if provider == "heygen": return HeyGenService()
    # 将来: if provider == "did": return DIDService()
    # 将来: if provider == "sadtalker": return SadTalkerService()
    return FFmpegCharacterAnimationService()
