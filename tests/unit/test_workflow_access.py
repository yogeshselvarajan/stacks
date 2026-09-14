from stacks.identity.workflow_access import role_can_access_workflow


def test_branch_manager_can_access_every_workflow():
    assert role_can_access_workflow("branch_manager", "room_booking") is True
    assert role_can_access_workflow("branch_manager", "ill_routing") is True
    assert role_can_access_workflow("branch_manager", "overdue_chase") is True


def test_room_booking_staff_can_only_access_room_booking():
    assert role_can_access_workflow("room_booking_staff", "room_booking") is True
    assert role_can_access_workflow("room_booking_staff", "ill_routing") is False
    assert role_can_access_workflow("room_booking_staff", "overdue_chase") is False


def test_ill_coordinator_can_only_access_ill_routing():
    assert role_can_access_workflow("ill_coordinator", "ill_routing") is True
    assert role_can_access_workflow("ill_coordinator", "room_booking") is False
    assert role_can_access_workflow("ill_coordinator", "overdue_chase") is False


def test_circulation_staff_can_only_access_overdue_chase():
    assert role_can_access_workflow("circulation_staff", "overdue_chase") is True
    assert role_can_access_workflow("circulation_staff", "room_booking") is False
    assert role_can_access_workflow("circulation_staff", "ill_routing") is False
