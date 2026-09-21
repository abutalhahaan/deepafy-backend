from django.urls import path

from .views import central_popup_settings, feature_access_controls, update_feature_access, start_feature_trial, check_feature_access, premium_packages, premium_status, activate_premium, payment_methods, create_payment_transaction, review_payment_transaction, personal_font_styles, personal_font_favorites, editor_image_upload, messaging_appearance, messaging_appearance_update, messaging_appearance_image_update, dmail_inbox, dmail_send, dmail_reply, dmail_thread, dmail_sent, dmail_draft_save, dmail_draft_list, dmail_draft_update, dmail_draft_delete, dmail_draft_send

urlpatterns = [
    path("messaging/inbox/", dmail_inbox, name="dmail-inbox"),
    path("messaging/send/", dmail_send, name="dmail-send"),
    path("messaging/<int:message_id>/reply/", dmail_reply, name="dmail-reply"),
    path("messaging/<int:message_id>/thread/", dmail_thread, name="dmail-thread"),
    path("messaging/sent/", dmail_sent, name="dmail-sent"),
    path("messaging/draft/save/", dmail_draft_save, name="dmail-draft-save"),
    path("messaging/draft/", dmail_draft_list, name="dmail-draft-list"),
    path("messaging/draft/<int:draft_id>/", dmail_draft_update, name="dmail-draft-update"),
    path("messaging/draft/<int:draft_id>/delete/", dmail_draft_delete, name="dmail-draft-delete"),
    path("messaging/draft/<int:draft_id>/send/", dmail_draft_send, name="dmail-draft-send"),
    path("popup-settings/", central_popup_settings, name="central-popup-settings"),
    path("personal-font-styles/", personal_font_styles, name="personal-font-styles"),
    path("personal-accounts/<int:personal_account_id>/font-favorites/", personal_font_favorites, name="personal-font-favorites"),
    path("editor-image-upload/", editor_image_upload, name="editor-image-upload"),
    path("messaging/appearance/", messaging_appearance, name="messaging-appearance"),
    path("messaging/appearance/update/", messaging_appearance_update, name="messaging-appearance-update"),
    path("messaging/appearance/image/", messaging_appearance_image_update, name="messaging-appearance-image-update"),
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
