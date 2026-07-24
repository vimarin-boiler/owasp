from app.services.organization_service import organization_service


def test_organization_slugs_are_unique(app, admin_user):
    with app.app_context():
        first = organization_service.create(
            name="Cliente Ágil",
            legal_name=None,
            tax_identifier=None,
            description=None,
            actor_id=admin_user.id,
        )
        second = organization_service.create(
            name="Cliente Agil",
            legal_name=None,
            tax_identifier=None,
            description=None,
            actor_id=admin_user.id,
        )
        assert first.slug == "cliente-agil"
        assert second.slug == "cliente-agil-2"
        assert first.public_id != second.public_id
