"""KYC business rules, kept out of the views so they are easy to test."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Farm, KYCApplication


@transaction.atomic
def submit_kyc(farm, *, id_type, id_number, document):
    farm = Farm.objects.select_for_update().get(pk=farm.pk)
    if farm.kyc_status == Farm.KYCStatus.PENDING:
        raise ValidationError({'detail': 'You already have a KYC application under review.'})
    if farm.kyc_status == Farm.KYCStatus.APPROVED:
        raise ValidationError({'detail': 'Your KYC is already approved.'})
    app = KYCApplication.objects.create(
        farm=farm, id_type=id_type, id_number_last4=id_number[-4:], document=document,
    )
    farm.kyc_status = Farm.KYCStatus.PENDING
    farm.save(update_fields=['kyc_status', 'updated_at'])
    return app


@transaction.atomic
def decide_kyc(application_id, admin_user, *, approve, reason=''):
    app = KYCApplication.objects.select_for_update().select_related('farm').get(pk=application_id)
    if app.status != KYCApplication.Status.PENDING:
        raise ValidationError({'detail': 'This application has already been reviewed.'})
    if not approve and not reason.strip():
        raise ValidationError({'reason': 'A reason is required when rejecting an application.'})

    app.status = KYCApplication.Status.APPROVED if approve else KYCApplication.Status.REJECTED
    app.decision_reason = reason.strip()
    app.reviewed_by = admin_user
    app.reviewed_at = timezone.now()
    app.save(update_fields=['status', 'decision_reason', 'reviewed_by', 'reviewed_at'])

    app.farm.kyc_status = Farm.KYCStatus.APPROVED if approve else Farm.KYCStatus.REJECTED
    app.farm.save(update_fields=['kyc_status', 'updated_at'])
    return app
