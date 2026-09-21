from django.test import TestCase
from rest_framework.test import APIClient

from identity.models import AccountType, UserIdentity
from notifications.models import Notification

from core.models import Dmail, DmailMailbox


class DmailSendInboxTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.sender = UserIdentity.objects.create(
            first_name="Test",
            last_name="Sender",
            username="test_sender",
            email="test_sender@example.com",
            is_active=True,
        )
        self.sender.set_password("TestPassword123!")
        self.sender.save()

        self.receiver = UserIdentity.objects.create(
            first_name="Test",
            last_name="Receiver",
            username="test_receiver",
            email="test_receiver@example.com",
            is_active=True,
        )
        self.receiver.set_password("TestPassword123!")
        self.receiver.save()

        AccountType.objects.create(
            identity=self.sender,
            account_type=AccountType.Type.PERSONAL,
            is_primary=True,
            is_active=True,
        )

        AccountType.objects.create(
            identity=self.receiver,
            account_type=AccountType.Type.PERSONAL,
            is_primary=True,
            is_active=True,
        )

    def test_send_dmail_creates_sent_inbox_and_notification(self):
        login_response = self.client.post(
            "/api/identity/login/",
            {
                "identifier": "test_sender",
                "password": "TestPassword123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.json()["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.post(
            "/api/core/messaging/send/",
            {
                "receiver": "test_receiver",
                "subject": "Test Dmail",
                "body": "This is a test Dmail.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        dmail = Dmail.objects.get(
            sender=self.sender,
            receiver=self.receiver,
        )

        self.assertEqual(dmail.subject, "Test Dmail")
        self.assertEqual(dmail.body, "This is a test Dmail.")

        sender_mailbox = DmailMailbox.objects.get(
            dmail=dmail,
            user=self.sender,
        )

        receiver_mailbox = DmailMailbox.objects.get(
            dmail=dmail,
            user=self.receiver,
        )

        self.assertEqual(sender_mailbox.folder, "sent")
        self.assertTrue(sender_mailbox.is_read)

        self.assertEqual(receiver_mailbox.folder, "inbox")
        self.assertFalse(receiver_mailbox.is_read)

        notification = Notification.objects.get(
            user=self.receiver,
            notification_type="new_dmail",
        )

        self.assertEqual(notification.category, "message")
        self.assertEqual(notification.source, "dmail")
        self.assertFalse(notification.is_read)

    def test_self_dmail_is_rejected(self):
        login_response = self.client.post(
            "/api/identity/login/",
            {
                "identifier": "test_sender",
                "password": "TestPassword123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.json()["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.post(
            "/api/core/messaging/send/",
            {
                "receiver": "test_sender",
                "subject": "Self test",
                "body": "This should fail.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Dmail.objects.count(), 0)

    def test_inbox_returns_received_dmail(self):
        login_response = self.client.post(
            "/api/identity/login/",
            {
                "identifier": "test_sender",
                "password": "TestPassword123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.json()["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        send_response = self.client.post(
            "/api/core/messaging/send/",
            {
                "receiver": "test_receiver",
                "subject": "Inbox test",
                "body": "Inbox body.",
            },
            format="json",
        )

        self.assertEqual(send_response.status_code, 201)

        receiver_login = self.client.post(
            "/api/identity/login/",
            {
                "identifier": "test_receiver",
                "password": "TestPassword123!",
            },
            format="json",
        )

        self.assertEqual(receiver_login.status_code, 200)

        receiver_token = receiver_login.json()["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {receiver_token}"
        )

        response = self.client.get("/api/core/messaging/inbox/")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["folder"], "inbox")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["messages"][0]["subject"], "Inbox test")
        self.assertFalse(data["messages"][0]["is_read"])


    def test_sent_returns_sent_dmail(self):
        login_response = self.client.post(
            "/api/identity/login/",
            {
                "identifier": "test_sender",
                "password": "TestPassword123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.json()["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        send_response = self.client.post(
            "/api/core/messaging/send/",
            {
                "receiver": "test_receiver",
                "subject": "Sent test",
                "body": "Sent mailbox test.",
            },
            format="json",
        )

        self.assertEqual(send_response.status_code, 201)

        response = self.client.get("/api/core/messaging/sent/")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["folder"], "sent")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["messages"][0]["subject"], "Sent test")
        self.assertEqual(
            data["messages"][0]["receiver_username"],
            "test_receiver",
        )


    def test_save_dmail_draft(self):
        login_response = self.client.post(
            "/api/identity/login/",
            {
                "identifier": "test_sender",
                "password": "TestPassword123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.json()["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.post(
            "/api/core/messaging/draft/save/",
            {
                "receiver": "test_receiver",
                "subject": "Draft test",
                "body": "This is a draft.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Draft saved successfully.")
        self.assertEqual(data["draft"]["receiver"], "test_receiver")
        self.assertEqual(data["draft"]["subject"], "Draft test")
        self.assertEqual(data["draft"]["body"], "This is a draft.")

        dmail = Dmail.objects.get(
            sender=self.sender,
            receiver=self.receiver,
        )

        self.assertEqual(dmail.subject, "Draft test")
        self.assertEqual(dmail.body, "This is a draft.")

        mailbox = DmailMailbox.objects.get(
            dmail=dmail,
            user=self.sender,
        )

        self.assertEqual(mailbox.folder, "draft")
        self.assertTrue(mailbox.is_read)


    def test_draft_list_returns_saved_draft(self):
        login_response = self.client.post(
            "/api/identity/login/",
            {
                "identifier": "test_sender",
                "password": "TestPassword123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.json()["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        save_response = self.client.post(
            "/api/core/messaging/draft/save/",
            {
                "receiver": "test_receiver",
                "subject": "Draft list test",
                "body": "Draft list body.",
            },
            format="json",
        )

        self.assertEqual(save_response.status_code, 201)

        response = self.client.get(
            "/api/core/messaging/draft/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["folder"], "draft")
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["drafts"][0]["receiver_username"],
            "test_receiver",
        )
        self.assertEqual(
            data["drafts"][0]["subject"],
            "Draft list test",
        )
        self.assertEqual(
            data["drafts"][0]["body"],
            "Draft list body.",
        )


    def test_update_dmail_draft(self):
        login_response = self.client.post(
            "/api/identity/login/",
            {
                "identifier": "test_sender",
                "password": "TestPassword123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.json()["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        save_response = self.client.post(
            "/api/core/messaging/draft/save/",
            {
                "receiver": "test_receiver",
                "subject": "Original subject",
                "body": "Original body.",
            },
            format="json",
        )

        self.assertEqual(save_response.status_code, 201)

        draft_id = save_response.json()["draft"]["id"]

        response = self.client.patch(
            f"/api/core/messaging/draft/{draft_id}/",
            {
                "receiver": "test_receiver",
                "subject": "Updated subject",
                "body": "Updated body.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(
            data["message"],
            "Draft updated successfully.",
        )
        self.assertEqual(
            data["draft"]["subject"],
            "Updated subject",
        )
        self.assertEqual(
            data["draft"]["body"],
            "Updated body.",
        )

        dmail = Dmail.objects.get(id=draft_id)

        self.assertEqual(dmail.subject, "Updated subject")
        self.assertEqual(dmail.body, "Updated body.")


    def test_delete_dmail_draft(self):
        login_response = self.client.post(
            "/api/identity/login/",
            {
                "identifier": "test_sender",
                "password": "TestPassword123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.json()["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        save_response = self.client.post(
            "/api/core/messaging/draft/save/",
            {
                "receiver": "test_receiver",
                "subject": "Delete test",
                "body": "Delete this draft.",
            },
            format="json",
        )

        self.assertEqual(save_response.status_code, 201)

        draft_id = save_response.json()["draft"]["id"]

        response = self.client.delete(
            f"/api/core/messaging/draft/{draft_id}/delete/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(
            data["message"],
            "Draft deleted successfully.",
        )
        self.assertEqual(data["draft_id"], draft_id)

        self.assertFalse(
            Dmail.objects.filter(id=draft_id).exists()
        )
        self.assertFalse(
            DmailMailbox.objects.filter(
                dmail_id=draft_id
            ).exists()
        )


    def test_send_dmail_draft(self):
        login_response = self.client.post(
            "/api/identity/login/",
            {
                "identifier": "test_sender",
                "password": "TestPassword123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.json()["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        save_response = self.client.post(
            "/api/core/messaging/draft/save/",
            {
                "receiver": "test_receiver",
                "subject": "Send draft test",
                "body": "This draft will be sent.",
            },
            format="json",
        )

        self.assertEqual(save_response.status_code, 201)

        draft_id = save_response.json()["draft"]["id"]

        response = self.client.post(
            f"/api/core/messaging/draft/{draft_id}/send/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(
            data["message"],
            "Draft sent successfully.",
        )
        self.assertEqual(
            data["dmail"]["receiver_username"],
            "test_receiver",
        )

        dmail = Dmail.objects.get(id=draft_id)

        sender_mailbox = DmailMailbox.objects.get(
            dmail=dmail,
            user=self.sender,
        )

        receiver_mailbox = DmailMailbox.objects.get(
            dmail=dmail,
            user=self.receiver,
        )

        self.assertEqual(sender_mailbox.folder, "sent")
        self.assertTrue(sender_mailbox.is_read)

        self.assertEqual(receiver_mailbox.folder, "inbox")
        self.assertFalse(receiver_mailbox.is_read)

        notification = Notification.objects.get(
            user=self.receiver,
            notification_type="new_dmail",
        )

        self.assertEqual(notification.category, "message")
        self.assertEqual(notification.source, "dmail")
        self.assertFalse(notification.is_read)
