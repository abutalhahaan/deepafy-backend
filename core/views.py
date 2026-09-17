from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import FeatureAccessControl, UserFeatureTrial, UserPremiumSubscription, PremiumPackage, PersonalFontStyle
from core.services.feature_access import get_current_feature, get_feature_access, start_feature_trial_for_user


@api_view(["GET"])
@permission_classes([AllowAny])
def personal_font_styles(request):
    fonts = PersonalFontStyle.objects.filter(is_enabled=True).order_by("display_order", "font_name")
    return Response({
        "success": True,
        "fonts": [
            {
                "font_key": font.font_key,
                "font_name": font.font_name,
                "font_family": font.font_family,
                "font_source": font.font_source,
                "font_weights": font.font_weights,
                "language_support": font.language_support,
                "category": font.category,
                "access_level": font.access_level,
                "is_enabled": font.is_enabled,
                "display_order": font.display_order,
            }
            for font in fonts
        ],
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def feature_access_controls(request):
    features = FeatureAccessControl.objects.filter(is_enabled=True).values(
        "feature_key",
        "feature_name",
        "account_type",
        "category",
        "access_level",
        "trial_enabled",
        "trial_days",
        "description",
    )

    return Response(list(features))

from identity.permissions import get_current_account_type

from rest_framework.permissions import BasePermission, IsAuthenticated


class IsDeepafyAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_superuser", False)
                or getattr(request.user, "is_staff", False)
            )
        )


@api_view(["PATCH"])
@permission_classes([IsDeepafyAdmin])
def update_feature_access(request, feature_key, account_type):
    if account_type not in {"personal", "professional", "company"}:
        return Response({"detail": "Invalid account_type."}, status=400)

    try:
        feature = FeatureAccessControl.objects.get(
            feature_key=feature_key,
            account_type=account_type,
        )
    except FeatureAccessControl.DoesNotExist:
        return Response({"detail": "Feature not found for this account type."}, status=404)

    allowed_fields = {
        "is_enabled",
        "access_level",
        "trial_enabled",
        "trial_days",
        "description",
    }

    for field in allowed_fields:
        if field in request.data:
            setattr(feature, field, request.data[field])

    feature.save()

    return Response({
        "feature_key": feature.feature_key,
        "feature_name": feature.feature_name,
        "account_type": feature.account_type,
        "category": feature.category,
        "is_enabled": feature.is_enabled,
        "access_level": feature.access_level,
        "trial_enabled": feature.trial_enabled,
        "trial_days": feature.trial_days,
        "description": feature.description,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_feature_trial(request, feature_key):
    feature, current_account_type, error = get_current_feature(
        request,
        feature_key,
    )

    if error:
        return Response(
            {
                "detail": error,
                "feature_key": feature_key,
                "account_type": (
                    current_account_type.account_type
                    if current_account_type
                    else None
                ),
            },
            status=400 if current_account_type is None else 404,
        )

    if feature.access_level != "premium":
        return Response({
            "access": "free",
            "feature_key": feature.feature_key,
            "account_type": feature.account_type,
        })

    if not feature.trial_enabled or feature.trial_days <= 0:
        return Response({
            "access": "premium",
            "trial_available": False,
            "feature_key": feature.feature_key,
            "account_type": feature.account_type,
        })

    return Response(
        start_feature_trial_for_user(request, feature)
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_feature_access(request, feature_key):
    access = get_feature_access(request, feature_key)

    if access["access"] == "error":
        return Response(
            {
                "detail": access["detail"],
                "feature_key": access["feature_key"],
                "account_type": access["account_type"],
            },
            status=400,
        )

    return Response(access)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def activate_premium(request):
    package_id = request.data.get("package_id")

    if not package_id:
        return Response({"detail": "package_id is required."}, status=400)

    try:
        package = PremiumPackage.objects.get(id=package_id, is_active=True)
    except PremiumPackage.DoesNotExist:
        return Response({"detail": "Premium package not found."}, status=404)

    now = timezone.now()
    current = UserPremiumSubscription.objects.filter(
        user=request.user,
        is_active=True,
        expires_at__gt=now,
        package__is_active=True,
    ).first()

    if current:
        return Response({
            "detail": "You already have an active Premium subscription.",
            "is_premium": True,
            "expires_at": current.expires_at,
        }, status=400)

    subscription = UserPremiumSubscription.objects.create(
        user=request.user,
        package=package,
        started_at=now,
        expires_at=now + timedelta(days=package.duration_days),
        is_active=True,
    )

    return Response({
        "success": True,
        "is_premium": True,
        "plan": package.name,
        "package_id": package.id,
        "duration_days": package.duration_days,
        "started_at": subscription.started_at,
        "expires_at": subscription.expires_at,
    }, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment_transaction(request):
    from .models import PaymentMethod, PaymentTransaction

    package_id = request.data.get("package_id")
    payment_method_id = request.data.get("payment_method_id")
    payment_details = request.data.get("payment_details") or {}

    try:
        package = PremiumPackage.objects.get(id=package_id, is_active=True)
        payment_method = PaymentMethod.objects.get(id=payment_method_id, is_active=True)
    except (PremiumPackage.DoesNotExist, PaymentMethod.DoesNotExist):
        return Response({"detail": "Invalid package or payment method."}, status=400)

    if not isinstance(payment_details, dict):
        return Response({"detail": "Payment details must be an object."}, status=400)

    required_fields = payment_method.fields.filter(is_active=True, is_required=True, is_customer_input=True)
    missing_fields = [field.field_key for field in required_fields if not str(payment_details.get(field.field_key, "")).strip()]
    if missing_fields:
        return Response({"detail": "Required payment information is missing.", "missing_fields": missing_fields}, status=400)

    transaction = PaymentTransaction.objects.create(
        user=request.user,
        package=package,
        payment_method=payment_method,
        amount=package.price,
        currency=package.currency,
        transaction_id=f"DF-{timezone.now().strftime('%Y%m%d%H%M%S%f')}",
        payment_reference=str(payment_details.get("transaction_reference", "")).strip(),
        sender_account=str(payment_details.get("sender_account", "")).strip(),
        payment_details=payment_details,
        status="pending",
    )

    return Response({
        "success": True,
        "transaction_id": transaction.transaction_id,
        "status": transaction.status,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "payment_method": payment_method.name,
    }, status=201)


@api_view(["POST"])
@authentication_classes([SessionAuthentication, JWTAuthentication])
@permission_classes([IsAuthenticated, IsDeepafyAdmin])
def review_payment_transaction(request, transaction_id):
    from .models import PaymentTransaction, UserPremiumSubscription

    action = str(request.data.get("action", "")).strip().lower()
    admin_note = str(request.data.get("admin_note", "")).strip()

    if action not in {"approve", "reject"}:
        return Response({"detail": "Action must be approve or reject."}, status=400)

    try:
        transaction = PaymentTransaction.objects.select_related("package", "payment_method", "user").get(id=transaction_id)
    except PaymentTransaction.DoesNotExist:
        return Response({"detail": "Payment transaction not found."}, status=404)

    if transaction.status != "pending":
        return Response({"detail": "Only pending transactions can be reviewed."}, status=400)

    now = timezone.now()

    if action == "reject":
        if not admin_note:
            return Response({"detail": "Rejection reason is required."}, status=400)
        transaction.status = "rejected"
        transaction.admin_note = admin_note
        transaction.verified_at = now
        transaction.save(update_fields=["status", "admin_note", "verified_at", "updated_at"])
        return Response({
            "success": True,
            "status": transaction.status,
            "transaction_id": transaction.transaction_id,
            "admin_note": transaction.admin_note,
        })

    current = UserPremiumSubscription.objects.filter(
        user=transaction.user,
        is_active=True,
        expires_at__gt=now,
        package__is_active=True,
    ).first()

    if current:
        return Response({"detail": "User already has an active Premium subscription."}, status=400)

    subscription = UserPremiumSubscription.objects.create(
        user=transaction.user,
        package=transaction.package,
        started_at=now,
        expires_at=now + timedelta(days=transaction.package.duration_days),
        is_active=True,
    )

    transaction.status = "approved"
    transaction.admin_note = admin_note
    transaction.verified_at = now
    transaction.save(update_fields=["status", "admin_note", "verified_at", "updated_at"])

    from notifications.services import create_notification
    create_notification(
        user=transaction.user,
        category="premium",
        notification_type="premium_payment_approved",
        title="Premium Payment Approved",
        message=f"Your payment for {transaction.package.name} has been approved. Your Premium subscription is now active.",
        source="payment",
        action_url="/dashboard",
        priority="normal",
    )

    return Response({
        "success": True,
        "status": transaction.status,
        "transaction_id": transaction.transaction_id,
        "plan": transaction.package.name,
        "subscription_id": subscription.id,
        "expires_at": subscription.expires_at,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def payment_methods(request):
    from .models import PaymentMethod
    methods = PaymentMethod.objects.filter(is_active=True).prefetch_related("fields")
    data = []
    for method in methods:
        data.append({
            "id": method.id,
            "name": method.name,
            "method_type": method.method_type,
            "verification_type": method.verification_type,
            "provider_key": method.provider_key,
            "logo_url": method.logo_url,
            "instructions": method.instructions,
            "display_order": method.display_order,
            "fields": [
                {
                    "field_key": field.field_key,
                    "field_label": field.field_label,
                    "field_type": field.field_type,
                    "placeholder": field.placeholder,
                    "help_text": field.help_text,
                    "is_required": field.is_required,
                    "is_active": field.is_active,
                    "is_customer_input": field.is_customer_input,
                    "value": field.value,
                    "display_order": field.display_order,
                }
                for field in method.fields.filter(is_active=True)
            ],
        })
    return Response(data)


@api_view(["GET"])
@permission_classes([AllowAny])
def premium_packages(request):
    packages = PremiumPackage.objects.filter(is_active=True).values(
        "id",
        "name",
        "duration_days",
        "price",
        "currency",
        "description",
    )

    return Response(list(packages))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def premium_status(request):
    now = timezone.now()

    subscription = (
        UserPremiumSubscription.objects
        .filter(
            user=request.user,
            is_active=True,
            expires_at__gt=now,
            package__is_active=True,
        )
        .select_related("package")
        .first()
    )

    if not subscription:
        return Response({
            "is_premium": False,
            "plan": "Free Personal Account",
            "expires_at": None,
        })

    return Response({
        "is_premium": True,
        "plan": subscription.package.name,
        "package_id": subscription.package.id,
        "duration_days": subscription.package.duration_days,
        "expires_at": subscription.expires_at,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def editor_image_upload(request):
    uploaded_image = request.FILES.get("image")

    if not uploaded_image:
        return Response(
            {"detail": "image is required."},
            status=400,
        )

    try:
        from django.core.files.storage import default_storage
        from .services.media_service import process_editor_image

        processed_image = process_editor_image(uploaded_image)

        file_path = default_storage.save(
            f"editor/{processed_image.name}",
            processed_image,
        )

        image_url = request.build_absolute_uri(
            default_storage.url(file_path)
        )

        return Response({
            "success": True,
            "url": image_url,
            "path": file_path,
        })

    except ValueError as error:
        return Response(
            {"detail": str(error)},
            status=400,
        )
