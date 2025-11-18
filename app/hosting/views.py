"""
Views for Org Social Host application.
"""

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import HostedFile
from .utils import (
    build_vfile_url,
    generate_vfile_token,
    parse_vfile_url,
    validate_nickname,
    verify_vfile_token,
)


@api_view(["GET"])
def root_view(request):
    """Root endpoint with basic information and available endpoints."""
    return Response(
        {
            "type": "Success",
            "errors": [],
            "data": {
                "name": "Org Social Host",
                "description": "Host your social.org files online",
                "version": "1.0.0",
            },
            "_links": {
                "self": {"href": "/", "method": "GET"},
                "signup": {
                    "href": "/signup",
                    "method": "POST",
                    "description": "Register a new nickname and get vfile token",
                },
                "upload": {
                    "href": "/upload",
                    "method": "POST",
                    "description": "Upload or update your social.org file",
                },
                "delete": {
                    "href": "/delete",
                    "method": "POST",
                    "description": "Delete your hosted file",
                },
                "redirect": {
                    "href": "/redirect",
                    "method": "POST",
                    "description": "Set up permanent redirect to new URL",
                },
                "remove-redirect": {
                    "href": "/remove-redirect",
                    "method": "POST",
                    "description": "Remove redirect and resume hosting",
                },
            },
        }
    )


@api_view(["GET", "POST"])
@parser_classes([JSONParser, FormParser])
def signup_view(request):
    """Register a new nickname and get vfile token."""
    # Handle GET request - show HTML form
    if request.method == "GET":
        from django.shortcuts import render
        return render(request, "hosting/signup.html")

    # Handle POST request - process signup
    # Support both JSON (API) and form data (HTMX)
    nickname = request.data.get("nick") or request.POST.get("nick")

    # Validate nickname
    if not nickname:
        return Response(
            {
                "type": "Error",
                "errors": ["Nickname is required"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    is_valid, error_message = validate_nickname(nickname)
    if not is_valid:
        return Response(
            {
                "type": "Error",
                "errors": [error_message],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if nickname already exists
    if HostedFile.objects.filter(nickname=nickname).exists():
        return Response(
            {
                "type": "Error",
                "errors": [f"Nickname '{nickname}' is already taken"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Generate vfile token
    token_data = generate_vfile_token(nickname)
    vfile_url = build_vfile_url(
        token_data["token"],
        token_data["timestamp"],
        token_data["signature"],
    )

    # Generate default content from template
    from django.template.loader import render_to_string
    default_content = render_to_string(
        "hosting/default_social.org",
        {"nick": nickname}
    )

    # Create hosted file record with default content
    hosted_file = HostedFile.objects.create(
        nickname=nickname,
        vfile_token=token_data["token"],
        vfile_timestamp=token_data["timestamp"],
        vfile_signature=token_data["signature"],
        file_content=default_content,
    )

    # Return vfile and public URL
    return Response(
        {
            "type": "Success",
            "errors": [],
            "data": {
                "vfile": vfile_url,
                "public-url": hosted_file.public_url,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def upload_view(request):
    """Upload or update social.org file."""
    vfile_url = request.data.get("vfile")
    uploaded_file = request.FILES.get("file")

    # Validate vfile
    if not vfile_url:
        return Response(
            {
                "type": "Error",
                "errors": ["vfile parameter is required"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Parse vfile
    vfile_data = parse_vfile_url(vfile_url)
    if not vfile_data or not all(vfile_data.values()):
        return Response(
            {
                "type": "Error",
                "errors": ["Invalid vfile format"],
                "data": {},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Find hosted file by token
    try:
        hosted_file = HostedFile.objects.get(vfile_token=vfile_data["token"])
    except HostedFile.DoesNotExist:
        return Response(
            {
                "type": "Error",
                "errors": ["Invalid vfile token"],
                "data": {},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Verify signature
    if not verify_vfile_token(
        vfile_data["token"],
        vfile_data["timestamp"],
        vfile_data["signature"],
        hosted_file.nickname,
    ):
        return Response(
            {
                "type": "Error",
                "errors": ["Invalid vfile signature"],
                "data": {},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Check if file is provided
    if not uploaded_file:
        return Response(
            {
                "type": "Error",
                "errors": ["File is required"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check file size
    if uploaded_file.size > settings.MAX_FILE_SIZE:
        return Response(
            {
                "type": "Error",
                "errors": [f"File too large. Maximum size is {settings.MAX_FILE_SIZE} bytes"],
                "data": {},
            },
            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    # Check if account is redirected
    if hosted_file.is_redirected:
        return Response(
            {
                "type": "Error",
                "errors": ["Cannot upload file while redirect is active. Remove redirect first."],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Save file content to database
    file_content = uploaded_file.read().decode("utf-8")
    hosted_file.file_content = file_content
    hosted_file.save()

    return Response(
        {
            "type": "Success",
            "errors": [],
            "data": {
                "message": "File uploaded successfully",
                "public-url": hosted_file.public_url,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def delete_view(request):
    """Delete hosted file."""
    vfile_url = request.data.get("vfile")

    # Validate vfile
    if not vfile_url:
        return Response(
            {
                "type": "Error",
                "errors": ["vfile parameter is required"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Parse vfile
    vfile_data = parse_vfile_url(vfile_url)
    if not vfile_data or not all(vfile_data.values()):
        return Response(
            {
                "type": "Error",
                "errors": ["Invalid vfile format"],
                "data": {},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Find hosted file by token
    try:
        hosted_file = HostedFile.objects.get(vfile_token=vfile_data["token"])
    except HostedFile.DoesNotExist:
        # Check if token is properly formatted (64-char hex string)
        # If yes, it's likely a valid token for non-existent account (404)
        # If no, it's an invalid/forged token (401)
        token = vfile_data["token"]
        if len(token) == 64 and all(c in "0123456789abcdef" for c in token.lower()):
            return Response(
                {
                    "type": "Error",
                    "errors": ["File not found"],
                    "data": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        else:
            return Response(
                {
                    "type": "Error",
                    "errors": ["Invalid vfile token"],
                    "data": {},
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

    # Verify signature
    if not verify_vfile_token(
        vfile_data["token"],
        vfile_data["timestamp"],
        vfile_data["signature"],
        hosted_file.nickname,
    ):
        return Response(
            {
                "type": "Error",
                "errors": ["Invalid vfile signature"],
                "data": {},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Delete database record
    hosted_file.delete()

    return Response(
        {
            "type": "Success",
            "errors": [],
            "data": {
                "message": "File deleted successfully",
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def redirect_view(request):
    """Set up permanent redirect to new URL."""
    vfile_url = request.data.get("vfile")
    new_url = request.data.get("new-url")

    # Validate vfile
    if not vfile_url:
        return Response(
            {
                "type": "Error",
                "errors": ["vfile parameter is required"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate new URL
    if not new_url:
        return Response(
            {
                "type": "Error",
                "errors": ["new-url parameter is required"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Basic URL validation
    if not (new_url.startswith("http://") or new_url.startswith("https://")):
        return Response(
            {
                "type": "Error",
                "errors": ["Invalid URL format. Must start with http:// or https://"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Parse vfile
    vfile_data = parse_vfile_url(vfile_url)
    if not vfile_data or not all(vfile_data.values()):
        return Response(
            {
                "type": "Error",
                "errors": ["Invalid vfile format"],
                "data": {},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Find hosted file by token
    try:
        hosted_file = HostedFile.objects.get(vfile_token=vfile_data["token"])
    except HostedFile.DoesNotExist:
        return Response(
            {
                "type": "Error",
                "errors": ["File not found"],
                "data": {},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Verify signature
    if not verify_vfile_token(
        vfile_data["token"],
        vfile_data["timestamp"],
        vfile_data["signature"],
        hosted_file.nickname,
    ):
        return Response(
            {
                "type": "Error",
                "errors": ["Invalid vfile signature"],
                "data": {},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Set redirect URL
    hosted_file.redirect_url = new_url
    hosted_file.save()

    return Response(
        {
            "type": "Success",
            "errors": [],
            "data": {
                "message": "Redirect configured successfully",
                "redirect-url": new_url,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def remove_redirect_view(request):
    """Remove redirect and resume hosting."""
    vfile_url = request.data.get("vfile")

    # Validate vfile
    if not vfile_url:
        return Response(
            {
                "type": "Error",
                "errors": ["vfile parameter is required"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Parse vfile
    vfile_data = parse_vfile_url(vfile_url)
    if not vfile_data or not all(vfile_data.values()):
        return Response(
            {
                "type": "Error",
                "errors": ["Invalid vfile format"],
                "data": {},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Find hosted file by token
    try:
        hosted_file = HostedFile.objects.get(vfile_token=vfile_data["token"])
    except HostedFile.DoesNotExist:
        return Response(
            {
                "type": "Error",
                "errors": ["File not found"],
                "data": {},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Verify signature
    if not verify_vfile_token(
        vfile_data["token"],
        vfile_data["timestamp"],
        vfile_data["signature"],
        hosted_file.nickname,
    ):
        return Response(
            {
                "type": "Error",
                "errors": ["Invalid vfile signature"],
                "data": {},
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Check if redirect exists
    if not hosted_file.is_redirected:
        return Response(
            {
                "type": "Error",
                "errors": ["No redirect configured for this account"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Remove redirect
    hosted_file.redirect_url = None
    hosted_file.save()

    return Response(
        {
            "type": "Success",
            "errors": [],
            "data": {
                "message": "Redirect removed successfully",
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def serve_file_view(request, nickname):
    """Serve the social.org file for a given nickname."""
    # Find hosted file
    try:
        hosted_file = HostedFile.objects.get(nickname=nickname)
    except HostedFile.DoesNotExist:
        return Response(
            {
                "type": "Error",
                "errors": ["File not found"],
                "data": {},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Check if redirected
    if hosted_file.is_redirected:
        return HttpResponse(
            status=status.HTTP_301_MOVED_PERMANENTLY,
            headers={"Location": hosted_file.redirect_url},
        )

    # Check if file has content
    if not hosted_file.file_content:
        return Response(
            {
                "type": "Error",
                "errors": ["File has no content"],
                "data": {},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Update last access
    hosted_file.touch()

    # Return file content
    response = HttpResponse(
        hosted_file.file_content,
        content_type="text/plain; charset=utf-8",
    )
    return response
