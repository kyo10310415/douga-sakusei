"""Offline security dependency smoke checks (no DB, broker, or cloud services)."""
import io
import unittest
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.testclient import TestClient


class DependencyCompatibilityTests(unittest.TestCase):
    def test_patched_multipart_form_and_upload(self):
        app = FastAPI()
        @app.post('/upload')
        async def upload(name: str = Form(...), file: UploadFile = File(...)):
            return {'name': name, 'content': (await file.read()).decode()}
        with TestClient(app) as client:
            response = client.post('/upload', data={'name': 'test'}, files={'file': ('test.txt', b'synthetic', 'text/plain')})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {'name': 'test', 'content': 'synthetic'})

    def test_jwt_and_encryption_round_trip(self):
        from app.core.security import create_access_token, decode_access_token, encrypt_token, decrypt_token
        token = create_access_token({'sub': 'synthetic-user'})
        self.assertEqual(decode_access_token(token)['sub'], 'synthetic-user')
        self.assertIsNone(decode_access_token(token + 'corrupt'))
        self.assertEqual(decrypt_token(encrypt_token('synthetic-secret')), 'synthetic-secret')

    def test_pillow_placeholder_round_trip(self):
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (64, 64), 'white')
        ImageDraw.Draw(image).text((2, 2), 'test', fill='black')
        output = io.BytesIO()
        image.save(output, format='PNG')
        output.seek(0)
        with Image.open(output) as result:
            result.load()
            self.assertEqual(result.size, (64, 64))
