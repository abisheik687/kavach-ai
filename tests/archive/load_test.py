from locust import HttpUser, task, between
import base64
import random
import io
from PIL import Image
import numpy as np


class KavachLoadTester(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Prepare a fake base64 face image payload."""
        test_img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        pil = Image.fromarray(test_img)
        buf = io.BytesIO()
        pil.save(buf, format="JPEG")
        self.b64_image = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    @task(3)
    def scan_image(self):
        """Hit the synchronous scan endpoint with an image."""
        payload = {
            "source_url": f"https://example.com/simulated_{random.randint(1000, 9999)}.jpg",
            "base64_data": self.b64_image,
            "source_type": "url"
        }
        with self.client.post("/api/scan/image", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status: {response.status_code}")

    @task(1)
    def health_check(self):
        self.client.get("/health")

