from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime


# ──────────────────────────────────────────────
# Lookup / Reference Tables
# ──────────────────────────────────────────────

class Department(models.Model):
    """Departments that handle complaints/letters. Stores email for forwarding."""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    head = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class ComplaintCategory(models.Model):
    """Extensible list of complaint categories (POCSO, Harassment, etc.)."""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Complaint Categories'


class StaffProfile(models.Model):
    """Extends Django User with OMS-specific fields."""

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'CCPCR Admin'
        DEPT_USER = 'DEPT_USER', 'Department User'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DEPT_USER)
    initials = models.CharField(max_length=5, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        # Auto-generate initials from first + last name if not set
        if not self.initials and self.user:
            first = self.user.first_name[:1].upper() if self.user.first_name else ''
            last = self.user.last_name[:1].upper() if self.user.last_name else ''
            self.initials = first + last
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────
# Core Parent: Master Record
# ──────────────────────────────────────────────

class MasterRecord(models.Model):
    """Unified parent record for both Letters and Complaints.
    Provides a single table for combined search, filtering, and reporting."""

    class RecordType(models.TextChoices):
        LETTER = 'LETTER', 'Letter'
        COMPLAINT = 'COMPLAINT', 'Complaint'

    class Status(models.TextChoices):
        # Letter statuses
        PENDING = 'PENDING', 'Pending'
        REPLIED = 'REPLIED', 'Replied'
        FORWARDED = 'FORWARDED', 'Forwarded'
        DRAFT = 'DRAFT', 'Draft'
        # Complaint statuses
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'

    class Priority(models.TextChoices):
        HIGH = 'HIGH', 'High'
        MEDIUM = 'MEDIUM', 'Medium'
        LOW = 'LOW', 'Low'

    ref_no = models.CharField(max_length=30, unique=True, editable=False,
                              help_text='Auto-generated: CCPCR-YYYY-LTR/CMP-NNNN')
    record_type = models.CharField(max_length=10, choices=RecordType.choices)
    subject = models.CharField(max_length=500)
    sender_name = models.CharField(max_length=200,
                                   help_text='Sender for letters, Citizen name for complaints')
    sender_contact = models.CharField(max_length=200, blank=True,
                                      help_text='Phone or email')
    filed_against = models.CharField(max_length=255, blank=True,
                                     help_text='Who the letter/complaint is filed against (person, organization, etc.)')
    received_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   help_text='Department this is forwarded/assigned to')
    assigned_to = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL,
                                    null=True, blank=True)
    description = models.TextField(blank=True, help_text='Full details / body')
    notes = models.TextField(blank=True, help_text='Internal remarks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ref_no} — {self.subject}"

    class Meta:
        ordering = ['-received_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.ref_no:
            self.ref_no = self._generate_ref_no()
        super().save(*args, **kwargs)

    def _generate_ref_no(self):
        """Generate ref_no like CCPCR-2025-LTR-0001 or CCPCR-2025-CMP-0001."""
        year = timezone.now().year
        type_code = 'LTR' if self.record_type == self.RecordType.LETTER else 'CMP'
        prefix = f'CCPCR-{year}-{type_code}-'

        # Find the highest existing number for this type and year
        last_record = (
            MasterRecord.objects
            .filter(ref_no__startswith=prefix)
            .order_by('-ref_no')
            .first()
        )

        if last_record:
            try:
                last_num = int(last_record.ref_no.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        return f'{prefix}{next_num:04d}'

    @property
    def status_css_class(self):
        """Return CSS class name for status badge."""
        mapping = {
            'PENDING': 'pending',
            'REPLIED': 'replied',
            'FORWARDED': 'forwarded',
            'DRAFT': 'draft',
            'OPEN': 'open',
            'IN_PROGRESS': 'in-progress',
            'RESOLVED': 'resolved',
        }
        return mapping.get(self.status, 'pending')

    @property
    def priority_css_class(self):
        """Return CSS class name for priority badge."""
        mapping = {
            'HIGH': 'prio-high',
            'MEDIUM': 'prio-medium',
            'LOW': 'prio-low',
        }
        return mapping.get(self.priority, 'prio-medium')


# ──────────────────────────────────────────────
# Child Tables
# ──────────────────────────────────────────────

class Letter(models.Model):
    """Letter-specific fields, linked to a MasterRecord."""
    master = models.OneToOneField(MasterRecord, on_delete=models.CASCADE, related_name='letter')
    diary_no = models.CharField(max_length=30, unique=True, editable=False,
                                help_text='Auto-generated: CCPCR-YYYY-LTR-NNNN')
    letter_type = models.CharField(max_length=100, blank=True,
                                   help_text='Optional subcategory')
    reply_due_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Letter: {self.diary_no}"

    def save(self, *args, **kwargs):
        # diary_no mirrors the master ref_no for letters
        if not self.diary_no and self.master:
            self.diary_no = self.master.ref_no
        super().save(*args, **kwargs)


class Complaint(models.Model):
    """Complaint-specific fields, linked to a MasterRecord."""

    class VictimGender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'

    master = models.OneToOneField(MasterRecord, on_delete=models.CASCADE, related_name='complaint')
    complaint_no = models.CharField(max_length=30, unique=True, editable=False,
                                    help_text='Auto-generated: CCPCR-YYYY-CMP-NNNN')
    category = models.ForeignKey(ComplaintCategory, on_delete=models.SET_NULL,
                                  null=True, blank=True)
    victim_age = models.IntegerField(null=True, blank=True)
    victim_gender = models.CharField(max_length=10, choices=VictimGender.choices,
                                      null=True, blank=True)

    def __str__(self):
        return f"Complaint: {self.complaint_no}"

    def save(self, *args, **kwargs):
        # complaint_no mirrors the master ref_no for complaints
        if not self.complaint_no and self.master:
            self.complaint_no = self.master.ref_no
        super().save(*args, **kwargs)


# ──────────────────────────────────────────────
# Operational Tables
# ──────────────────────────────────────────────

class Draft(models.Model):
    """Draft replies linked to a MasterRecord (letter or complaint)."""
    master = models.ForeignKey(MasterRecord, on_delete=models.CASCADE, related_name='drafts')
    subject_line = models.CharField(max_length=500)
    summary = models.TextField(help_text='Brief summary of the draft')
    body = models.TextField(help_text='Full draft content')
    ai_suggestion = models.TextField(blank=True, help_text='AI-generated improvement suggestion')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Draft for {self.master.ref_no}: {self.subject_line}"

    class Meta:
        ordering = ['-updated_at']


class ForwardRecord(models.Model):
    """Tracks forwarding actions — which record was forwarded to which department."""
    master = models.ForeignKey(MasterRecord, on_delete=models.CASCADE, related_name='forwards')
    forwarded_to = models.ForeignKey(Department, on_delete=models.CASCADE)
    forwarded_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True)
    forwarded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.master.ref_no} → {self.forwarded_to.name}"

    class Meta:
        ordering = ['-forwarded_at']


class InboxMessage(models.Model):
    """Multi-channel inbox: email, WhatsApp, web portal, SMS."""

    class Channel(models.TextChoices):
        EMAIL = 'EMAIL', 'Email'
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        WEB = 'WEB', 'Web Portal'
        SMS = 'SMS', 'SMS'

    class Priority(models.TextChoices):
        HIGH = 'HIGH', 'High'
        MEDIUM = 'MEDIUM', 'Medium'
        LOW = 'LOW', 'Low'

    ref_id = models.CharField(max_length=30)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    sender_name = models.CharField(max_length=200)
    sender_contact = models.CharField(max_length=200, blank=True,
                                      help_text='Email address or phone number')
    subject = models.CharField(max_length=500)
    received_at = models.DateTimeField(default=timezone.now)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.channel}] {self.ref_id}: {self.subject[:50]}"

    class Meta:
        ordering = ['-received_at']

    @property
    def channel_lower(self):
        return self.channel.lower()

    @property
    def priority_css_class(self):
        mapping = {
            'HIGH': 'prio-high',
            'MEDIUM': 'prio-medium',
            'LOW': 'prio-low',
        }
        return mapping.get(self.priority, 'prio-medium')

    @property
    def sender_initials(self):
        """Generate initials from sender name."""
        parts = self.sender_name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            return parts[0][:2].upper()
        return '??'


class Deadline(models.Model):
    """Upcoming deadlines tied to master records."""
    master = models.ForeignKey(MasterRecord, on_delete=models.CASCADE, related_name='deadlines')
    due_date = models.DateField()
    description = models.CharField(max_length=300)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.description} — Due: {self.due_date}"

    class Meta:
        ordering = ['due_date']

    @property
    def is_overdue(self):
        return not self.is_completed and self.due_date < datetime.date.today()

    @property
    def is_urgent(self):
        """Due within 3 days."""
        if self.is_completed:
            return False
        return self.due_date <= datetime.date.today() + datetime.timedelta(days=3)


class Reply(models.Model):
    """Reply from a department user to a forwarded letter/complaint."""
    master = models.ForeignKey(MasterRecord, on_delete=models.CASCADE, related_name='replies')
    forward = models.ForeignKey(ForwardRecord, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='replies')
    replied_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True)
    content = models.TextField(help_text='Reply content / action taken')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def get_replied_by_name(self):
        if self.replied_by:
            name = self.replied_by.user.get_full_name()
            return name if name else self.replied_by.user.username
        return 'Unknown'

    @property
    def get_department_name(self):
        if self.replied_by and self.replied_by.department:
            return self.replied_by.department.name
        return ''

    def __str__(self):
        return f"Reply on {self.master.ref_no} by {self.replied_by}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Replies'

class ReplyReadStatus(models.Model):
    """Tracks whether a specific user (admin) has read a specific reply."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_replies')
    reply = models.ForeignKey(Reply, on_delete=models.CASCADE, related_name='read_statuses')
    is_read = models.BooleanField(default=True)
    read_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'reply')

    def __str__(self):
        return f"User {self.user.username} read status for Reply {self.reply.id}: {self.is_read}"
