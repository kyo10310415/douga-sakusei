"""
TTS (Text-to-Speech) サービス - 差し替え可能な設計
"""
import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.core.config import settings


class BaseTTSService(ABC):
    @abstractmethod
    async def generate_voice(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speech_rate: float = 1.0,
        pitch: float = 0.0,
        emotion_strength: float = 0.7,
        output_path: str = "",
    ) -> Dict[str, Any]:
        """
        Returns:
            dict with keys: file_path, duration_seconds, success, error
        """
        pass


class MockTTSService(BaseTTSService):
    """開発・テスト用モックTTSサービス（無音 or サンプル音声）"""

    async def generate_voice(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speech_rate: float = 1.0,
        pitch: float = 0.0,
        emotion_strength: float = 0.7,
        output_path: str = "",
    ) -> Dict[str, Any]:
        # 無音のWAVファイルを生成（文字数 × 0.1秒）
        duration = max(1.0, len(text) * 0.1 / speech_rate)

        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # 無音WAVヘッダー生成
            import struct
            import wave
            sample_rate = 22050
            num_samples = int(sample_rate * duration)
            with wave.open(output_path, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b'\x00\x00' * num_samples)

        return {
            "file_path": output_path,
            "duration_seconds": duration,
            "success": True,
            "provider": "mock",
        }


class OpenAITTSService(BaseTTSService):
    """OpenAI TTS API"""

    def __init__(self):
        import openai
        self.client = openai.AsyncOpenAI(api_key=settings.TTS_API_KEY or settings.OPENAI_API_KEY)

    async def generate_voice(
        self,
        text: str,
        voice_id: Optional[str] = "nova",
        speech_rate: float = 1.0,
        pitch: float = 0.0,
        emotion_strength: float = 0.7,
        output_path: str = "",
    ) -> Dict[str, Any]:
        try:
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=voice_id or "nova",
                input=text,
                speed=speech_rate,
            )
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                response.stream_to_file(output_path)

            # 推定duration（文字数ベース）
            duration = len(text) * 0.08 / speech_rate
            return {
                "file_path": output_path,
                "duration_seconds": duration,
                "success": True,
                "provider": "openai",
            }
        except Exception as e:
            return {
                "file_path": None,
                "duration_seconds": 0,
                "success": False,
                "error": str(e),
                "provider": "openai",
            }


class ElevenLabsTTSService(BaseTTSService):
    """ElevenLabs TTS API"""

    def __init__(self):
        import httpx
        self.api_key = settings.TTS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"

    async def generate_voice(
        self,
        text: str,
        voice_id: Optional[str] = "21m00Tcm4TlvDq8ikWAM",
        speech_rate: float = 1.0,
        pitch: float = 0.0,
        emotion_strength: float = 0.7,
        output_path: str = "",
    ) -> Dict[str, Any]:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    headers={"xi-api-key": self.api_key},
                    json={
                        "text": text,
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": emotion_strength,
                            "speed": speech_rate,
                        },
                    },
                    timeout=60,
                )
                if response.status_code == 200:
                    if output_path:
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                    duration = len(text) * 0.08 / speech_rate
                    return {
                        "file_path": output_path,
                        "duration_seconds": duration,
                        "success": True,
                        "provider": "elevenlabs",
                    }
                else:
                    return {
                        "file_path": None,
                        "duration_seconds": 0,
                        "success": False,
                        "error": f"ElevenLabs API error: {response.status_code}",
                        "provider": "elevenlabs",
                    }
        except Exception as e:
            return {
                "file_path": None,
                "duration_seconds": 0,
                "success": False,
                "error": str(e),
                "provider": "elevenlabs",
            }


class VoicevoxTTSService(BaseTTSService):
    """VOICEVOX TTS (ローカルまたはAPI)"""

    def __init__(self):
        self.base_url = settings.VOICEVOX_URL

    async def generate_voice(
        self,
        text: str,
        voice_id: Optional[str] = "1",  # Speaker ID
        speech_rate: float = 1.0,
        pitch: float = 0.0,
        emotion_strength: float = 0.7,
        output_path: str = "",
    ) -> Dict[str, Any]:
        import httpx
        try:
            speaker_id = int(voice_id) if voice_id and voice_id.isdigit() else 1
            async with httpx.AsyncClient() as client:
                # 音声合成クエリ生成
                query_response = await client.post(
                    f"{self.base_url}/audio_query",
                    params={"text": text, "speaker": speaker_id},
                    timeout=30,
                )
                if query_response.status_code != 200:
                    raise Exception(f"VOICEVOX query error: {query_response.status_code}")

                query = query_response.json()
                query["speedScale"] = speech_rate
                query["pitchScale"] = pitch
                query["intonationScale"] = emotion_strength

                # 音声生成
                synthesis_response = await client.post(
                    f"{self.base_url}/synthesis",
                    params={"speaker": speaker_id},
                    json=query,
                    timeout=60,
                )
                if synthesis_response.status_code == 200:
                    if output_path:
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, "wb") as f:
                            f.write(synthesis_response.content)
                    duration = len(text) * 0.08 / speech_rate
                    return {
                        "file_path": output_path,
                        "duration_seconds": duration,
                        "success": True,
                        "provider": "voicevox",
                    }
                raise Exception(f"VOICEVOX synthesis error: {synthesis_response.status_code}")
        except Exception as e:
            return {
                "file_path": None,
                "duration_seconds": 0,
                "success": False,
                "error": str(e),
                "provider": "voicevox",
            }


def get_tts_service() -> BaseTTSService:
    """環境設定に基づいてTTSサービスを返す"""
    provider = settings.TTS_PROVIDER.lower()
    if provider == "openai":
        return OpenAITTSService()
    elif provider == "elevenlabs":
        return ElevenLabsTTSService()
    elif provider == "voicevox":
        return VoicevoxTTSService()
    return MockTTSService()
