from app import create_app, celery

app = create_app()
# Optional: Push context if tasks need it outside the ContextTask wrapper
# app.app_context().push()
