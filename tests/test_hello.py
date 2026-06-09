import unittest
import json
import sys, os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from hello import app # Assuming your original code is in app.py

class TestHelloSpencer(unittest.TestCase):
    def setUp(self):
        """Set up test client before each test."""
        self.app = app.test_client()
        self.app.testing = True

    def test_hello_endpoint_status_code(self):
        """Test if the endpoint returns 200 status code."""
        response = self.app.get('/api/hello')
        self.assertEqual(response.status_code, 200)

    def test_hello_endpoint_content_type(self):
        """Test if the response content type is application/json."""
        response = self.app.get('/api/hello')
        self.assertEqual(response.content_type, 'application/json')

    def test_hello_endpoint_data(self):
        """Test if the endpoint returns correct data."""
        response = self.app.get('/api/hello')
        data = json.loads(response.data.decode())

        # Test the response structure
        self.assertIn('message', data)
        self.assertIn('status', data)

        # Test the actual values
        self.assertEqual(data['message'], 'Hello Konstantin')
        self.assertEqual(data['status'], 'success')

if __name__ == '__main__':
    unittest.main()
