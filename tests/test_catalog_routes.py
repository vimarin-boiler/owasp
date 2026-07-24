def test_catalog_requires_admin(client, login, respondent_user):
    login(respondent_user.email)
    assert client.get("/catalog/").status_code == 403
    assert client.get("/catalog/questions").status_code == 403
    assert client.get("/catalog/imports/new").status_code == 403


def test_admin_can_open_catalog_pages(client, login, admin_user):
    login(admin_user.email)
    assert client.get("/catalog/").status_code == 200
    assert client.get("/catalog/functions").status_code == 200
    assert client.get("/catalog/practices").status_code == 200
    assert client.get("/catalog/streams").status_code == 200
    assert client.get("/catalog/levels").status_code == 200
    assert client.get("/catalog/answer-sets").status_code == 200
    assert client.get("/catalog/questions").status_code == 200
    assert client.get("/catalog/versions").status_code == 200
