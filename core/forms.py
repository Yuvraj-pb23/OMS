from django import forms
from .models import (
    MasterRecord, Letter, Complaint,
    Department, ComplaintCategory, StaffProfile
)


class LetterRegistrationForm(forms.Form):
    """Form for registering a new letter. Creates both MasterRecord + Letter."""
    sender = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Ministry of Finance'
        })
    )
    sender_contact = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email or phone (optional)'
        })
    )
    filed_against = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Who is this filed against? (optional)'
        })
    )
    subject = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Budget Allocation Query'
        })
    )
    received_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    priority = forms.ChoiceField(
        choices=MasterRecord.Priority.choices,
        initial=MasterRecord.Priority.MEDIUM,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label='— Select Department (optional) —',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    letter_type = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Inquiry, Notice, Memo (optional)'
        })
    )
    reply_due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Full details of the letter...',
            'rows': 4
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Internal remarks (optional)',
            'rows': 2
        })
    )

    def save(self):
        """Create MasterRecord + Letter and return both."""
        data = self.cleaned_data

        master = MasterRecord.objects.create(
            record_type=MasterRecord.RecordType.LETTER,
            subject=data['subject'],
            sender_name=data['sender'],
            sender_contact=data.get('sender_contact', ''),
            filed_against=data.get('filed_against', ''),
            received_date=data['received_date'],
            status=MasterRecord.Status.PENDING,
            priority=data['priority'],
            department=data.get('department'),
            description=data.get('description', ''),
            notes=data.get('notes', ''),
        )

        letter = Letter.objects.create(
            master=master,
            letter_type=data.get('letter_type', ''),
            reply_due_date=data.get('reply_due_date'),
        )

        return master, letter


class ComplaintRegistrationForm(forms.Form):
    """Form for registering a new complaint. Creates both MasterRecord + Complaint."""
    citizen_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Vikram Singh'
        })
    )
    citizen_contact = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Phone or email (optional)'
        })
    )
    filed_against = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Who is the complaint against? (optional)'
        })
    )
    subject = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Brief description of the complaint'
        })
    )
    category = forms.ModelChoiceField(
        queryset=ComplaintCategory.objects.all(),
        empty_label='— Select Category —',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_filed = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    priority = forms.ChoiceField(
        choices=MasterRecord.Priority.choices,
        initial=MasterRecord.Priority.MEDIUM,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label='— Forward to Department (optional) —',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    victim_age = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Age (optional)',
            'min': 0, 'max': 18
        })
    )
    victim_gender = forms.ChoiceField(
        choices=[('', '— Select Gender (optional) —')] + list(Complaint.VictimGender.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Full details of the complaint...',
            'rows': 4
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Internal remarks (optional)',
            'rows': 2
        })
    )

    def save(self):
        """Create MasterRecord + Complaint and return both."""
        data = self.cleaned_data

        master = MasterRecord.objects.create(
            record_type=MasterRecord.RecordType.COMPLAINT,
            subject=data['subject'],
            sender_name=data['citizen_name'],
            sender_contact=data.get('citizen_contact', ''),
            filed_against=data.get('filed_against', ''),
            received_date=data['date_filed'],
            status=MasterRecord.Status.OPEN,
            priority=data['priority'],
            department=data.get('department'),
            description=data.get('description', ''),
            notes=data.get('notes', ''),
        )

        complaint = Complaint.objects.create(
            master=master,
            category=data.get('category'),
            victim_age=data.get('victim_age'),
            victim_gender=data.get('victim_gender') or None,
        )

        return master, complaint
