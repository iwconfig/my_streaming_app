from app import create_app

app = create_app()

if __name__ == '__main__':
    # Use Flask's built-in server for development
    # For production, use a production-ready WSGI server like Gunicorn or uWSGI
    app.run(debug=True) # debug=True enables auto-reloading and debugger
