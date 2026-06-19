import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# @MX:ANCHOR: [AUTO] invalidate_tokens_on_deactivation — REQ-AUTH-022, SEC-MUST-005
# @MX:REASON: Called on every AdminUser post_save; deactivation path bulk-blacklists tokens
@receiver(post_save, sender="accounts.AdminUser")
def invalidate_tokens_on_deactivation(sender, instance, created=False, **kwargs):
    """
    REQ-AUTH-022 [CRITICAL]: When an account is deactivated (is_active → False),
    immediately invalidate ALL existing refresh tokens for that user.

    Note: Password reset does NOT invalidate tokens (see REQ-AUTH-018).
    """
    if created:
        # New user — no tokens to invalidate
        return

    if instance.is_active:
        # User is still active — nothing to do
        return

    # User is now inactive — blacklist all outstanding refresh tokens
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        # Find all outstanding tokens for this user
        outstanding_tokens = OutstandingToken.objects.filter(user=instance)

        # Avoid re-blacklisting already-blacklisted tokens
        existing_blacklisted_jtis = set(
            BlacklistedToken.objects.filter(token__in=outstanding_tokens).values_list(
                "token__jti", flat=True
            )
        )

        tokens_to_blacklist = [
            BlacklistedToken(token=token)
            for token in outstanding_tokens
            if token.jti not in existing_blacklisted_jtis
        ]

        if tokens_to_blacklist:
            BlacklistedToken.objects.bulk_create(tokens_to_blacklist, ignore_conflicts=True)

    except Exception:
        logger.exception(
            "Failed to blacklist tokens during account deactivation for user %s",
            instance.pk,
        )
