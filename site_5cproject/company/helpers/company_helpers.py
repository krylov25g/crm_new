from django.db import connection
from core.models import StatusJob, Company, Regions, Types


def dictfetchall(cursor):
    """
    Return all rows from a cursor as a dict.
    Assume the column names are unique.
    """
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_inactive_regions():
    result = []
    with connection.cursor() as cursor:
        cursor.execute("SELECT " \
                "regions.id_region as id, " \
                "region_descriptions.region_status_id, " \
                "(SELECT COUNT(id_company) FROM company WHERE company.id_region_id = regions.id_region AND id_status_job = 2) as send_ip,  " \
                "(SELECT COUNT(id_company) FROM company WHERE company.id_region_id = regions.id_region AND id_status_job = 3) as send_kp,  " \
                "(SELECT COUNT(id_company) FROM company WHERE company.id_region_id = regions.id_region AND id_status_job = 6) as discussing_conditions, " \
                "(SELECT COUNT(id_company) FROM company WHERE company.id_region_id = regions.id_region AND  id_status_job = 8) as get_deal, " \

                "(SELECT COUNT(id_company) FROM company WHERE company.id_region_id = regions.id_region) as company_count, " \
                "(SELECT COUNT(id_company) FROM company WHERE company.id_region_id = regions.id_region AND company.id_status_job = 13) as company_trash_count " \
            "FROM regions " \
            "INNER JOIN region_descriptions ON region_descriptions.region_id = regions.id_region")
        rows = dictfetchall(cursor)
        
        for row in rows:
            if row["region_status_id"] == 1:
                result.append(row["id"])
            elif row["send_ip"] == 0 and row["send_kp"] == 0 \
                    and row["discussing_conditions"] == 0 \
                    and row["get_deal"] == 0:
                # проверка условия есть хотя бы одна карточка не в мусоре
                if ((row["company_trash_count"] > 0 and row["company_count"] == 0) or
                    (row["company_trash_count"] == row["company_count"] and row["company_trash_count"] > 0)):
                    result.append(row["id"])
            elif row["get_deal"] > 0:
                continue
            elif row["send_kp"] > 0 and row["get_deal"] == 0: 
                continue
            elif row["send_kp"] == 0 and row["get_deal"] == 0:
                continue
    return result

def get_company_statuses_filter(request, user_group):
    result = []
    company_statuses = StatusJob.objects.raw("SELECT * FROM status_job  ORDER BY FIELD (id_status_job, 9,1,2,3,6,8,15,12,11,14,4, 5, 7, 10, 13)")
    inactive_regions = get_inactive_regions()

    for company_status in company_statuses:
        query_status = Company.objects.filter(id_status_job=company_status.id_status_job)

        if user_group == 'manager':
            query_status = query_status.filter(id_manager=request.user.id)
        
        query_status = query_status.exclude(id_region_id__in=inactive_regions).count()
        
        result.append({
            "company_status": company_status.id_status_job,
            "name_status": company_status.name_status,
            "count": query_status
        })
    return result


def get_company_types_filter(request, user_group):
    result = []
    types = Types.objects.all()
    
    for type_ in types:
        query_status = Company.objects.filter(id_type_id=type_.id_type)

        if user_group == 'manager':
            query_status = query_status.filter(id_manager=request.user.id)
        
        query_status = query_status.count()

        result.append({
            "id_type": type_.id_type,
            "name_type": type_.name_type,
            "count": query_status
        })
    return result


def lost_companies_for_offers(region_id, user_id):
    result = []

    non_working_statuses = "4,7,9,10,11,13,14,15"
    statuses = '1, 2, 3, 6, 8'

    query_has_reminders = "SELECT DISTINCT c.id_company " \
        "FROM `company` AS c " \
        "INNER JOIN `reminders` AS r ON r.id_company = c.id_company " \
        f"WHERE c.id_status_job IN ({statuses}) AND r.check_reminder != 'on' " \
        "GROUP BY c.id_company"

    query_has_activeReminders = "SELECT DISTINCT c.id_company " \
        "FROM `company` AS c " \
        "INNER JOIN `reminders` AS r ON r.id_company = c.id_company " \
        f"WHERE c.id_status_job IN ({non_working_statuses}) AND r.check_reminder = ''" \
        "GROUP BY c.id_company "
    
    with connection.cursor() as cursor:
        query = "SELECT DISTINCT " \
                "c.id_company AS `company_id`, " \
                "c.id_manager_id AS `user_id`, " \
                "c.name_company AS `company`, " \
                "u.fio AS `fio`, " \
                "c.id_status_job AS `status_id`, " \
                "s.name_status AS `status` " \
                "FROM `company` AS c " \
                "LEFT JOIN users_old as u ON u.id_user = c.id_manager_id " \
                "LEFT JOIN status_job as s ON c.id_status_job = s.id_status_job " \
                f"WHERE ((c.id_status_job IN ({statuses}) AND c.id_company NOT IN ({query_has_reminders})) OR " \
                f"(c.id_status_job IN ({non_working_statuses}) AND c.id_company IN ({query_has_activeReminders}))) " \
                "GROUP BY c.id_company "
        cursor.execute(query)
        result_rows = dictfetchall(cursor)
        
        for result_row in result_rows:
            result.append({
                "company_id": result_row["company_id"],
                "user_id": result_row["user_id"],
                "company": result_row["company"],
                "fio": result_row["fio"],
                "status_id": result_row["status_id"],
                "status_name": result_row["status"],
            })
    return result

def get_regions_filter(request, user_group, query, region_timezone_sort, region_name_sort, selected_regions):
    orders = []    
    regions_list = []

    query_regions = "SELECT regions.id_region, "\
                        "regions.name_region, "\
                        "regions.timezone, "\
                        "region_descriptions.is_moving_out, "\
                        "region_descriptions.region_status_id, "\
                        "(SELECT COUNT(id_company) FROM company WHERE company.id_region_id = regions.id_region) as company_count "\
                    "FROM `regions`, `region_descriptions` "\
                    "WHERE regions.id_region = region_descriptions.region_id AND region_descriptions.region_status_id != 1 "
    query_regions += f" AND regions.name_region LIKE '%{query}%'" if len(query) > 0 else ""

    if len(region_timezone_sort) > 0 and region_timezone_sort == "region-timezone-asc": orders.append("regions.timezone ASC")
    elif len(region_timezone_sort) > 0 and region_timezone_sort == "region-timezone-desc": orders.append("regions.timezone DESC")
    if len(region_name_sort) > 0 and region_name_sort == "region-name-asc": orders.append("regions.name_region ASC")
    elif len(region_name_sort) > 0 and region_name_sort == "region-name-desc": orders.append("regions.name_region DESC")

    query_regions += " GROUP BY regions.id_region HAVING company_count > 0"
    query_regions += " ORDER BY " + ', '.join(orders) if len(orders) > 0 else " ORDER BY name_region ASC"

    with connection.cursor() as cursor:
        cursor.execute(query_regions)
        result_rows = dictfetchall(cursor)

        for result_row in result_rows:
            regions_list.append(result_row)
            query_region = f"SELECT * FROM company WHERE id_region_id = {result_row['id_region']}"
            query_region += f' AND id_manager = {request.user.id}' if user_group == "manager" else ""
            cursor.execute(query_region)
            result_region_rows = dictfetchall(cursor)

            result_row['result_region_numrows'] = len(result_region_rows)
    return result_rows
