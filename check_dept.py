import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'oms.settings'
django.setup()

from core.models import Reply, StaffProfile, Department
from django.contrib.auth.models import User

with open('dept_report.txt', 'w') as f:
    f.write("=== ALL DEPARTMENTS ===\n")
    for d in Department.objects.all():
        f.write(f"  ID={d.pk}, Name={d.name}\n")

    f.write("\n=== ALL STAFF PROFILES ===\n")
    for sp in StaffProfile.objects.select_related('user', 'department').all():
        dept_name = sp.department.name if sp.department else 'NO DEPARTMENT'
        f.write(f"  User={sp.user.username}, Role={sp.role}, Dept={dept_name}\n")

    f.write("\n=== ALL REPLIES ===\n")
    for r in Reply.objects.select_related('replied_by', 'replied_by__user', 'replied_by__department').all():
        f.write(f"  Reply ID={r.pk}, Master={r.master_id}\n")
        if r.replied_by:
            f.write(f"    user: {r.replied_by.user.username}\n")
            dept = r.replied_by.department
            f.write(f"    department obj: {dept}\n")
            if dept:
                f.write(f"    department.name: {dept.name}\n")
            else:
                f.write(f"    department: NONE\n")
        f.write(f"    get_department_name: '{r.get_department_name}'\n")
    f.write("\nDONE\n")
