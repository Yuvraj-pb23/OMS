import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.core.paginator import Paginator

from .models import (
    MasterRecord, Letter, Complaint, Department, ComplaintCategory,
    StaffProfile, Draft, ForwardRecord, InboxMessage, Deadline, Reply,
)
from .forms import LetterRegistrationForm, ComplaintRegistrationForm
from .utils.notifications import send_sms_notification, send_email_notification


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def get_profile(request):
    """Get StaffProfile for logged-in user, or None."""
    try:
        return request.user.staff_profile
    except (StaffProfile.DoesNotExist, AttributeError):
        return None


def is_admin(request):
    """Check if logged-in user is a CCPCR admin."""
    profile = get_profile(request)
    return profile and profile.is_admin


def admin_required(view_func):
    """Decorator: only CCPCR admins can access."""
    def wrapper(request, *args, **kwargs):
        if not is_admin(request):
            messages.error(request, 'Access denied. Admin only.')
            return redirect('dept_dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        if is_admin(request):
            return redirect('index')
        return redirect('dept_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            profile = get_profile(request)
            if profile and profile.is_admin:
                return redirect('index')
            return redirect('dept_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ──────────────────────────────────────────────
# Registration (Admin only)
# ──────────────────────────────────────────────

@login_required
@admin_required
def register_letter(request):
    if request.method == 'POST':
        form = LetterRegistrationForm(request.POST)
        if form.is_valid():
            master = MasterRecord.objects.create(
                record_type=MasterRecord.RecordType.LETTER,
                subject=form.cleaned_data['subject'],
                sender_name=form.cleaned_data['sender'],
                sender_contact=form.cleaned_data.get('sender_contact', ''),
                filed_against=form.cleaned_data.get('filed_against', ''),
                received_date=form.cleaned_data['received_date'],
                priority=form.cleaned_data.get('priority', 'MEDIUM'),
                department=form.cleaned_data.get('department'),
                description=form.cleaned_data.get('description', ''),
            )
            Letter.objects.create(
                master=master,
                letter_type=form.cleaned_data.get('letter_type', ''),
                reply_due_date=form.cleaned_data.get('reply_due_date'),
            )
            
            # Application Logic: Notifications
            if master.sender_contact:
                sms_message = f"Your letter has been registered. Ref No: {master.ref_no}. Thanks, CCPCR OMS."
                send_sms_notification(master.sender_contact, sms_message)
                
            if master.department and master.department.email:
                email_subject = f"New Letter Assigned: {master.ref_no}"
                email_body = f"A new letter '{master.subject}' has been assigned to your department.\n\nDescription:\n{master.description}"
                send_email_notification(master.department.email, email_subject, email_body)

            messages.success(request, f'Letter registered: {master.ref_no}')
            return redirect('register_letter')
    else:
        form = LetterRegistrationForm()

    letters = Letter.objects.select_related('master').all()[:50]
    context = {
        'form': form,
        'letters': letters,
        'active_tab': 'register_letter',
    }
    return render(request, 'register_letter.html', context)


@login_required
@admin_required
def register_complaint(request):
    if request.method == 'POST':
        form = ComplaintRegistrationForm(request.POST)
        if form.is_valid():
            master = MasterRecord.objects.create(
                record_type=MasterRecord.RecordType.COMPLAINT,
                subject=form.cleaned_data['subject'],
                sender_name=form.cleaned_data['citizen_name'],
                sender_contact=form.cleaned_data.get('citizen_contact', ''),
                filed_against=form.cleaned_data.get('filed_against', ''),
                received_date=form.cleaned_data['date_filed'],
                priority=form.cleaned_data.get('priority', 'MEDIUM'),
                description=form.cleaned_data.get('description', ''),
                status=MasterRecord.Status.OPEN,
            )
            Complaint.objects.create(
                master=master,
                category=form.cleaned_data.get('category'),
                victim_age=form.cleaned_data.get('victim_age'),
                victim_gender=form.cleaned_data.get('victim_gender'),
            )
            
            # Application Logic: Notifications
            if master.sender_contact:
                sms_message = f"Your complaint has been registered. Ref No: {master.ref_no}. Thanks, CCPCR OMS."
                send_sms_notification(master.sender_contact, sms_message)
                
            # Note: Complaints might not have a department assigned on creation, 
            # but if they ever do in the future, this handles it.
            if master.department and master.department.email:
                email_subject = f"New Complaint Assigned: {master.ref_no}"
                email_body = f"A new complaint '{master.subject}' has been assigned to your department.\n\nDescription:\n{master.description}"
                send_email_notification(master.department.email, email_subject, email_body)

            messages.success(request, f'Complaint registered: {master.ref_no}')
            return redirect('register_complaint')
    else:
        form = ComplaintRegistrationForm()

    complaints = Complaint.objects.select_related('master', 'category').all()[:50]
    context = {
        'form': form,
        'complaints': complaints,
        'active_tab': 'register_complaint',
    }
    return render(request, 'register_complaint.html', context)


# ──────────────────────────────────────────────
# Admin Dashboard
# ──────────────────────────────────────────────

@login_required
@admin_required
def index(request):
    total_letters = MasterRecord.objects.filter(record_type='LETTER').count()
    total_complaints = MasterRecord.objects.filter(record_type='COMPLAINT').count()
    pending_replies = MasterRecord.objects.filter(
        status__in=['PENDING', 'OPEN', 'FORWARDED']
    ).count()
    active_cases = MasterRecord.objects.filter(
        status__in=['PENDING', 'OPEN', 'IN_PROGRESS', 'FORWARDED']
    ).count()

    recent_letters = Letter.objects.select_related('master', 'master__department').prefetch_related(
        'master__forwards', 'master__forwards__forwarded_to',
        'master__forwards__forwarded_by', 'master__forwards__forwarded_by__user',
    ).order_by('-master__created_at')[:5]
    recent_complaints = Complaint.objects.select_related('master', 'category', 'master__department').prefetch_related(
        'master__forwards', 'master__forwards__forwarded_to',
        'master__forwards__forwarded_by', 'master__forwards__forwarded_by__user',
    ).order_by('-master__created_at')[:5]
    deadlines = Deadline.objects.select_related('master').filter(
        is_completed=False, due_date__gte=datetime.date.today()
    )[:5]
    team = StaffProfile.objects.select_related('user', 'department').all()

    # AI-style insights
    overdue_letters = MasterRecord.objects.filter(
        record_type='LETTER', status='PENDING',
        received_date__lte=timezone.now().date() - datetime.timedelta(days=5)
    ).count()
    urgent_complaints = MasterRecord.objects.filter(
        record_type='COMPLAINT', priority='HIGH',
        status__in=['OPEN', 'IN_PROGRESS']
    ).count()
    recommended_forwards = MasterRecord.objects.filter(
        assigned_to__isnull=True,
        status__in=['PENDING', 'OPEN']
    ).count()

    # Chart data & specific stats for tabs
    months = []
    
    # Pre-calculated Tab Data
    dashboard_data = {
        'letters': {'kpis': [0,0,0,0], 'chartVol': [], 'chartDist': [0,0,0]},
        'complaints': {'kpis': [0,0,0,0], 'chartVol': [], 'chartDist': [0,0,0]},
        'replies': {'kpis': [0,0,0,0], 'chartVol': [], 'chartDist': [0,0,0]},
        'months': []
    }

    today = timezone.now().date()
    for i in range(5, -1, -1):
        d = today.replace(day=1) - datetime.timedelta(days=i * 30)
        month_label = d.strftime('%b')
        dashboard_data['months'].append(month_label)
        
        dashboard_data['letters']['chartVol'].append(
            MasterRecord.objects.filter(record_type='LETTER', received_date__year=d.year, received_date__month=d.month).count()
        )
        dashboard_data['complaints']['chartVol'].append(
            MasterRecord.objects.filter(record_type='COMPLAINT', received_date__year=d.year, received_date__month=d.month).count()
        )
        dashboard_data['replies']['chartVol'].append(
            Reply.objects.filter(created_at__year=d.year, created_at__month=d.month).count()
        )

    # Status Data
    def get_status_dist(record_type):
        return [
            MasterRecord.objects.filter(record_type=record_type, status__in=['RESOLVED', 'REPLIED']).count(),
            MasterRecord.objects.filter(record_type=record_type, status__in=['IN_PROGRESS', 'FORWARDED', 'DRAFT']).count(),
            MasterRecord.objects.filter(record_type=record_type, status__in=['PENDING', 'OPEN']).count()
        ]
        
    dashboard_data['letters']['chartDist'] = get_status_dist('LETTER')
    dashboard_data['complaints']['chartDist'] = get_status_dist('COMPLAINT')
    
    # For replies, we can just pseudo-distribute based on forward vs direct, or simply show all as "Resolved" for now in terms of the reply action itself
    dashboard_data['replies']['chartDist'] = [
        Reply.objects.filter(forward__isnull=False).count(), # Reply via forward
        Reply.objects.filter(forward__isnull=True).count(),  # Direct reply
        0 
    ]

    # Specific KPIs
    # Letters
    l_total = MasterRecord.objects.filter(record_type='LETTER').count()
    l_pending = MasterRecord.objects.filter(record_type='LETTER', status__in=['PENDING', 'OPEN', 'FORWARDED']).count()
    l_resolved = MasterRecord.objects.filter(record_type='LETTER', status__in=['RESOLVED', 'REPLIED']).count()
    l_urgent = MasterRecord.objects.filter(record_type='LETTER', priority='HIGH', status__in=['PENDING', 'OPEN']).count()
    dashboard_data['letters']['kpis'] = [l_total, l_pending, l_resolved, l_urgent]

    # Complaints
    c_total = MasterRecord.objects.filter(record_type='COMPLAINT').count()
    c_pending = MasterRecord.objects.filter(record_type='COMPLAINT', status__in=['PENDING', 'OPEN', 'FORWARDED', 'IN_PROGRESS']).count()
    c_resolved = MasterRecord.objects.filter(record_type='COMPLAINT', status='RESOLVED').count()
    c_urgent = MasterRecord.objects.filter(record_type='COMPLAINT', priority='HIGH', status__in=['PENDING', 'OPEN']).count()
    dashboard_data['complaints']['kpis'] = [c_total, c_pending, c_resolved, c_urgent]

    # Replies
    r_total = Reply.objects.count()
    r_today = Reply.objects.filter(created_at__date=today).count()
    r_week = Reply.objects.filter(created_at__gte=today - datetime.timedelta(days=7)).count()
    r_users = Reply.objects.values('replied_by').distinct().count()
    dashboard_data['replies']['kpis'] = [r_total, r_today, r_week, r_users]

    # Recent replies for admin to review
    recent_replies = Reply.objects.select_related(
        'master', 'replied_by', 'replied_by__user'
    ).order_by('-created_at')[:5]

    context = {
        'total_letters': total_letters,
        'total_complaints': total_complaints,
        'pending_replies': pending_replies,
        'active_cases': active_cases,
        'recent_letters': recent_letters,
        'recent_complaints': recent_complaints,
        'deadlines': deadlines,
        'team': team,
        'overdue_letters': overdue_letters,
        'urgent_complaints': urgent_complaints,
        'recommended_forwards': recommended_forwards,
        'dashboard_data_json': json.dumps(dashboard_data),
        'recent_replies': recent_replies,
        'active_tab': 'dashboard',
    }
    return render(request, 'index.html', context)


@login_required
@admin_required
def letters_list(request):
    """Paginated list of all letters."""
    query = Letter.objects.select_related('master').order_by('-master__created_at')
    
    # Optional search functionality
    search = request.GET.get('q', '')
    if search:
        query = query.filter(
            Q(master__ref_no__icontains=search) |
            Q(master__subject__icontains=search) |
            Q(master__sender_name__icontains=search)
        )
        
    status_filter = request.GET.get('status', '')
    if status_filter:
        query = query.filter(master__status=status_filter)

    paginator = Paginator(query, 20)  # 20 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    status_options = [
        {'value': 'PENDING', 'label': 'Pending', 'selected': status_filter == 'PENDING'},
        {'value': 'REPLIED', 'label': 'Replied', 'selected': status_filter == 'REPLIED'},
        {'value': 'FORWARDED', 'label': 'Forwarded', 'selected': status_filter == 'FORWARDED'},
        {'value': 'DRAFT', 'label': 'Draft', 'selected': status_filter == 'DRAFT'},
    ]

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'status_options': status_options,
        'active_tab': 'letters_list',
    }
    return render(request, 'letters_list.html', context)


@login_required
@admin_required
def complaints_list(request):
    """Paginated list of all complaints."""
    query = Complaint.objects.select_related('master', 'category').order_by('-master__created_at')
    
    # Optional search functionality
    search = request.GET.get('q', '')
    if search:
        query = query.filter(
            Q(master__ref_no__icontains=search) |
            Q(master__subject__icontains=search) |
            Q(master__sender_name__icontains=search)
        )

    status_filter = request.GET.get('status', '')
    if status_filter:
        query = query.filter(master__status=status_filter)

    paginator = Paginator(query, 20)  # 20 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    status_options = [
        {'value': 'OPEN', 'label': 'Open', 'selected': status_filter == 'OPEN'},
        {'value': 'IN_PROGRESS', 'label': 'In Progress', 'selected': status_filter == 'IN_PROGRESS'},
        {'value': 'RESOLVED', 'label': 'Resolved', 'selected': status_filter == 'RESOLVED'},
    ]

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'status_options': status_options,
        'active_tab': 'complaints_list',
    }
    return render(request, 'complaints_list.html', context)


@login_required
def dashboard_main(request):
    return redirect('index')


# ──────────────────────────────────────────────
# Forwarding (Admin + Dept users for chain)
# ──────────────────────────────────────────────

@login_required
def forward_record(request, pk):
    record = get_object_or_404(MasterRecord, pk=pk)
    profile = get_profile(request)
    departments = Department.objects.all()
    officers = StaffProfile.objects.select_related('user', 'department').all()

    if request.method == 'POST':
        dept_id = request.POST.get('department')
        officer_id = request.POST.get('officer')
        notes = request.POST.get('notes', '')

        dept = get_object_or_404(Department, pk=dept_id) if dept_id else None

        ForwardRecord.objects.create(
            master=record,
            forwarded_to=dept,
            forwarded_by=profile,
            notes=notes,
        )
        record.status = MasterRecord.Status.FORWARDED
        record.department = dept
        if officer_id:
            record.assigned_to = StaffProfile.objects.get(pk=officer_id)
        record.save()

        messages.success(request, f'{record.ref_no} forwarded to {dept.name}')
        if is_admin(request):
            return redirect('index')
    context = {
        'record': record,
        'departments': departments,
        'officers': officers,
        'active_tab': 'dashboard',
    }
    return render(request, 'forward.html', context)


# ──────────────────────────────────────────────
# Delete Record (Admin only)
# ──────────────────────────────────────────────

@login_required
@admin_required
def delete_record(request, pk):
    """Permanently delete a master record and redirect back to the list view."""
    record = get_object_or_404(MasterRecord, pk=pk)
    
    # Store record type before deletion for redirect routing
    r_type = record.record_type
    ref_no = record.ref_no
    
    if request.method == 'POST':
        record.delete()
        messages.success(request, f'Record {ref_no} was successfully deleted.')
        
        if r_type == 'LETTER':
            return redirect('letters_list')
        else:
            return redirect('complaints_list')
            
    # Fallback if accessed via GET accidentally
    if r_type == 'LETTER':
        return redirect('letters_list')
    else:
        return redirect('complaints_list')


# ──────────────────────────────────────────────
# Department Dashboard
# ──────────────────────────────────────────────

@login_required
def dept_dashboard(request):
    profile = get_profile(request)
    if not profile or not profile.department:
        messages.error(request, 'No department assigned to your profile.')
        return render(request, 'dept_dashboard.html', {
            'records': [], 'active_tab': 'dept_dashboard'
        })

    dept = profile.department

    # Records forwarded to this department
    forwarded_pks = ForwardRecord.objects.filter(
        forwarded_to=dept
    ).values_list('master_id', flat=True)

    records = MasterRecord.objects.filter(
        pk__in=forwarded_pks
    ).select_related('department', 'assigned_to', 'assigned_to__user')

    total = records.count()
    pending = records.filter(status__in=['PENDING', 'OPEN', 'FORWARDED']).count()
    replied = records.filter(status='REPLIED').count()
    resolved = records.filter(status='RESOLVED').count()

    context = {
        'records': records,
        'department': dept,
        'total': total,
        'pending': pending,
        'replied': replied,
        'resolved': resolved,
        'active_tab': 'dept_dashboard',
    }
    return render(request, 'dept_dashboard.html', context)


# ──────────────────────────────────────────────
# Reply
# ──────────────────────────────────────────────

@login_required
def reply_record(request, pk):
    record = get_object_or_404(MasterRecord, pk=pk)
    profile = get_profile(request)

    # Forward history for context
    forwards = ForwardRecord.objects.filter(
        master=record
    ).select_related('forwarded_to', 'forwarded_by', 'forwarded_by__user')

    # Existing replies
    existing_replies = Reply.objects.filter(
        master=record
    ).select_related('replied_by', 'replied_by__user')

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            # Link to the latest forward to this user's department
            latest_forward = forwards.filter(
                forwarded_to=profile.department
            ).first() if profile and profile.department else None

            Reply.objects.create(
                master=record,
                forward=latest_forward,
                replied_by=profile,
                content=content,
            )
            record.status = MasterRecord.Status.REPLIED
            record.save()

            messages.success(request, f'Reply submitted for {record.ref_no}')
            if is_admin(request):
                return redirect('index')
            return redirect('dept_dashboard')
        else:
            messages.error(request, 'Reply content cannot be empty.')

    context = {
        'record': record,
        'forwards': forwards,
        'existing_replies': existing_replies,
        'active_tab': 'dept_dashboard',
    }
    return render(request, 'reply.html', context)


# ──────────────────────────────────────────────
# Replies Received (Admin only)
# ──────────────────────────────────────────────

@login_required
@admin_required
def replies_received(request):
    """Show all letters and complaints that have received department replies."""
    from django.db.models import Prefetch, Count, Exists, OuterRef, Q
    from .models import ReplyReadStatus

    # Identify if a reply is unread by the current user
    # A reply is unread if there is no ReplyReadStatus for this user where is_read=True
    unread_status_subquery = ReplyReadStatus.objects.filter(
        reply=OuterRef('pk'),
        user=request.user,
        is_read=True
    )

    reply_prefetch = Prefetch(
        'replies',
        queryset=Reply.objects.select_related('replied_by', 'replied_by__user')
        .annotate(is_read_by_user=Exists(unread_status_subquery))
        .order_by('-created_at'),
    )

    # We also need a way to know if a *master record* has ANY unread replies.
    # We can annotate the MasterRecord with `has_unread`
    # A master record has unread replies if any of its replies lack a read status for this user
    unread_replies_for_record = Reply.objects.filter(
        master=OuterRef('pk')
    ).exclude(
        read_statuses__user=request.user,
        read_statuses__is_read=True
    )

    # Letters with at least one reply
    replied_letters = (
        MasterRecord.objects
        .filter(record_type='LETTER', replies__isnull=False)
        .distinct()
        .select_related('department')
        .prefetch_related(reply_prefetch)
        .annotate(
            reply_count=Count('replies'),
            has_unread=Exists(unread_replies_for_record)
        )
        .order_by('-updated_at')
    )

    # Complaints with at least one reply
    replied_complaints = (
        MasterRecord.objects
        .filter(record_type='COMPLAINT', replies__isnull=False)
        .distinct()
        .select_related('department')
        .prefetch_related(reply_prefetch)
        .annotate(
            reply_count=Count('replies'),
            has_unread=Exists(unread_replies_for_record)
        )
        .order_by('-updated_at')
    )

    context = {
        'replied_letters': replied_letters,
        'replied_complaints': replied_complaints,
        'letter_count': replied_letters.count(),
        'complaint_count': replied_complaints.count(),
        'active_tab': 'replies_received',
    }
    return render(request, 'replies_received.html', context)


# ──────────────────────────────────────────────
# Record Detail (Admin only)
# ──────────────────────────────────────────────

@login_required
@admin_required
def record_detail(request, pk):
    """Full detail view of a letter/complaint with forwarding history and replies."""
    record = get_object_or_404(MasterRecord, pk=pk)

    forwards = ForwardRecord.objects.filter(
        master=record
    ).select_related('forwarded_to', 'forwarded_by', 'forwarded_by__user')

    # Compute display name for each forward
    for fwd in forwards:
        if fwd.forwarded_by:
            name = fwd.forwarded_by.user.get_full_name()
            if not name:
                name = fwd.forwarded_by.user.username
            fwd.forwarded_by_display = name
        else:
            fwd.forwarded_by_display = 'Admin'

    replies = Reply.objects.filter(
        master=record
    ).select_related('replied_by', 'replied_by__user', 'replied_by__department')

    # Compute display name for each reply
    for r in replies:
        if r.replied_by:
            name = r.replied_by.user.get_full_name()
            if not name:
                name = r.replied_by.user.username
            r.replied_by_display = name
            r.department_display = r.replied_by.department.name if r.replied_by.department else ''
        else:
            r.replied_by_display = 'Unknown'
            r.department_display = ''

    context = {
        'record': record,
        'forwards': forwards,
        'replies': replies,
        'active_tab': 'dashboard',
    }
    return render(request, 'record_detail.html', context)


@login_required
@admin_required
def reply_detail(request, pk):
    """Minimal detail view for a replied record — shows record summary, forwarding chain, and replies."""
    record = get_object_or_404(MasterRecord, pk=pk)

    forwards = ForwardRecord.objects.filter(
        master=record
    ).select_related('forwarded_to', 'forwarded_by', 'forwarded_by__user')

    for fwd in forwards:
        if fwd.forwarded_by:
            name = fwd.forwarded_by.user.get_full_name()
            fwd.forwarded_by_display = name if name else fwd.forwarded_by.user.username
        else:
            fwd.forwarded_by_display = 'Admin'

    replies = Reply.objects.filter(
        master=record
    ).select_related('replied_by', 'replied_by__user', 'replied_by__department')

    for r in replies:
        if r.replied_by:
            name = r.replied_by.user.get_full_name()
            r.replied_by_display = name if name else r.replied_by.user.username
            r.department_display = r.replied_by.department.name if r.replied_by.department else ''
        else:
            r.replied_by_display = 'Unknown'
            r.department_display = ''

        # Mark each reply as read for this user
        from .models import ReplyReadStatus
        status_obj, created = ReplyReadStatus.objects.get_or_create(
            user=request.user,
            reply=r,
            defaults={'is_read': True}
        )
        if not status_obj.is_read:
            status_obj.is_read = True
            status_obj.save()

    context = {
        'record': record,
        'forwards': forwards,
        'replies': replies,
        'active_tab': 'replies',
    }
    return render(request, 'reply_detail.html', context)


from django.http import JsonResponse
import json

@login_required
@admin_required
def toggle_reply_read_status(request, pk):
    """AJAX endpoint to mark all replies for a master record as read or unread."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mark_as_read = data.get('is_read', True)
            
            record = get_object_or_404(MasterRecord, pk=pk)
            replies = record.replies.all()
            
            from .models import ReplyReadStatus
            for r in replies:
                status_obj, _ = ReplyReadStatus.objects.get_or_create(
                    user=request.user, reply=r
                )
                status_obj.is_read = mark_as_read
                status_obj.save()
                
            return JsonResponse({'success': True, 'is_read': mark_as_read})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


# ──────────────────────────────────────────────
# Inbox (Admin only)
# ──────────────────────────────────────────────

@login_required
@admin_required
def inbox(request):
    inbox_messages = InboxMessage.objects.all()[:50]
    context = {
        'messages_list': inbox_messages,
        'total_inbox': InboxMessage.objects.count(),
        'urgent_count': InboxMessage.objects.filter(priority='HIGH').count(),
        'unread_count': InboxMessage.objects.filter(is_read=False).count(),
        'resolution_rate': '94.2',
        'active_tab': 'inbox',
    }
    return render(request, 'inbox.html', context)


# ──────────────────────────────────────────────
# Analytics (Admin only)
# ──────────────────────────────────────────────

@login_required
@admin_required
def Analytics_Reporting(request):
    staff_count = max(1, StaffProfile.objects.count())
    letter_count = MasterRecord.objects.filter(record_type='LETTER').count()
    complaint_count = MasterRecord.objects.filter(record_type='COMPLAINT').count()

    def build_category_data(record_type, total):
        high = MasterRecord.objects.filter(record_type=record_type, priority='HIGH').count()
        med = MasterRecord.objects.filter(record_type=record_type, priority='MEDIUM').count()
        low = MasterRecord.objects.filter(record_type=record_type, priority='LOW').count()
        
        resolved_records = MasterRecord.objects.filter(record_type=record_type, status__in=['RESOLVED', 'REPLIED'])
        resolved = resolved_records.count()
        pending = MasterRecord.objects.filter(record_type=record_type, status__in=['PENDING', 'OPEN']).count()

        # Avg Resolution time
        avg_res_days = 0
        if resolved > 0:
            total_days = sum(
                (r.updated_at.date() - r.received_date).days 
                for r in resolved_records if r.received_date
            )
            avg_res_days = round(total_days / resolved, 1)

        # 6-month Efficiency Chart
        months = []
        eff_res = []
        eff_pen = []
        today = timezone.now().date()
        for i in range(5, -1, -1):
            d = today.replace(day=1) - datetime.timedelta(days=i * 30)
            months.append(d.strftime('%b'))
            res_count = MasterRecord.objects.filter(
                record_type=record_type, status__in=['RESOLVED', 'REPLIED'],
                updated_at__year=d.year, updated_at__month=d.month
            ).count()
            pen_count = MasterRecord.objects.filter(
                record_type=record_type, status__in=['PENDING', 'OPEN'],
                received_date__year=d.year, received_date__month=d.month
            ).count()
            eff_res.append(res_count)
            eff_pen.append(pen_count)

        dept_data = []
        for dept in Department.objects.all():
            dept_records = MasterRecord.objects.filter(record_type=record_type, department=dept)
            cap_pct = f"{min(100, int(dept_records.count() / staff_count * 100))}%"
            lead = dept.head or 'Unassigned'
            status = 'Operational' if dept_records.filter(status='RESOLVED').exists() else 'Review'
            dept_data.append({
                'id': f'{record_type[:3]}-{dept.pk}',
                'dept': dept.name,
                'lead': lead,
                'status': status,
                'cap': cap_pct,
            })

        return {
            'kpis': [str(total), str(pending), f'{avg_res_days} days', f'{min(100, int(total / staff_count * 100))}%'],
            'chartDist': [high, med, low, resolved],
            'chartEffLabels': months,
            'chartEff': {
                'res': eff_res,
                'pen': eff_pen,
            },
            'matrix': dept_data,
        }

    analytics_data = {
        'letters': build_category_data('LETTER', letter_count),
        'complaints': build_category_data('COMPLAINT', complaint_count),
    }

    context = {
        'analytics_json': json.dumps(analytics_data),
        'active_tab': 'analytics',
    }
    return render(request, 'Analytics & Reporting.html', context)


@login_required
def Document_Repository(request):
    return render(request, 'index.html', {'active_tab': 'documents'})