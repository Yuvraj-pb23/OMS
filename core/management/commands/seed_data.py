from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

from core.models import (
    Department, ComplaintCategory, StaffProfile,
    MasterRecord, Letter, Complaint,
    Draft, ForwardRecord, InboxMessage, Deadline
)


class Command(BaseCommand):
    help = 'Seeds the database with initial CCPCR OMS data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding CCPCR OMS database...\n')

        # ── 1. Superuser ──
        superuser, created = User.objects.get_or_create(username='admin', defaults={
            'email': 'admin@ccpcr.gov.in',
            'first_name': 'Super',
            'last_name': 'Admin'
        })
        if created:
            superuser.set_password('admin123')
            superuser.is_superuser = True
            superuser.is_staff = True
            superuser.save()

        # Ensure admin has a StaffProfile with ADMIN role
        StaffProfile.objects.get_or_create(
            user=superuser,
            defaults={'role': StaffProfile.Role.ADMIN, 'initials': 'SA'}
        )
        self.stdout.write(self.style.SUCCESS('  ✓ Superuser ready (admin / admin123)'))

        # ── 2. Departments ──
        departments_data = [
            ('Legal Department', 'legal@ccpcr.gov.in', 'Adv. Meera Sharma'),
            ('Investigation Cell', 'investigation@ccpcr.gov.in', 'SP Rajesh Malhotra'),
            ('Counseling Unit', 'counseling@ccpcr.gov.in', 'Dr. Anita Roy'),
            ('Child Welfare Committee', 'cwc@ccpcr.gov.in', 'Mrs. Sunita Devi'),
            ('Juvenile Justice Board', 'jjb@ccpcr.gov.in', 'Justice K.P. Singh'),
            ('Education Wing', 'education@ccpcr.gov.in', 'Prof. Ramesh Iyer'),
            ('Health Wing', 'health@ccpcr.gov.in', 'Dr. Priya Mehta'),
        ]
        departments = {}
        for name, email, head in departments_data:
            dept, created = Department.objects.get_or_create(
                name=name, defaults={'email': email, 'head': head}
            )
            departments[name] = dept
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(departments_data)} departments'))

        # ── 3. Complaint Categories ──
        categories_data = [
            ('POCSO', 'Protection of Children from Sexual Offences Act cases'),
            ('Child Marriage', 'Cases related to child marriage prevention'),
            ('Child Labour', 'Cases involving child labour violations'),
            ('Child Trafficking', 'Cases of child trafficking and abduction'),
            ('Corporal Punishment', 'Cases of corporal punishment in schools/institutions'),
            ('Juvenile Justice', 'Matters related to juvenile justice system'),
            ('Child Abuse', 'Physical, emotional, or psychological abuse cases'),
            ('Harassment', 'Harassment and bullying cases involving children'),
            ('Missing Child', 'Cases of missing or runaway children'),
            ('Education Related', 'Denial of education, RTE violations'),
            ('Health Related', 'Denial of healthcare, malnutrition cases'),
            ('Cyber Crime', 'Online exploitation and cyber crimes against children'),
            ('Other', 'Cases not fitting other categories'),
        ]
        categories = {}
        for name, desc in categories_data:
            cat, created = ComplaintCategory.objects.get_or_create(
                name=name, defaults={'description': desc}
            )
            categories[name] = cat
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(categories_data)} complaint categories'))

        # ── 4. Staff Profiles ──
        staff_data = [
            ('arjun', 'Arjun', 'Mehta', StaffProfile.Role.DEPT_USER, 'AM', 'Legal Department'),
            ('priya', 'Priya', 'Kapoor', StaffProfile.Role.DEPT_USER, 'PK', 'Investigation Cell'),
            ('rajesh', 'Rajesh', 'Verma', StaffProfile.Role.DEPT_USER, 'RV', 'Legal Department'),
            ('sita', 'Sita', 'Iyer', StaffProfile.Role.DEPT_USER, 'SI', 'Education Wing'),
        ]
        profiles = {}
        for username, first, last, role, initials, dept_name in staff_data:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'first_name': first, 'last_name': last}
            )
            profile, _ = StaffProfile.objects.update_or_create(
                user=user,
                defaults={
                    'role': role,

                    'initials': initials,
                    'department': departments.get(dept_name),
                }
            )
            profiles[username] = profile
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(staff_data)} staff profiles'))

        # ── 5. Letters (MasterRecord + Letter) ──
        letters_data = [
            {
                'subject': 'Budget Allocation Query',
                'sender': 'Ministry of Finance',
                'contact': 'finance@gov.in',
                'filed_against': 'Finance Department',
                'date': datetime.date(2024, 12, 1),
                'status': 'PENDING',
                'priority': 'HIGH',
                'dept': 'Legal Department',
                'due': datetime.date(2024, 12, 22),
                'desc': 'Inquiry regarding the projected budget shortfall for Q4 2024.',
            },
            {
                'subject': 'Infrastructure Plan',
                'sender': 'Public Works Dept',
                'contact': 'pwd@gov.in',
                'filed_against': 'City Planning Authority',
                'date': datetime.date(2024, 11, 28),
                'status': 'REPLIED',
                'priority': 'MEDIUM',
                'dept': 'Investigation Cell',
                'due': None,
                'desc': 'Proposal for new infrastructure development plan.',
            },
            {
                'subject': 'School Building Approval',
                'sender': 'Education Dept',
                'contact': 'education@gov.in',
                'filed_against': 'ABC Construction Corp',
                'date': datetime.date(2024, 11, 25),
                'status': 'FORWARDED',
                'priority': 'MEDIUM',
                'dept': 'Education Wing',
                'due': None,
                'desc': 'Request for approval of new school building construction.',
            },
            {
                'subject': 'Medical Procurement',
                'sender': 'Health Dept',
                'contact': 'health@gov.in',
                'filed_against': 'Pharma Supplies Ltd',
                'date': datetime.date(2024, 11, 20),
                'status': 'DRAFT',
                'priority': 'LOW',
                'dept': 'Health Wing',
                'due': None,
                'desc': 'Procurement request for medical supplies for child welfare centers.',
            },
        ]
        created_letters = []
        for data in letters_data:
            # Check if a MasterRecord with this subject already exists
            if not MasterRecord.objects.filter(
                record_type='LETTER', subject=data['subject']
            ).exists():
                master = MasterRecord.objects.create(
                    record_type='LETTER',
                    subject=data['subject'],
                    sender_name=data['sender'],
                    sender_contact=data['contact'],
                    filed_against=data.get('filed_against', ''),
                    received_date=data['date'],
                    status=data['status'],
                    priority=data['priority'],
                    department=departments.get(data['dept']),
                    assigned_to=profiles.get('arjun'),
                    description=data['desc'],
                )
                letter = Letter.objects.create(
                    master=master,
                    reply_due_date=data['due'],
                )
                created_letters.append(letter)

        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(letters_data)} letters'))

        # ── 6. Complaints (MasterRecord + Complaint) ──
        complaints_data = [
            {
                'subject': 'Infrastructure deterioration complaint',
                'citizen': 'Vikram Singh',
                'contact': '+91 98765 43210',
                'filed_against': 'Sunshine Children\'s Home',
                'date': datetime.date(2024, 12, 5),
                'status': 'OPEN',
                'priority': 'HIGH',
                'category': 'Child Abuse',
                'dept': 'Investigation Cell',
                'desc': 'Complaint regarding unsafe infrastructure at a children\'s home.',
            },
            {
                'subject': 'Service delay in processing application',
                'citizen': 'Anjali Desai',
                'contact': 'anjali.d@gmail.com',
                'filed_against': 'Central School Board',
                'date': datetime.date(2024, 12, 4),
                'status': 'IN_PROGRESS',
                'priority': 'MEDIUM',
                'category': 'Education Related',
                'dept': 'Education Wing',
                'desc': 'Delay in processing school enrollment application for a child.',
            },
            {
                'subject': 'Documentation irregularities',
                'citizen': 'Rohan Gupta',
                'contact': '+91 87654 32100',
                'filed_against': 'Local Police Station Sector 12',
                'date': datetime.date(2024, 12, 3),
                'status': 'RESOLVED',
                'priority': 'LOW',
                'category': 'Juvenile Justice',
                'dept': 'Juvenile Justice Board',
                'desc': 'Issues found in documentation process at juvenile justice board.',
            },
        ]
        for data in complaints_data:
            if not MasterRecord.objects.filter(
                record_type='COMPLAINT', subject=data['subject']
            ).exists():
                master = MasterRecord.objects.create(
                    record_type='COMPLAINT',
                    subject=data['subject'],
                    sender_name=data['citizen'],
                    sender_contact=data['contact'],
                    filed_against=data.get('filed_against', ''),
                    received_date=data['date'],
                    status=data['status'],
                    priority=data['priority'],
                    department=departments.get(data['dept']),
                    description=data['desc'],
                )
                Complaint.objects.create(
                    master=master,
                    category=categories.get(data['category']),
                )

        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(complaints_data)} complaints'))

        # ── 7. Drafts ──
        letter_masters = MasterRecord.objects.filter(record_type='LETTER').order_by('received_date')
        if letter_masters.exists() and Draft.objects.count() == 0:
            drafts_data = [
                {
                    'master': letter_masters[0],
                    'subject_line': 'Budget Allocation Inquiry',
                    'summary': 'This draft reply addresses the Ministry of Finance\'s inquiry regarding the projected budget shortfall for Q4 2024. It covers the unexpected rise in raw material costs, reallocation of funds, and a request for an emergency grant of ₹4 Crores.',
                    'body': 'To: The Under Secretary, Ministry of Finance\nSubject: Clarification on Budget Allocation & Shortfall Projection\n\nRespected Sir/Madam,\n\nWith reference to your letter, we submit the following details regarding the projected deficit in the Public Works account.\n\nOur primary focus has been the Metro Phase 2 extension. Due to market fluctuations, costs have risen by approximately 15%. This has created an unforeseen gap of ₹2.5 Crores.\n\nWe kindly request you to review the attached audit report and consider our application for the supplementary grant.\n\nYours Faithfully,\nArjun Mehta\nAdministrator, CCPCR.',
                    'ai_suggestion': 'I recommend using "market-driven cost variance" instead of "unforeseen gap" for a more analytical tone. Additionally, referencing the State Public Works Manual, Section 4 would strengthen the grant request.',
                },
                {
                    'master': letter_masters[1] if letter_masters.count() > 1 else letter_masters[0],
                    'subject_line': 'Infrastructure Complaint Response',
                    'summary': 'Formal response to citizen complaint regarding infrastructure deterioration. Confirms site inspection and outlines repair timeline.',
                    'body': 'Dear Citizen,\n\nThank you for reaching out regarding the infrastructure issues. Following your complaint, we dispatched our Quality Control Officer to inspect the location.\n\nRepair work is scheduled to commence within 48 hours. You can track the live status using the Ticket ID provided.\n\nRegards,\nPublic Grievance Cell.',
                    'ai_suggestion': 'Consider adding a sentence about the Defect Liability Period of the repair work to add assurance and professionalism to the response.',
                },
                {
                    'master': letter_masters[2] if letter_masters.count() > 2 else letter_masters[0],
                    'subject_line': 'Departmental Report Approval',
                    'summary': 'Internal cover letter for the Annual Departmental Performance Report 2024. Summarizes key achievements and seeks final approval.',
                    'body': 'Memorandum\nTo: The Director of Operations\nFrom: Administrative Desk\n\nPlease find attached the Annual Report for fiscal year 2024.\n\nKey Highlights:\n1. Operational Efficiency improved by 12%\n2. 5% surplus in administrative budget\n3. Employee retention at 98%\n\nWe request your signature to authorize the release.\n\nRegards,\nArjun Mehta.',
                    'ai_suggestion': 'Consider highlighting the Digital India Initiative metrics (paperless workflow savings) to align with Central Government mandates.',
                },
            ]
            for d in drafts_data:
                Draft.objects.create(**d)
            self.stdout.write(self.style.SUCCESS(f'  ✓ {len(drafts_data)} drafts'))

        # ── 8. Inbox Messages ──
        if InboxMessage.objects.count() == 0:
            now = timezone.now()
            inbox_data = [
                {
                    'ref_id': 'DRY-1460', 'channel': 'EMAIL',
                    'sender_name': 'John Citizen', 'sender_contact': 'john.citizen@gmail.com',
                    'subject': 'Urgent: Building Permit Request for Plot #45B',
                    'received_at': now - datetime.timedelta(minutes=10),
                    'priority': 'HIGH', 'is_read': False,
                },
                {
                    'ref_id': 'CMP-0450', 'channel': 'WHATSAPP',
                    'sender_name': 'Rajesh Kumar', 'sender_contact': '+91 98765 43210',
                    'subject': 'Water supply disruption in Sector 4',
                    'received_at': now - datetime.timedelta(minutes=24),
                    'priority': 'HIGH', 'is_read': False,
                },
                {
                    'ref_id': 'DRY-1459', 'channel': 'WEB',
                    'sender_name': 'Sarah Johnson', 'sender_contact': 'sarah.j@consultant.in',
                    'subject': 'RTI Application #RTI/2024/0892 - Infrastructure Projects',
                    'received_at': now - datetime.timedelta(hours=1),
                    'priority': 'MEDIUM', 'is_read': False,
                },
                {
                    'ref_id': 'SMS-7821', 'channel': 'SMS',
                    'sender_name': 'Anita Patel', 'sender_contact': '+91 87654 32109',
                    'subject': 'Follow-up on property tax rebate application',
                    'received_at': now - datetime.timedelta(hours=2),
                    'priority': 'LOW', 'is_read': True,
                },
                {
                    'ref_id': 'DRY-1458', 'channel': 'EMAIL',
                    'sender_name': 'Municipal Corp', 'sender_contact': 'notifications@municipal.gov',
                    'subject': 'Scheduled Maintenance: Portal downtime Sunday 2AM-5AM',
                    'received_at': now - datetime.timedelta(hours=3),
                    'priority': 'MEDIUM', 'is_read': True,
                },
                {
                    'ref_id': 'CMP-0449', 'channel': 'WHATSAPP',
                    'sender_name': 'Vikram Singh', 'sender_contact': '+91 76543 21098',
                    'subject': 'Request for street light repair at Block C',
                    'received_at': now - datetime.timedelta(hours=5),
                    'priority': 'LOW', 'is_read': True,
                },
                {
                    'ref_id': 'DRY-1457', 'channel': 'WEB',
                    'sender_name': 'Priya Kapoor', 'sender_contact': 'priya.k@business.com',
                    'subject': 'URGENT: Food license renewal deadline tomorrow',
                    'received_at': now - datetime.timedelta(minutes=45),
                    'priority': 'HIGH', 'is_read': False,
                },
                {
                    'ref_id': 'DRY-1456', 'channel': 'EMAIL',
                    'sender_name': 'Tech Support', 'sender_contact': 'support@citizenservices.gov',
                    'subject': 'System Update: New features deployed - Release v2.4.1',
                    'received_at': now - datetime.timedelta(hours=8),
                    'priority': 'LOW', 'is_read': True,
                },
            ]
            for msg in inbox_data:
                InboxMessage.objects.create(**msg)
            self.stdout.write(self.style.SUCCESS(f'  ✓ {len(inbox_data)} inbox messages'))

        # ── 9. Deadline ──
        first_letter_master = MasterRecord.objects.filter(record_type='LETTER').first()
        if first_letter_master and Deadline.objects.count() == 0:
            Deadline.objects.create(
                master=first_letter_master,
                due_date=datetime.date(2024, 12, 22),
                description='Reply Due',
            )
            self.stdout.write(self.style.SUCCESS('  ✓ 1 deadline'))

        self.stdout.write(self.style.SUCCESS('\n✅ Database seeded successfully!'))
        self.stdout.write(f'   Admin login: admin / admin123')
        self.stdout.write(f'   Total records: {MasterRecord.objects.count()} master records')
