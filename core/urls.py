from django.urls import path

from .views import feature_access_controls, update_feature_access, start_feature_trial, check_feature_access, premium_packages, premium_status, activate_premium, payment_methods, create_payment_transaction, review_payment_transaction, personal_font_styles, personal_font_favorites, editor_image_upload

urlpatterns = [
    path("personal-font-styles/", personal_font_styles, name="personal-font-styles"),
    path("personal-accounts/<int:personal_account_id>/font-favorites/", personal_font_favorites, name="personal-font-favorites"),
    path("editor-image-upload/", editor_image_upload, name="editor-image-upload"),
    path("premium-status/", premium_status, name="premium-status"),
    path("premium-activate/", activate_premium, name="premium-activate"),
    path("premium-packages/", premium_packages, name="premium-packages"),
    path("payment-methods/", payment_methods, name="payment-methods"),
    path("payment-transactions/", create_payment_transaction, name="create-payment-transaction"),
    path("admin/payment-transactions/<int:transaction_id>/review/", review_payment_transaction, name="review-payment-transaction"),
    path("feature-access/", feature_access_controls, name="feature-access-controls"),
    path("feature-access/<str:feature_key>/trial/", start_feature_trial, name="start-feature-trial"),
    path("feature-access/<str:feature_key>/check/", check_feature_access, name="check-feature-access"),
    path("admin/feature-access/<str:feature_key>/<str:account_type>/", update_feature_access, name="admin-update-feature-access"),
]
