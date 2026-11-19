"""Service-functies voor het goedkeuren/afwijzen van vakantieaanvragen."""

from django.contrib.auth import get_user_model

from ..models import VacationRequest


def get_employees():
    """Gebruikers die geen planner of admin zijn (dus geen is_staff)."""
    user_model = get_user_model()
    return user_model.objects.filter(is_staff=False)


def get_filtered_vacation_requests(status="", user_id=""):
    """Alle vakantieaanvragen, optioneel gefilterd op status en/of gebruiker."""
    requests = VacationRequest.objects.select_related("user").all()

    if status in VacationRequest.PlanningStatus.values:
        requests = requests.filter(planning_status=status)

    if user_id:
        requests = requests.filter(user_id=user_id)

    return requests


def create_vacation_request(user, start_date, end_date):
    """Create a validated vacation request for an employee."""
    return VacationRequest.objects.create(
        user=user,
        start_date=start_date,
        end_date=end_date,
    )


def get_user_vacation_request_groups(user):
    """Return one employee's requests grouped by their planning status."""
    requests = VacationRequest.objects.filter(user=user)
    return {
        "pending_requests": requests.filter(
            planning_status=VacationRequest.PlanningStatus.PENDING
        ),
        "approved_requests": requests.filter(
            planning_status=VacationRequest.PlanningStatus.APPROVED
        ),
        "declined_requests": requests.filter(
            planning_status=VacationRequest.PlanningStatus.DECLINED
        ),
    }


def get_overlapping_vacation_requests(
    start_date, end_date, exclude_request_id=None, exclude_user_id=None
):
    """Geeft actieve vakantieaanvragen die een periode overlappen."""
    requests = VacationRequest.objects.select_related("user").filter(
        start_date__lte=end_date,
        end_date__gte=start_date,
        planning_status__in=[
            VacationRequest.PlanningStatus.PENDING,
            VacationRequest.PlanningStatus.APPROVED,
        ],
    )
    if exclude_request_id is not None:
        requests = requests.exclude(pk=exclude_request_id)
    if exclude_user_id is not None:
        requests = requests.exclude(user_id=exclude_user_id)
    return requests


def get_vacation_conflict_summary(
    start_date, end_date, exclude_request_id=None, exclude_user_id=None
):
    """Vat overlappende actieve aanvragen samen voor medewerker en planner."""
    overlaps = list(
        get_overlapping_vacation_requests(
            start_date,
            end_date,
            exclude_request_id=exclude_request_id,
            exclude_user_id=exclude_user_id,
        )
    )
    approved = [
        request
        for request in overlaps
        if request.planning_status == VacationRequest.PlanningStatus.APPROVED
    ]
    pending = [
        request
        for request in overlaps
        if request.planning_status == VacationRequest.PlanningStatus.PENDING
    ]
    return {
        "total": len(overlaps),
        "approved_count": len(approved),
        "pending_count": len(pending),
        "users": [request.user.username for request in overlaps],
        "has_conflict": bool(overlaps),
    }


def build_approval_request_overview(user_id=""):
    """Build request groups and conflict information for the planner overview."""
    requests = list(get_filtered_vacation_requests(user_id=user_id))
    conflict_count = 0
    for vacation_request in requests:
        if vacation_request.planning_status == VacationRequest.PlanningStatus.DECLINED:
            continue
        vacation_request.conflict_summary = get_vacation_conflict_summary(
            vacation_request.start_date,
            vacation_request.end_date,
            exclude_request_id=vacation_request.id,
        )
        if vacation_request.conflict_summary["has_conflict"]:
            conflict_count += 1

    pending_requests = [
        request
        for request in requests
        if request.planning_status == VacationRequest.PlanningStatus.PENDING
    ]
    approved_requests = [
        request
        for request in requests
        if request.planning_status == VacationRequest.PlanningStatus.APPROVED
    ]
    declined_requests = [
        request
        for request in requests
        if request.planning_status == VacationRequest.PlanningStatus.DECLINED
    ]
    return {
        "requests": requests,
        "pending_requests": pending_requests,
        "approved_requests": approved_requests,
        "declined_requests": declined_requests,
        "conflict_count": conflict_count,
    }


def apply_action_to_requests(action, request_ids):
    """Keurt de opgegeven vakantieaanvragen goed of af. Retourneert of er iets is bijgewerkt."""
    if action == "approve":
        new_status = VacationRequest.PlanningStatus.APPROVED
    elif action == "decline":
        new_status = VacationRequest.PlanningStatus.DECLINED
    else:
        return False

    if not request_ids:
        return False

    updated = VacationRequest.objects.filter(id__in=request_ids).update(
        planning_status=new_status
    )
    return updated > 0
