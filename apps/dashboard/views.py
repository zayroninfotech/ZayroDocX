from django.shortcuts import render
from apps.pdf_tools.mongo_db import get_recent_jobs, get_stats


def dashboard(request):
    try:
        stats = get_stats()
        recent_jobs = get_recent_jobs(10)
    except Exception:
        stats = {'total_jobs': 0, 'by_tool': []}
        recent_jobs = []

    context = {
        'stats': stats,
        'recent_jobs': recent_jobs,
    }
    return render(request, 'dashboard.html', context)
