from django.contrib import admin
from .models import (
    Department, ComplaintCategory, StaffProfile,
    MasterRecord, Letter, Complaint,
    Draft, ForwardRecord, InboxMessage, Deadline, Reply,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'head')
    search_fields = ('name',)


@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'initials')
    list_filter = ('role', 'department')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(MasterRecord)
class MasterRecordAdmin(admin.ModelAdmin):
    list_display = ('ref_no', 'record_type', 'subject', 'sender_name', 'filed_against', 'status', 'priority', 'department')
    list_filter = ('record_type', 'status', 'priority', 'department')
    search_fields = ('ref_no', 'subject', 'sender_name', 'filed_against')
    readonly_fields = ('ref_no', 'created_at', 'updated_at')


@admin.register(Letter)
class LetterAdmin(admin.ModelAdmin):
    list_display = ('diary_no', 'letter_type', 'reply_due_date')
    search_fields = ('diary_no',)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('complaint_no', 'category', 'victim_age', 'victim_gender')
    list_filter = ('category',)


@admin.register(Draft)
class DraftAdmin(admin.ModelAdmin):
    list_display = ('master', 'subject_line', 'updated_at')


@admin.register(ForwardRecord)
class ForwardRecordAdmin(admin.ModelAdmin):
    list_display = ('master', 'forwarded_to', 'forwarded_by', 'forwarded_at')
    list_filter = ('forwarded_to',)


@admin.register(InboxMessage)
class InboxMessageAdmin(admin.ModelAdmin):
    list_display = ('ref_id', 'channel', 'sender_name', 'subject', 'priority', 'is_read')
    list_filter = ('channel', 'priority', 'is_read')


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ('master', 'due_date', 'is_completed')
    list_filter = ('is_completed',)


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('master', 'replied_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content',)
