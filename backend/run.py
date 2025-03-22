from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(app, host='127.0.0.1', debug=True, port=5000, allow_unsafe_werkzeug=True)