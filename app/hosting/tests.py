"""
Tests for Org Social Host application.
Following the Given/When/Then pattern from org-social-relay.
"""

from django.conf import settings
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import HostedFile
from .utils import generate_vfile_token, build_vfile_url, validate_nickname


class RootViewTest(TestCase):
    """Test cases for the root endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.root_url = "/"

    def test_root_endpoint_success(self):
        """Test GET / returns success response with HATEOAS links."""
        # Given: The root endpoint

        # When: We request the root endpoint
        response = self.client.get(self.root_url)

        # Then: We should get success response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["type"], "Success")
        self.assertEqual(response.json()["errors"], [])

        # Then: Should have data with name and description
        data = response.json()["data"]
        self.assertIn("name", data)
        self.assertIn("description", data)
        self.assertEqual(data["name"], "Org Social Host")

    def test_root_endpoint_hateoas_links(self):
        """Test GET / returns all expected HATEOAS links."""
        # Given: The root endpoint

        # When: We request the root endpoint
        response = self.client.get(self.root_url)

        # Then: Should have _links with all endpoints
        links = response.json()["_links"]
        expected_links = [
            "self",
            "signup",
            "upload",
            "delete",
            "redirect",
            "remove-redirect",
        ]

        for link_name in expected_links:
            self.assertIn(link_name, links, f"Missing link: {link_name}")

    def test_root_endpoint_response_format_compliance(self):
        """Test root endpoint response format compliance."""
        # Given: The root endpoint

        # When: We request the root endpoint
        response = self.client.get(self.root_url)

        # Then: Response should match expected format
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn("type", response_data)
        self.assertIn("errors", response_data)
        self.assertIn("data", response_data)
        self.assertIn("_links", response_data)
        self.assertIsInstance(response_data["errors"], list)
        self.assertIsInstance(response_data["data"], dict)
        self.assertIsInstance(response_data["_links"], dict)


class SignupViewTest(TestCase):
    """Test cases for the signup endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.signup_url = "/signup"

    def test_signup_success(self):
        """Test POST /signup with valid nickname creates account."""
        # Given: A valid nickname that doesn't exist
        nickname = "test_user"

        # When: We signup with the nickname
        response = self.client.post(
            self.signup_url,
            {"nick": nickname},
            format="json",
        )

        # Then: We should get success response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["type"], "Success")
        self.assertEqual(response.json()["errors"], [])

        # Then: Response should contain vfile and public-url
        data = response.json()["data"]
        self.assertIn("vfile", data)
        self.assertIn("public-url", data)

        # Then: vfile should be a valid URL with required params
        vfile = data["vfile"]
        self.assertIn("token=", vfile)
        self.assertIn("ts=", vfile)
        self.assertIn("sig=", vfile)

        # Then: public-url should match expected format
        public_url = data["public-url"]
        self.assertIn(f"/{nickname}/social.org", public_url)

        # Then: HostedFile should be created in database
        hosted_file = HostedFile.objects.get(nickname=nickname)
        self.assertEqual(hosted_file.nickname, nickname)
        self.assertIsNotNone(hosted_file.vfile_token)

    def test_signup_nickname_already_taken(self):
        """Test POST /signup with existing nickname returns error."""
        # Given: A nickname that already exists
        nickname = "existing_user"
        HostedFile.objects.create(
            nickname=nickname,
            vfile_token="token123",
            vfile_timestamp=1234567890,
            vfile_signature="sig123",
            file_content="",
        )

        # When: We try to signup with the same nickname
        response = self.client.post(
            self.signup_url,
            {"nick": nickname},
            format="json",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["type"], "Error")
        self.assertIn("already taken", response.json()["errors"][0].lower())

    def test_signup_invalid_nickname_too_short(self):
        """Test POST /signup with too short nickname returns error."""
        # Given: A nickname that is too short
        nickname = "ab"

        # When: We try to signup
        response = self.client.post(
            self.signup_url,
            {"nick": nickname},
            format="json",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["type"], "Error")
        self.assertIn("at least 3 characters", response.json()["errors"][0].lower())

    def test_signup_invalid_nickname_special_chars(self):
        """Test POST /signup with invalid characters returns error."""
        # Given: A nickname with invalid characters
        nickname = "user@name"

        # When: We try to signup
        response = self.client.post(
            self.signup_url,
            {"nick": nickname},
            format="json",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["type"], "Error")
        self.assertTrue(
            any("letters" in err.lower() or "alphanumeric" in err.lower()
                for err in response.json()["errors"])
        )

    def test_signup_missing_nickname(self):
        """Test POST /signup without nickname returns error."""
        # Given: No nickname provided

        # When: We try to signup without nickname
        response = self.client.post(
            self.signup_url,
            {},
            format="json",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["type"], "Error")


class UploadViewTest(TestCase):
    """Test cases for the upload endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.upload_url = "/upload"

        # Create a test user
        self.nickname = "test_user"
        token_data = generate_vfile_token(self.nickname)
        self.vfile = build_vfile_url(
            token_data["token"],
            token_data["timestamp"],
            token_data["signature"],
        )

        # Create hosted file
        self.hosted_file = HostedFile.objects.create(
            nickname=self.nickname,
            vfile_token=token_data["token"],
            vfile_timestamp=token_data["timestamp"],
            vfile_signature=token_data["signature"],
            file_content="",
        )

    def test_upload_success(self):
        """Test POST /upload with valid vfile uploads file."""
        # Given: A valid vfile and file content
        file_content = b"#+TITLE: Test\n\n* Posts\n** Test post\n"

        # Create a file-like object
        from io import BytesIO
        file = BytesIO(file_content)
        file.name = "social.org"

        # When: We upload the file
        response = self.client.post(
            self.upload_url,
            {
                "vfile": self.vfile,
                "file": file,
            },
            format="multipart",
        )

        # Then: We should get success response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["type"], "Success")
        self.assertEqual(response.json()["errors"], [])

        # Then: Response should contain confirmation
        data = response.json()["data"]
        self.assertIn("message", data)
        self.assertIn("public-url", data)

        # Then: Content should be saved in database
        self.hosted_file.refresh_from_db()
        self.assertEqual(self.hosted_file.file_content, file_content.decode("utf-8"))

    def test_upload_invalid_vfile(self):
        """Test POST /upload with invalid vfile returns error."""
        # Given: An invalid vfile
        invalid_vfile = "http://localhost/vfile?token=invalid&ts=123&sig=bad"

        file_content = b"#+TITLE: Test\n"
        from io import BytesIO
        file = BytesIO(file_content)
        file.name = "social.org"

        # When: We try to upload with invalid vfile
        response = self.client.post(
            self.upload_url,
            {
                "vfile": invalid_vfile,
                "file": file,
            },
            format="multipart",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["type"], "Error")
        self.assertIn("invalid", response.json()["errors"][0].lower())

    def test_upload_file_too_large(self):
        """Test POST /upload with file exceeding size limit returns error."""
        # Given: A file that exceeds MAX_FILE_SIZE
        large_content = b"X" * (settings.MAX_FILE_SIZE + 1)

        from io import BytesIO
        file = BytesIO(large_content)
        file.name = "social.org"

        # When: We try to upload the large file
        response = self.client.post(
            self.upload_url,
            {
                "vfile": self.vfile,
                "file": file,
            },
            format="multipart",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        self.assertEqual(response.json()["type"], "Error")
        self.assertIn("too large", response.json()["errors"][0].lower())

    def test_upload_missing_file(self):
        """Test POST /upload without file returns error."""
        # Given: No file provided

        # When: We try to upload without file
        response = self.client.post(
            self.upload_url,
            {"vfile": self.vfile},
            format="multipart",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["type"], "Error")


class DeleteViewTest(TestCase):
    """Test cases for the delete endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.delete_url = "/delete"

        # Create a test user
        self.nickname = "test_user"
        token_data = generate_vfile_token(self.nickname)
        self.vfile = build_vfile_url(
            token_data["token"],
            token_data["timestamp"],
            token_data["signature"],
        )

        # Create hosted file
        self.hosted_file = HostedFile.objects.create(
            nickname=self.nickname,
            vfile_token=token_data["token"],
            vfile_timestamp=token_data["timestamp"],
            vfile_signature=token_data["signature"],
            file_content="",
        )

    def test_delete_success(self):
        """Test POST /delete with valid vfile deletes account."""
        # Given: A valid vfile for existing account

        # When: We delete the account
        response = self.client.post(
            self.delete_url,
            {"vfile": self.vfile},
            format="json",
        )

        # Then: We should get success response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["type"], "Success")
        self.assertEqual(response.json()["errors"], [])

        # Then: HostedFile should be deleted from database
        self.assertFalse(
            HostedFile.objects.filter(nickname=self.nickname).exists()
        )

    def test_delete_invalid_vfile(self):
        """Test POST /delete with invalid vfile returns error."""
        # Given: An invalid vfile
        invalid_vfile = "http://localhost/vfile?token=invalid&ts=123&sig=bad"

        # When: We try to delete with invalid vfile
        response = self.client.post(
            self.delete_url,
            {"vfile": invalid_vfile},
            format="json",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["type"], "Error")
        self.assertIn("invalid", response.json()["errors"][0].lower())

        # Then: HostedFile should still exist
        self.assertTrue(
            HostedFile.objects.filter(nickname=self.nickname).exists()
        )

    def test_delete_nonexistent_account(self):
        """Test POST /delete for non-existent account returns error."""
        # Given: A valid vfile for non-existent account
        token_data = generate_vfile_token("nonexistent")
        vfile = build_vfile_url(
            token_data["token"],
            token_data["timestamp"],
            token_data["signature"],
        )

        # When: We try to delete non-existent account
        response = self.client.post(
            self.delete_url,
            {"vfile": vfile},
            format="json",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["type"], "Error")


class RedirectViewTest(TestCase):
    """Test cases for the redirect endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.redirect_url = "/redirect"

        # Create a test user
        self.nickname = "test_user"
        token_data = generate_vfile_token(self.nickname)
        self.vfile = build_vfile_url(
            token_data["token"],
            token_data["timestamp"],
            token_data["signature"],
        )

        # Create hosted file
        self.hosted_file = HostedFile.objects.create(
            nickname=self.nickname,
            vfile_token=token_data["token"],
            vfile_timestamp=token_data["timestamp"],
            vfile_signature=token_data["signature"],
            file_content="",
        )

    def test_redirect_success(self):
        """Test POST /redirect with valid vfile sets redirect."""
        # Given: A valid vfile and new URL
        new_url = "https://my-domain.org/social.org"

        # When: We set up a redirect
        response = self.client.post(
            self.redirect_url,
            {
                "vfile": self.vfile,
                "new-url": new_url,
            },
            format="json",
        )

        # Then: We should get success response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["type"], "Success")
        self.assertEqual(response.json()["errors"], [])

        # Then: Response should contain redirect URL
        data = response.json()["data"]
        self.assertIn("redirect-url", data)
        self.assertEqual(data["redirect-url"], new_url)

        # Then: HostedFile should have redirect_url set
        self.hosted_file.refresh_from_db()
        self.assertEqual(self.hosted_file.redirect_url, new_url)

    def test_redirect_invalid_url(self):
        """Test POST /redirect with invalid URL returns error."""
        # Given: An invalid URL
        invalid_url = "not-a-valid-url"

        # When: We try to set redirect with invalid URL
        response = self.client.post(
            self.redirect_url,
            {
                "vfile": self.vfile,
                "new-url": invalid_url,
            },
            format="json",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["type"], "Error")

        # Then: HostedFile should not have redirect_url set
        self.hosted_file.refresh_from_db()
        self.assertIsNone(self.hosted_file.redirect_url)


class RemoveRedirectViewTest(TestCase):
    """Test cases for the remove-redirect endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.remove_redirect_url = "/remove-redirect"

        # Create a test user with redirect
        self.nickname = "test_user"
        token_data = generate_vfile_token(self.nickname)
        self.vfile = build_vfile_url(
            token_data["token"],
            token_data["timestamp"],
            token_data["signature"],
        )

        # Create hosted file with redirect
        self.hosted_file = HostedFile.objects.create(
            nickname=self.nickname,
            vfile_token=token_data["token"],
            vfile_timestamp=token_data["timestamp"],
            vfile_signature=token_data["signature"],
            file_content="",
            redirect_url="https://other-domain.org/social.org",
        )

    def test_remove_redirect_success(self):
        """Test POST /remove-redirect with valid vfile removes redirect."""
        # Given: A valid vfile for account with redirect

        # When: We remove the redirect
        response = self.client.post(
            self.remove_redirect_url,
            {"vfile": self.vfile},
            format="json",
        )

        # Then: We should get success response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["type"], "Success")
        self.assertEqual(response.json()["errors"], [])

        # Then: HostedFile should not have redirect_url
        self.hosted_file.refresh_from_db()
        self.assertIsNone(self.hosted_file.redirect_url)

    def test_remove_redirect_no_redirect_configured(self):
        """Test POST /remove-redirect when no redirect exists returns error."""
        # Given: An account without redirect
        self.hosted_file.redirect_url = None
        self.hosted_file.save()

        # When: We try to remove redirect
        response = self.client.post(
            self.remove_redirect_url,
            {"vfile": self.vfile},
            format="json",
        )

        # Then: We should get error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["type"], "Error")
        self.assertIn("no redirect", response.json()["errors"][0].lower())


class ServeFileViewTest(TestCase):
    """Test cases for the serve file endpoint."""

    def setUp(self):
        self.client = APIClient()

        # Create a test user
        self.nickname = "test_user"
        token_data = generate_vfile_token(self.nickname)

        # Create hosted file with content
        self.file_content = "#+TITLE: Test\n\n* Posts\n** Test post\n"
        self.hosted_file = HostedFile.objects.create(
            nickname=self.nickname,
            vfile_token=token_data["token"],
            vfile_timestamp=token_data["timestamp"],
            vfile_signature=token_data["signature"],
            file_content=self.file_content,
        )

    def test_serve_file_success(self):
        """Test GET /<nickname>/social.org serves file."""
        # Given: A file exists for the nickname
        serve_url = f"/{self.nickname}/social.org"

        # When: We request the file
        response = self.client.get(serve_url)

        # Then: We should get the file content
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode("utf-8"), self.file_content)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")

    def test_serve_file_not_found(self):
        """Test GET /<nickname>/social.org for non-existent file returns 404."""
        # Given: A nickname that doesn't exist
        serve_url = "/nonexistent/social.org"

        # When: We request the file
        response = self.client.get(serve_url)

        # Then: We should get 404
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_serve_file_with_redirect(self):
        """Test GET /<nickname>/social.org with redirect returns 301."""
        # Given: A file with redirect configured
        redirect_url = "https://new-domain.org/social.org"
        self.hosted_file.redirect_url = redirect_url
        self.hosted_file.save()

        serve_url = f"/{self.nickname}/social.org"

        # When: We request the file
        response = self.client.get(serve_url, follow=False)

        # Then: We should get 301 redirect
        self.assertEqual(response.status_code, status.HTTP_301_MOVED_PERMANENTLY)
        self.assertEqual(response["Location"], redirect_url)


class UtilsTest(TestCase):
    """Test cases for utility functions."""

    def test_generate_vfile_token(self):
        """Test generate_vfile_token creates valid token."""
        # Given: A nickname
        nickname = "test_user"

        # When: We generate a token
        token_data = generate_vfile_token(nickname)

        # Then: Token should have required fields
        self.assertIn("token", token_data)
        self.assertIn("timestamp", token_data)
        self.assertIn("signature", token_data)

        # Then: Token should be 64 hex characters (256 bits)
        self.assertEqual(len(token_data["token"]), 64)

        # Then: Timestamp should be an integer
        self.assertIsInstance(token_data["timestamp"], int)

        # Then: Signature should be a hex string
        self.assertTrue(all(c in "0123456789abcdef" for c in token_data["signature"]))

    def test_validate_nickname_valid(self):
        """Test validate_nickname accepts valid nicknames."""
        # Given: Valid nicknames
        valid_nicknames = [
            "user123",
            "test_user",
            "user-name",
            "ABC",
            "a_b_c",
        ]

        # When/Then: All should be valid
        for nickname in valid_nicknames:
            is_valid, error = validate_nickname(nickname)
            self.assertTrue(is_valid, f"{nickname} should be valid: {error}")
            self.assertEqual(error, "")

    def test_validate_nickname_invalid(self):
        """Test validate_nickname rejects invalid nicknames."""
        # Given: Invalid nicknames
        invalid_cases = [
            ("", "Nickname is required"),
            ("ab", "at least 3 characters"),
            ("a" * 51, "at most 50 characters"),
            ("user@name", "letters, numbers"),
            ("user name", "letters, numbers"),
        ]

        # When/Then: All should be invalid
        for nickname, expected_error in invalid_cases:
            is_valid, error = validate_nickname(nickname)
            self.assertFalse(is_valid, f"{nickname} should be invalid")
            self.assertIn(expected_error.lower(), error.lower())
