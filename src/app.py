from datetime import datetime, timedelta, timezone

import bcrypt
from flask import Flask, jsonify, request
from config import config
import jwt
import pymysql
from encrypt import hash_pwd



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

@app.route('/register', methods=['POST'])
def postRegister():
    try:
        data = request.get_json()

        ci = data.get('ci')
        name = data.get('name')
        lastname = data.get('lastname')
        email = data.get('email')
        password = data.get('password')
        career_name = data.get('career')


        if not all([ci, name, lastname, email, password, career_name]):
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400


        if len(password) <= 8:
            return jsonify({
                'success': False,
                'description': 'La contraseña es muy corta (mínimo 9 caracteres)'
            }), 400

        cursor = connection.cursor()


        cursor.execute("SELECT careerId FROM career WHERE careerName = %s", (career_name,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            return jsonify({
                'success': False,
                'description': f'No se encontró la carrera "{career_name}"'
            }), 404

        careerId = result[0]

        passwordHash = hash_pwd(password)

        # Insertar primero en user
        cursor.execute(
            "INSERT INTO user (ci, name, lastName, mail) VALUES (%s, %s, %s, %s)",
            (ci, name, lastname, email)
        )

        # Insertar en login
        cursor.execute(
            "INSERT INTO login (mail, password) VALUES (%s, %s)",
            (email, passwordHash)
        )

        # Insertar en student
        cursor.execute(
            "INSERT INTO student (ci, careerId) VALUES (%s, %s)",
            (ci, careerId)
        )

        connection.commit()
        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Usuario registrado correctamente'
        }), 201

    except Exception as ex:
        connection.rollback()
        return jsonify({
            'success': False,
            'description': 'Error al registrar el usuario',
            'error': str(ex)
        }), 500


@app.route('/login', methods=['POST'])
def postLogin():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        cursor = connection.cursor()
        cursor.execute("SELECT password FROM login WHERE mail = %s", (email,))
        result = cursor.fetchone()

        if not result:
            return jsonify({
                'success': False,
                'description': 'Credenciales inválidas'
            }), 401

        stored_hash = result[0].encode() if isinstance(result[0], str) else result[0]

        if not bcrypt.checkpw(password.encode(), stored_hash):
            return jsonify({
                'success': False,
                'description': 'Credenciales inválidas'
            }), 401

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
        }), 200

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'Error en el login',
            'error': str(ex)
        }), 500
if __name__ == '__main__':
    app.register_error_handler(404, pageNotFound)
    app.run()
