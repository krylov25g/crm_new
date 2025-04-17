from django.urls import path

from .views import search, \
                    action_search, \
                    search_result, \
                    view, \
                    create, \
                    action_region_filter

app_name = 'company'

urlpatterns = [
    path('search/', search, name='search'),
    path('action_search/', action_search, name='action_search'),
    path('search_result/<str:companies_list>', search_result, name='search_result'),
    path('view/<int:company_id>', view, name='view'),
    path('create/', create, name='create'),
    path('action_region_filter/', action_region_filter, name='action_region_filter'),
]