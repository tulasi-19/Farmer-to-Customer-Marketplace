"""Shared upload validators (size, extension, real file signature)."""
from django.conf import settings
from django.core.exceptions import ValidationError

# First bytes ("magic numbers") of the file types we accept.
_SIGNATURES = {
    'pdf': (b'%PDF-',),
    'jpg': (b'\xff\xd8\xff',),
    'jpeg': (b'\xff\xd8\xff',),
    'png': (b'\x89PNG\r\n\x1a\n',),
}


def validate_upload(file, allowed_ext):
    """Reject files that are too big, have a disallowed extension, or whose
    content does not match the extension (e.g. an .exe renamed to .pdf)."""
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(f'File too large. Maximum size is {settings.MAX_UPLOAD_MB} MB.')
    name = (file.name or '').lower()
    ext = name.rsplit('.', 1)[-1] if '.' in name else ''
    if ext not in allowed_ext:
        raise ValidationError(f"Unsupported file type. Allowed: {', '.join(sorted(allowed_ext))}.")
    head = file.read(16)
    file.seek(0)
    if not any(head.startswith(sig) for sig in _SIGNATURES[ext]):
        raise ValidationError('File content does not match its extension.')


def validate_kyc_document(file):
    validate_upload(file, {'pdf', 'jpg', 'jpeg', 'png'})


def validate_image_upload(file):
    validate_upload(file, {'jpg', 'jpeg', 'png'})
