import requests
import sys
import os
import json
from datetime import datetime
from pathlib import Path

class PoseDetectionAPITester:
    def __init__(self, base_url="http://localhost:8001/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.detection_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        
        # Don't set Content-Type for file uploads
        if not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)

            print(f"   Response Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_pose_detection_no_file(self):
        """Test pose detection without file"""
        success, response = self.run_test(
            "Pose Detection - No File",
            "POST",
            "detect-pose",
            422  # Unprocessable Entity for missing file
        )
        return success

    def test_pose_detection_invalid_file(self):
        """Test pose detection with invalid file"""
        # Create a dummy text file
        files = {'file': ('test.txt', 'This is not an image', 'text/plain')}
        success, response = self.run_test(
            "Pose Detection - Invalid File",
            "POST",
            "detect-pose",
            400,
            files=files
        )
        return success

    def create_sample_image(self):
        """Create a simple test image for pose detection"""
        try:
            import numpy as np
            from PIL import Image
            import io
            
            # Create a simple colored image (this won't have a pose, but tests the endpoint)
            img_array = np.random.randint(0, 255, (300, 300, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            
            return img_bytes.getvalue()
        except ImportError:
            # Fallback: create a minimal JPEG header (won't work for actual detection)
            return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'

    def test_pose_detection_valid_image(self):
        """Test pose detection with a valid image (may not contain pose)"""
        try:
            img_data = self.create_sample_image()
            files = {'file': ('test_image.jpg', img_data, 'image/jpeg')}
            
            success, response = self.run_test(
                "Pose Detection - Valid Image Format",
                "POST",
                "detect-pose",
                400,  # Expecting 400 because random image won't have detectable pose
                files=files
            )
            
            # If it succeeds (unlikely with random image), store detection_id
            if success and 'detection_id' in response:
                self.detection_id = response['detection_id']
                print(f"   Detection ID: {self.detection_id}")
                return True
            
            # Check if error message is about no pose detected
            return success
            
        except Exception as e:
            print(f"❌ Error creating test image: {str(e)}")
            return False

    def test_download_endpoints_without_detection(self):
        """Test download endpoints with invalid detection ID"""
        fake_id = "fake-detection-id"
        
        # Test JSON download
        json_success, _ = self.run_test(
            "Download JSON - Invalid ID",
            "GET",
            f"download/{fake_id}/json",
            404
        )
        
        # Test Image download
        img_success, _ = self.run_test(
            "Download Image - Invalid ID",
            "GET",
            f"download/{fake_id}/image",
            404
        )
        
        return json_success and img_success

    def test_download_invalid_file_type(self):
        """Test download with invalid file type"""
        fake_id = "fake-detection-id"
        success, _ = self.run_test(
            "Download - Invalid File Type",
            "GET",
            f"download/{fake_id}/invalid",
            400
        )
        return success

    def test_status_endpoints(self):
        """Test status check endpoints"""
        # Test POST status
        status_data = {"client_name": "test_client"}
        post_success, post_response = self.run_test(
            "Create Status Check",
            "POST",
            "status",
            200,
            data=status_data
        )
        
        # Test GET status
        get_success, get_response = self.run_test(
            "Get Status Checks",
            "GET",
            "status",
            200
        )
        
        return post_success and get_success

    def test_download_endpoints_with_valid_detection(self):
        """Test download endpoints if we have a valid detection ID"""
        if not self.detection_id:
            print("⏭️  Skipping download tests - no valid detection ID")
            return True
        
        # Test JSON download
        json_success, _ = self.run_test(
            "Download JSON - Valid ID",
            "GET",
            f"download/{self.detection_id}/json",
            200
        )
        
        # Test Image download
        img_success, _ = self.run_test(
            "Download Image - Valid ID",
            "GET",
            f"download/{self.detection_id}/image",
            200
        )
        
        return json_success and img_success

def main():
    print("🚀 Starting Pose Detection API Tests")
    print("=" * 50)
    
    tester = PoseDetectionAPITester()
    
    # Run all tests
    tests = [
        tester.test_root_endpoint,
        tester.test_pose_detection_no_file,
        tester.test_pose_detection_invalid_file,
        tester.test_pose_detection_valid_image,
        tester.test_download_endpoints_without_detection,
        tester.test_download_invalid_file_type,
        tester.test_status_endpoints,
        tester.test_download_endpoints_with_valid_detection,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {str(e)}")
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
