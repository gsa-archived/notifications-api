from enum import Enum


class TemplateType(Enum):
    SMS = "sms"
    EMAIL = "email"
    LETTER = "letter"


class NotificationType(Enum):
    SMS = "sms"
    EMAIL = "email"
    LETTER = "letter"


class TemplateProcessType(Enum):
    # TODO: Should Template.process_type be changed to use this?
    NORMAL = "normal"
    PRIORITY = "priority"


class AuthType(Enum):
    SMS = "sms_auth"
    EMAIL = "email_auth"
    WEBAUTHN = "webauthn_auth"


class CallbackType(Enum):
    DELIVERY_STATUS = "delivery_status"
    COMPLAINT = "complaint"


class OrganizationType(Enum):
    FEDERAL = "federal"
    STATE = "state"
    OTHER = "other"


class NotificationStatus(Enum):
    CANCELLED = "cancelled"
    CREATED = "created"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    PENDING = "pending"
    FAILED = "failed"
    TECHNICAL_FAILURE = "technical-failure"
    TEMPORARY_FAILURE = "temporary-failure"
    PERMANENT_FAILURE = "permanent-failure"
    PENDING_VIRUS_CHECK = "pending-virus-check"
    VALIDATION_FAILED = "validation-failed"
    VIRUS_SCAN_FAILED = "virus-scan-failed"

    @property
    def failed(self) -> tuple["NotificationStatus", ...]:
        cls = type(self)
        return (
            cls.TECHNICAL_FAILURE,
            cls.TEMPORARY_FAILURE,
            cls.PERMANENT_FAILURE,
            cls.VALIDATION_FAILED,
            cls.VIRUS_SCAN_FAILED,
        )

    @property
    def completed(self) -> tuple["NotificationStatus", ...]:
        cls = type(self)
        return (
            cls.SENT,
            cls.DELIVERED,
            cls.FAILED,
            cls.TECHNICAL_FAILURE,
            cls.TEMPORARY_FAILURE,
            cls.PERMANENT_FAILURE,
            cls.CANCELLED,
        )

    @property
    def success(self) -> tuple["NotificationStatus", ...]:
        cls = type(self)
        return (cls.SENT, cls.DELIVERED)

    @property
    def billable(self) -> tuple["NotificationStatus", ...]:
        cls = type(self)
        return (
            cls.SENDING,
            cls.SENT,
            cls.DELIVERED,
            cls.PENDING,
            cls.FAILED,
            cls.TEMPORARY_FAILURE,
            cls.PERMANENT_FAILURE,
        )

    @property
    def billable_sms(self) -> tuple["NotificationStatus", ...]:
        cls = type(self)
        return (
            cls.SENDING,
            cls.SENT,  # internationally
            cls.DELIVERED,
            cls.PENDING,
            cls.TEMPORARY_FAILURE,
            cls.PERMANENT_FAILURE,
        )

    @property
    def sent_emails(self) -> tuple["NotificationStatus", ...]:
        cls = type(self)
        return (
            cls.SENDING,
            cls.DELIVERED,
            cls.TEMPORARY_FAILURE,
            cls.PERMANENT_FAILURE,
        )

    @property
    def non_billable(self) -> tuple["NotificationStatus", ...]:
        self._non_billable: tuple["NotificationStatus", ...]
        try:
            return self._non_billable
        except AttributeError:
            self._non_billable = tuple(set(type(self)) - set(self.billable))
            return self._non_billable


class PermissionType(Enum):
    MANAGE_USERS = "manage_users"
    MANAGE_TEMPLATES = "manage_templates"
    MANAGE_SETTINGS = "manage_settings"
    SEND_TEXTS = "send_texts"
    SEND_EMAILS = "send_emails"
    MANAGE_API_KEYS = "manage_api_keys"
    PLATFORM_ADMIN = "platform_admin"
    VIEW_ACTIVITY = "view_activity"

    @property
    def defaults(self) -> tuple["PermissionType", ...]:
        cls = type(self)
        return (
            cls.MANAGE_USERS,
            cls.MANAGE_TEMPLATES,
            cls.MANAGE_SETTINGS,
            cls.SEND_TEXTS,
            cls.SEND_EMAILS,
            cls.MANAGE_API_KEYS,
            cls.VIEW_ACTIVITY,
        )


class ServicePermissionType(Enum):
    EMAIL = "email"
    SMS = "sms"
    INTERNATIONAL_SMS = "international_sms"
    INBOUND_SMS = "inbound_sms"
    SCHEDULE_NOTIFICATIONS = "schedule_notifications"
    EMAIL_AUTH = "email_auth"
    UPLOAD_DOCUMENT = "upload_document"
    EDIT_FOLDER_PERMISSIONS = "edit_folder_permissions"

    @property
    def defaults(self) -> tuple["ServicePermissionType", ...]:
        cls = type(self)
        return (
            cls.SMS,
            cls.EMAIL,
            cls.INTERNATIONAL_SMS,
        )


class RecipientType(Enum):
    MOBILE = "mobile"
    EMAIL = "email"


class KeyType(Enum):
    NORMAL = "normal"
    TEAM = "team"
    TEST = "test"


class JobStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in progress"
    FINISHED = "finished"
    SENDING_LIMITS_EXCEEDED = "sending limits exceeded"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    READY_TO_SEND = "ready to send"
    SENT_TO_DVLA = "sent to dvla"
    ERROR = "error"


class InvitedUserStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BrandType(Enum):
    # TODO: Should EmailBranding.branding_type be changed to use this?
    GOVUK = "govuk"  # Deprecated outside migrations
    ORG = "org"
    BOTH = "both"
    ORG_BANNER = "org_banner"


class CodeType(Enum):
    EMAIL = "email"
    SMS = "sms"


class AgreementType(Enum):
    MOU = "MOU"
    IAA = "IAA"


class AgreementStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
