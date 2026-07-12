from django.shortcuts import render
from datetime import datetime


def index(request):
    """首页 - 会议列表和主界面"""
    return render(request, 'core/index.html', {'now': datetime.now()})


def meeting_detail(request, meeting_id):
    """会议详情页"""
    return render(request, 'core/meeting_detail.html', {'meeting_id': meeting_id, 'now': datetime.now()})
