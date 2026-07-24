from uuid import uuid4


def test_anonymous_user_is_redirected_to_login(client):
    response = client.get("/admin/users")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_respondent_cannot_access_admin_routes(client, login, respondent_user):
    login(respondent_user.email)
    assert client.get("/admin/users").status_code == 403
    assert client.get("/admin/organizations").status_code == 403
    assert client.get("/admin/audit").status_code == 403


def test_admin_can_access_admin_routes(client, login, admin_user):
    login(admin_user.email)
    assert client.get("/admin/users").status_code == 200
    assert client.get("/admin/organizations").status_code == 200
    assert client.get("/admin/audit").status_code == 200


def test_unknown_public_uuid_returns_not_found_not_internal_id(client, login, admin_user):
    login(admin_user.email)
    response = client.get(f"/admin/organizations/{uuid4()}/edit")
    assert response.status_code == 404
