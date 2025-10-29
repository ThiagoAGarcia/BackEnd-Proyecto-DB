from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request
from config import config
import jwt
import pymysql

app = Flask(__name__)
app.config.from_object(config['development'])
SECRET_KEY = 'JWT_SECRET_KEY=dIeocMZ1BzPxMcgmkLLPweME31lpx4XP3bsAXpqgt3SLrpKF2a0X6cdUOYr7joIJQwgcL1ht3GFpijm8qFcm4pHyAjie0rCpWEbqUEyYB4W5p36YjqYLhykwjIctJmcoQwF7R8uL9Z3eC34jlgki9dA57EuzT06E6gamcrHbJSmYykfkDwOE5uEeerYGQqzKBFOw9esDhiC1g0v0gWtTcDEPbbg6XMlxhe4MKgZsTfyb7rvUyLRYITcFykegU2tCZDKY'

connection = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB']
)

def pageNotFound(error):
    return "<h1>La página que buscas no existe.</h1>"

@app.route('/user/<careerID>', methods = ['GET'])
def getUserByCareer(careerID):
    try:
        cursor = connection.cursor()
        SQL = "SELECT name, lastName FROM user WHERE careerID = '{0}'".format(careerID)
        cursor.execute(SQL)
        queryResults = cursor.fetchone()
        if queryResults != None:
           user = {'name': queryResults[0], 'lastName': queryResults[1]}
           return jsonify ({'user': user, 'message': 'Usuarios.'}) 
        else:
            return jsonify({'message': 'No existen.'})
    except Exception as ex:
        return jsonify({'description': 'Error', 'error': str(ex)})

@app.route('/user', methods = ['GET'])
def getUsers():
    try:
        cursor = connection.cursor()
        SQL = "SELECT name, lastName FROM user"
        cursor.execute(SQL)
        queryResults = cursor.fetchall()
        users = []
        for row in queryResults:
            user = {'name': row[0], 'lastName': row[1]}
            users.append(user)
        return jsonify({'users': users, 'desc': 'listo.'})
    except Exception as ex:
        return jsonify({'description': 'Error', 'error': str(ex)})
    
@app.route('/login', methods=['POST'])
def postLogin():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        cursor = connection.cursor()
        SQL = "SELECT * FROM login WHERE mail = %s AND password = %s"
        cursor.execute(SQL, (email, password,))
        queryResults = cursor.fetchall()

        if len(queryResults) > 0:

            now = datetime.now(timezone.utc)

            access_payload = {
                'email': email,
                'type': 'access',
                'exp': now + timedelta(minutes=30)
            }
            refresh_payload = {
                'email': email,
                'type': 'refresh',
                'exp': now + timedelta(days=7)
            }

            access_token = jwt.encode(access_payload, SECRET_KEY, algorithm='HS256')
            refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm='HS256')

            return jsonify({
                'success': True,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'description': 'Login correcto'
            })

        else:
            return jsonify({
                'success': False,
                'description': 'Credenciales inválidas'
            })

    except Exception as ex:
        return jsonify({'description': 'Error', 'error': str(ex)})
if __name__ == '__main__':
    app.register_error_handler(404, pageNotFound)
    app.run()
