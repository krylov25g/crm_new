from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from core.models import Projects, ProjectStatus, Users
from company.helpers.company_helpers import get_company_statuses_filter, \
                                            get_company_types_filter, \
                                            lost_companies_for_offers, \
                                            get_regions_filter

@login_required
def view(request, compamy_id):
    return render(request, 'company/company.html')

@login_required
@require_http_methods(['GET'])
def search(request):
    user_group = 'guest'
    for group in request.user.groups.all():
        user_group = group.name

    company_statuses_filter = get_company_statuses_filter(request, user_group)
    company_types_filter = get_company_types_filter(request, user_group)
    company_projects_filter = Projects.objects.all()
    company_project_statuses_filter = ProjectStatus.objects.all()
    manager_filter = Users.objects.filter(Q(role=0) | Q(fio = "Общий")).filter(is_active=1).all()

    if user_group == "director":
        region_id = 0
        user_id = 0
    elif user_group == "manager":
        region_id = 0
        user_id = request.user.id

    lost_user_companies = lost_companies_for_offers(region_id, user_id)
    lost_user_companies_count = len(lost_user_companies)

    lost_user_companies_line = {}
    for line in lost_user_companies:
        if line["user_id"] not in lost_user_companies_line.keys():
            lost_user_companies_line.update({
                line["user_id"]: {
                    "name": line["fio"],
                    "lost": {}
                }
            })
        else:
            if line["status_id"] not in lost_user_companies_line[line["user_id"]]["lost"].keys():
                lost_user_companies_line[line["user_id"]]["lost"].update({
                    line["status_id"]: {
                        "status_name": line["status_name"],
                        "companies": [line["company_id"]]
                    }
                })
            elif line["company_id"] not in lost_user_companies_line[line["user_id"]]["lost"][line["status_id"]]["companies"]:
                lost_user_companies_line[line["user_id"]]["lost"][line["status_id"]]["companies"].append(line["company_id"])

    return render(request, 'company/search_company.html', {
        "user_group": user_group,
        "company_statuses_filter": company_statuses_filter,
        "company_types_filter": company_types_filter,
        "company_projects_filter": company_projects_filter,
        "company_project_statuses_filter": company_project_statuses_filter,
        "manager_filter": manager_filter,
        "lost_user_companies_list": lost_user_companies_line,
        "lost_user_companies_count": lost_user_companies_count
    })

@login_required
@require_http_methods(['POST'])
def action_search(request):
    print(request.POST)
    return render(request, 'company/search_result.html')

@login_required
def search_result(request, companies_list):
    return render(request, 'company/search_result.html')

@login_required
def create(request):
    return render(request, 'company/create_company.html')

@login_required
def action_region_filter(request):
    regions_list = []
    selected_regions = []
    user_group = 'guest'
    
    for group in request.user.groups.all():
        user_group = group.name

    try:
        selected_regions = request.session['regions_poisk_selected']
    except KeyError:
        pass

    session_action = request.GET.get('session_action') if request.GET.get('session_action') else ""
    region_to_session = request.GET.get('region_to_session') if request.GET.get('region_to_session') else ""
    delete_session = request.GET.get('delete_session') if request.GET.get('delete_session') else ""
    query = request.GET.get('q') if request.GET.get('q') else ""
    region_name_sort = request.GET.get('region_name_sort') if request.GET.get('region_name_sort') else ""
    region_timezone_sort = request.GET.get('region_timezone_sort') if request.GET.get('region_timezone_sort') else ""

    if len(delete_session) > 0:
        if request.session.get("delete_session"):
            del request.session[delete_session]
    elif len(session_action) > 0 and len(region_to_session) > 0:
        if session_action == 'add':
            if request.session.get('regions_poisk_selected', None) is None:    
                request.session.update({'regions_poisk_selected': [region_to_session]})
            else:
                regions = request.session['regions_poisk_selected']
                if region_to_session not in regions:
                    regions.append(region_to_session)
                request.session.update({'regions_poisk_selected': regions})
        elif session_action == 'delete':
            if region_to_session == 'all':
                if request.session.get('regions_poisk_selected', None) is None:
                    del request.session['regions_poisk_selected']
            else:
                regions = request.session['regions_poisk_selected']
                if region_to_session in regions:
                    regions.remove(region_to_session)
                request.session.update({'regions_poisk_selected': regions})
    else:
        regions_list = get_regions_filter(request, 
                                          user_group, 
                                          query, 
                                          region_timezone_sort, 
                                          region_name_sort, 
                                          selected_regions)

    return JsonResponse({'status': 'ok', 'regions_list': regions_list, 'selected_regions': selected_regions})
