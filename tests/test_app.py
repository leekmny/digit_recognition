"""Offline inference and local HTTP regression tests."""
import base64
import http.client
import io
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

import numpy as np
from PIL import Image, ImageDraw

from shared.engine import Recognizer, normalize
from web_version.server import Handler


def drawing(offset=0):
    image = Image.new('RGB', (336, 336), 'white')
    ImageDraw.Draw(image).line(
        [(160 + offset, 70), (160 + offset, 260)], fill='#111111', width=22
    )
    return image


def image_data(image, kind='PNG'):
    with io.BytesIO() as buffer:
        image.save(buffer, format=kind)
        return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = Recognizer()

    def test_blank_drawing_is_rejected(self):
        with self.assertRaises(ValueError):
            self.model.predict(Image.new('RGB', (336, 336), 'white'))

    def test_normalization_centers_and_scales_ink(self):
        pixels = normalize(drawing())
        self.assertEqual(pixels.shape, (28, 28))
        self.assertTrue(np.isfinite(pixels).all())
        self.assertGreater(pixels.max(), 0.5)
        self.assertGreaterEqual(pixels.min(), 0)
        self.assertLessEqual(pixels.max(), 1)
        yy, xx = np.indices(pixels.shape)
        self.assertAlmostEqual(float((xx * pixels).sum() / pixels.sum()), 13.5, delta=0.6)
        self.assertAlmostEqual(float((yy * pixels).sum() / pixels.sum()), 13.5, delta=0.6)

    def test_moving_digit_keeps_normalized_input(self):
        np.testing.assert_array_equal(normalize(drawing()), normalize(drawing(offset=70)))

    def test_recognizes_a_vertical_one(self):
        result = self.model.predict(drawing())
        self.assertEqual(result['digit'], 1)
        self.assertEqual(len(result['probabilities']), 10)
        self.assertAlmostEqual(sum(result['probabilities']), 1.0, places=5)
        self.assertTrue(all(0 <= p <= 1 for p in result['probabilities']))
        self.assertAlmostEqual(result['confidence'], result['probabilities'][1])
        self.assertEqual(np.asarray(result['pixels']).shape, (28, 28))


class QuietHandler(Handler):
    def log_message(self, format, *args):
        pass


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.server.model = Recognizer()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def post(self, payload, headers=None):
        request_headers = {'Content-Type': 'application/json'}
        request_headers.update(headers or {})
        status, body = self.request('POST', '/predict', json.dumps(payload), request_headers)
        return status, json.loads(body)

    def test_serves_korean_interface(self):
        status, body = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn('숫자 인식하기', body.decode('utf-8'))

    def test_valid_png_returns_prediction(self):
        origin = f'http://127.0.0.1:{self.server.server_port}'
        status, result = self.post({'image': image_data(drawing())}, {'Origin': origin})
        self.assertEqual(status, 200)
        self.assertEqual(result['digit'], 1)
        self.assertEqual(len(result['probabilities']), 10)

    def test_blank_png_returns_input_error(self):
        status, result = self.post({'image': image_data(Image.new('RGB', (336, 336), 'white'))})
        self.assertEqual(status, 400)
        self.assertIn('error', result)

    def test_jpeg_bytes_labeled_png_are_rejected(self):
        status, result = self.post({'image': image_data(drawing(), kind='JPEG')})
        self.assertEqual(status, 400)
        self.assertIn('error', result)

    def test_invalid_json_returns_input_error(self):
        status, body = self.request('POST', '/predict', '{')
        self.assertEqual(status, 400)
        self.assertIn('error', json.loads(body))

    def test_missing_image_returns_input_error(self):
        status, result = self.post({})
        self.assertEqual(status, 400)
        self.assertIn('error', result)

    def test_invalid_image_encoding_returns_input_error(self):
        status, result = self.post({'image': 'data:image/png;base64,not-base64!'})
        self.assertEqual(status, 400)
        self.assertIn('error', result)

    def test_foreign_origin_is_rejected(self):
        status, result = self.post({'image': image_data(drawing())}, {'Origin': 'https://example.com'})
        self.assertEqual(status, 403)
        self.assertIn('error', result)

    def test_unregistered_file_is_not_served(self):
        status, _ = self.request('GET', '/model.npz')
        self.assertEqual(status, 404)


if __name__ == '__main__':
    unittest.main()
