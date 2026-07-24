# 5. Estructura completa del proyecto

```text
samm_assessment/
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── enums.py
│   ├── cli.py
│   ├── common/
│   │   ├── decorators.py
│   │   ├── errors.py
│   │   ├── logging.py
│   │   ├── pagination.py
│   │   ├── permissions.py
│   │   ├── security_headers.py
│   │   └── validators.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── identity.py
│   │   ├── organization.py
│   │   ├── catalog.py
│   │   ├── assessment.py
│   │   ├── response.py
│   │   ├── evidence.py
│   │   ├── recommendation.py
│   │   ├── scoring.py
│   │   └── audit.py
│   ├── repositories/
│   │   ├── base.py
│   │   ├── users.py
│   │   ├── organizations.py
│   │   ├── catalog.py
│   │   ├── assessments.py
│   │   ├── responses.py
│   │   ├── evidences.py
│   │   ├── recommendations.py
│   │   └── audit.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── organization_service.py
│   │   ├── catalog_service.py
│   │   ├── questionnaire_version_service.py
│   │   ├── import_service.py
│   │   ├── assessment_service.py
│   │   ├── assignment_service.py
│   │   ├── response_service.py
│   │   ├── review_service.py
│   │   ├── evidence_service.py
│   │   ├── scoring_service.py
│   │   ├── recommendation_service.py
│   │   ├── report_service.py
│   │   ├── backup_service.py
│   │   ├── notification_service.py
│   │   └── audit_service.py
│   ├── storage/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── antivirus.py
│   │   └── mime_detection.py
│   ├── importers/
│   │   ├── base.py
│   │   ├── samm_excel.py
│   │   ├── schemas.py
│   │   └── validators.py
│   ├── exporters/
│   │   ├── excel.py
│   │   ├── pdf.py
│   │   └── printable_html.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── templates/auth/
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── templates/admin/
│   ├── catalog/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── templates/catalog/
│   ├── organizations/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── templates/organizations/
│   ├── assessments/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── templates/assessments/
│   ├── reviews/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── templates/reviews/
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/dashboard/
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/reports/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── errors.py
│   │   ├── schemas.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── organizations.py
│   │       ├── assessments.py
│   │       ├── questions.py
│   │       ├── responses.py
│   │       ├── evidences.py
│   │       ├── results.py
│   │       └── recommendations.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── components/
│   │   ├── errors/
│   │   └── macros/
│   └── static/
│       ├── css/
│       │   ├── app.css
│       │   ├── theme-light.css
│       │   └── theme-dark.css
│       ├── js/
│       │   ├── app.js
│       │   ├── autosave.js
│       │   ├── charts.js
│       │   └── evidence-upload.js
│       ├── img/
│       │   └── .gitkeep
│       ├── icons/
│       └── vendor/
│           ├── bootstrap/
│           ├── bootstrap-icons/
│           └── chartjs/
├── migrations/
├── instance/
│   └── .gitkeep
├── uploads/
│   ├── quarantine/.gitkeep
│   └── evidence/.gitkeep
├── tests/
│   ├── conftest.py
│   ├── factories.py
│   ├── unit/
│   │   ├── test_scoring_service.py
│   │   ├── test_state_transitions.py
│   │   ├── test_file_validation.py
│   │   └── test_excel_parser.py
│   ├── integration/
│   │   ├── test_auth.py
│   │   ├── test_catalog_import.py
│   │   ├── test_assessment_flow.py
│   │   ├── test_review_flow.py
│   │   └── test_reports.py
│   └── security/
│       ├── test_rbac.py
│       ├── test_idor.py
│       ├── test_cross_organization_access.py
│       ├── test_csrf.py
│       └── test_upload_security.py
├── scripts/
│   ├── entrypoint.sh
│   ├── backup.sh
│   └── restore.sh
├── deploy/
│   ├── nginx/samm-assessment.conf
│   └── systemd/samm-assessment.service
├── docs/
├── backups/.gitkeep
├── config.py
├── run.py
├── wsgi.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── alembic.ini
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── LICENSES.md
└── README.md
```
