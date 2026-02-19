from django.shortcuts import render

# Create your views here.


def index(request):
    return render(request, 'index.html')

def inbox(request):
    return render(request, 'inbox.html')

def Document_Repository(request):
    return render(request, 'Document Repository.html', {'active_tab': 'Document Repository'})

def Analytics_Reporting(request):
    return render(request, 'Analytics & Reporting.html', {'active_tab': 'Analytics & Reporting'})

def dashboard(request):
    context = {
        'active_tab': 'dashboard'  # This tells the template which tab is active
    }
    return render(request, 'dashboard.html', context)