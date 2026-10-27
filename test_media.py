import base64
import os
import tempfile
import unittest

os.environ.setdefault("SECRET_KEY", "test-secret")

from app import create_app
from config import Config
from models import db


def data_url(mime, payload):
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime};base64,{encoded}"


class TestMedia(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_file.close()

        class TestConfig(Config):
            SECRET_KEY = "test-secret"
            TESTING = True
            EDITOR_SENHA = "resgate"
            MAX_FOTO_BYTES = 64
            MAX_VIDEO_BYTES = 128
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.db_file.name}"

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.token = self.client.post("/api/login", json={"senha": "resgate"}).json["token"]
        headers = {"Authorization": f"Bearer {self.token}"}
        response = self.client.post("/api/jabutis", json={"nome": "Yuki"}, headers=headers)
        self.jabuti_id = response.json["id"]

    def tearDown(self):
        with self.app.app_context():
            db.drop_all()
        os.unlink(self.db_file.name)

    def test_gallery_accepts_webm_and_exposes_type(self):
        media = data_url("video/webm", b"\x1a\x45\xdf\xa3" + b"\x00" * 8)
        response = self.client.post(
            f"/api/jabutis/{self.jabuti_id}/fotos",
            json={"foto": media},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["tipo"], "video/webm")
        self.assertEqual(response.json["media_type"], "video/webm")

    def test_rejects_mismatched_signature(self):
        media = data_url("image/png", b"\xff\xd8\xff" + b"\x00" * 8)
        response = self.client.patch(
            f"/api/jabutis/{self.jabuti_id}",
            json={"foto": media},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_enforces_decoded_photo_limit(self):
        media = data_url("image/jpeg", b"\xff\xd8\xff" + b"x" * 64)
        response = self.client.patch(
            f"/api/jabutis/{self.jabuti_id}",
            json={"foto": media},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_video_in_legacy_pet_photo(self):
        media = data_url("video/mp4", b"\x00\x00\x00\x18ftypisom" + b"\x00" * 8)
        response = self.client.patch(
            f"/api/jabutis/{self.jabuti_id}",
            json={"foto": media},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_record_accepts_video(self):
        media = data_url("video/mp4", b"\x00\x00\x00\x18ftypisom" + b"\x00" * 8)
        response = self.client.post(
            f"/api/jabutis/{self.jabuti_id}/registros",
            json={"foto": media},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["foto_tipo"], "video/mp4")

    def test_updates_gallery_caption_without_changing_media_or_date(self):
        media = data_url("video/webm", b"\x1a\x45\xdf\xa3" + b"\x00" * 8)
        headers = {"Authorization": f"Bearer {self.token}"}
        created = self.client.post(
            f"/api/jabutis/{self.jabuti_id}/fotos",
            json={"foto": media, "legenda": "antes", "data": "2026-01-02"},
            headers=headers,
        ).json

        response = self.client.patch(
            f"/api/fotos/{created['id']}",
            json={"caption": "depois"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["legenda"], "depois")
        self.assertEqual(response.json["foto"], media)
        self.assertEqual(response.json["tipo"], "video/webm")
        self.assertEqual(response.json["data"], "2026-01-02")

    def test_gallery_caption_update_requires_authentication_and_caption(self):
        media = data_url("video/webm", b"\x1a\x45\xdf\xa3" + b"\x00" * 8)
        headers = {"Authorization": f"Bearer {self.token}"}
        created = self.client.post(
            f"/api/jabutis/{self.jabuti_id}/fotos",
            json={"foto": media},
            headers=headers,
        ).json

        unauthorized = self.client.patch(
            f"/api/fotos/{created['id']}", json={"legenda": "novo"}
        )
        missing_caption = self.client.patch(
            f"/api/fotos/{created['id']}", json={}, headers=headers
        )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(missing_caption.status_code, 400)


if __name__ == "__main__":
    unittest.main()
