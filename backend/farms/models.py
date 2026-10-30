from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models

from common.validators import validate_image_upload, validate_kyc_document


def get_private_storage():
    """KYC documents live OUTSIDE the public MEDIA_ROOT and have no URL.
    (A callable keeps the absolute path out of migration files.)"""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def kyc_upload_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
    # Random-ish, non-guessable name; never reuse the user's filename.
    import uuid
    return f"kyc/farm_{instance.farm_id}/{uuid.uuid4().hex}.{ext}"


class Farm(models.Model):
    """One farmer -> one farm profile (public marketing info + cached KYC status)."""

    class KYCStatus(models.TextChoices):
        NOT_SUBMITTED = 'not_submitted', 'Not submitted'
        PENDING = 'pending', 'Pending review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farm')
    farm_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    state = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    village = models.CharField(max_length=150, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    area_in_acres = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    farm_image = models.ImageField(upload_to='farm_images/', blank=True, null=True,
                                   validators=[validate_image_upload])

    # Cached result of the latest KYCApplication (source of truth = KYCApplication rows).
    kyc_status = models.CharField(max_length=15, choices=KYCStatus.choices,
                                  default=KYCStatus.NOT_SUBMITTED, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.farm_name} ({self.user.username})"

    @property
    def is_verified(self):
        return self.kyc_status == self.KYCStatus.APPROVED


class KYCApplication(models.Model):
    """One row per submission, so history and resubmission after rejection are kept."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    class IDType(models.TextChoices):
        AADHAAR = 'aadhaar', 'Aadhaar'
        PAN = 'pan', 'PAN'
        VOTER_ID = 'voter_id', 'Voter ID'
        DRIVING_LICENSE = 'driving_license', 'Driving licence'
        LAND_RECORD = 'land_record', 'Land record'

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='kyc_applications')
    id_type = models.CharField(max_length=20, choices=IDType.choices)
    # Privacy: we never store the full ID number, only the last 4 characters.
    id_number_last4 = models.CharField(max_length=4)
    document = models.FileField(upload_to=kyc_upload_path, storage=get_private_storage,
                                validators=[validate_kyc_document])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    decision_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='kyc_reviews')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"KYC #{self.pk} for {self.farm.farm_name} [{self.status}]"
