"""
Job-related views for background tasks
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


@require_http_methods(["GET"])
@csrf_exempt
def check_for_completed_jobs(request):
    """
    Endpoint to check for completed jobs.
    Currently returns empty response as job system is not implemented.
    This endpoint exists to prevent 404 errors from polling requests.
    """
    return JsonResponse({
        'status': 'ok',
        'completed_jobs': [],
        'message': 'Job system not yet implemented'
    })
