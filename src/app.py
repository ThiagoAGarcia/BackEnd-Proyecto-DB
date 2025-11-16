from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from encrypt import hash_pwd
from config import config
from db import connection
from functools import wraps


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})

app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['JSONIFY_MIMETYPE'] = "application/json; charset=utf-8"

@app.after_request
def set_charset(response):
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

app.config.from_object(config['development'])
SECRET_KEY = 'JWT_SECRET_KEY=dIeocMZ1BzPxMcgmkLLPweME31lpx4XP3bsAXpqgt3SLrpKF2a0X6cdUOYr7joIJQwgcL1ht3GFpijm8qFcm4pHyAjie0rCpWEbqUEyYB4W5p36YjqYLhykwjIctJmcoQwF7R8uL9Z3eC34jlgki9dA57EuzT06E6gamcrHbJSmYykfkDwOE5uEeerYGQqzKBFOw9esDhiC1g0v0gWtTcDEPbbg6XMlxhe4MKgZsTfyb7rvUyLRYITcFykegU2tCZDKY'



def user_has_role(*allowed_roles):
    """
    Devuelve True si el usuario autenticado tiene
    al menos uno de los roles pasados.
    """
    roles = getattr(request, 'roles', None)
    if roles is None:
        role = getattr(request, 'role', None)
        roles = [role] if role else []
    return any(r in roles for r in allowed_roles)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({
                'success': False,
                'description': 'Token requerido'
            }), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

            request.role = data.get('role')
            request.roles = data.get('roles', [request.role] if data.get('role') else [])
            request.ci = data['ci']
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'description': 'El token ha expirado'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'description': 'Token inválido'
            }), 401

        return f(*args, **kwargs)
    return decorated


def pageNotFound(error):
    return "<h1>La página que buscas no existe.</h1>"


# Conseguir todas las sanciones de un usuario por mail
@app.route('/user/<mail>/sanctions', methods=['GET'])
@token_required
def getUserMailSanctions(mail):
    try:
        # solo bibliotecario o admin
        if not user_has_role("librarian", "administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                u.mail, 
                s.description, 
                GREATEST(DATEDIFF(s.endDate, CURRENT_DATE), 0) AS dias_restantes, 
                s.startDate, 
                s.endDate
            FROM sanction s
            JOIN user u ON s.ci = u.ci
            WHERE u.mail = %s
        """, (mail,))

        results = cursor.fetchall()
        cursor.close()

        sanctions = []
        for row in results:
            sanctions.append({
                'mail': row['mail'],
                'description': row['description'],
                'dias_restantes': row['dias_restantes'],
                'startDate': row['startDate'],
                'endDate': row['endDate']
            })

        return jsonify({'sanctions': sanctions, 'success': True}), 200

    except Exception as ex:
        return jsonify({'description': 'Error', 'error': str(ex)}), 500


# Conseguir todas las sanciones de un usuario por ci
@app.route('/user/<ci>/sanctions', methods=['GET'])
@token_required
def getUserCiSanctions(ci):
    try:
        if not user_has_role("librarian", "administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()
        ci = int(ci)

        cursor.execute("""
            SELECT s.description, GREATEST(DATEDIFF(s.endDate, CURRENT_DATE), 0) AS dias_restantes, s.startDate, s.endDate
            FROM sanction s
            WHERE s.ci = %s
        """, (ci,))

        results = cursor.fetchall()
        cursor.close()

        sanctions = []
        for row in results:
            sanctions.append({
                'description': row['description'],
                'dias_restantes': row['dias_restantes'],
                'startDate': row['startDate'],
                'endDate': row['endDate']
            })

        return jsonify({'sanctions': sanctions, 'success': True}), 200

    except Exception as ex:
        conn.rollback()
        return jsonify({
            'success': False,
            'description': 'No se pudieron ver tus sanciones',
            'error': str(ex)
        }), 500


# Conseguir todas las sanciones de un usuario por token
@app.route('/user/sanctions', methods=['GET'])
@token_required
def getMySanctions():
    try:
        # solo estudiantes y docentes
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()
        ci = request.ci

        cursor.execute("""
            SELECT s.description, GREATEST(DATEDIFF(s.endDate, CURRENT_DATE), 0) AS dias_restantes, s.startDate, s.endDate
            FROM sanction s
            WHERE s.ci = %s
        """, (ci,))

        results = cursor.fetchall()
        cursor.close()

        sanctions = []
        for row in results:
            sanctions.append({
                'description': row['description'],
                'dias_restantes': row['dias_restantes'],
                'startDate': row['startDate'],
                'endDate': row['endDate']
            })

        return jsonify({'sanctions': sanctions, 'success': True}), 200

    except Exception as ex:
        conn.rollback()
        return jsonify({
            'success': False,
            'description': 'No se pudieron ver tus sanciones',
            'error': str(ex)
        }), 500


# Insertar nuevas carreras
@app.route('/careerInsert', methods=['POST'])
@token_required
def createCareer():
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        data = request.get_json()
        careerName = data.get('careerName')
        planYear = data.get('planYear')
        facultyId = data.get('facultyId')
        type_ = data.get('type')

        if not all([careerName, planYear, facultyId, type_]):
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400

        if type_ not in ['Grado', 'Posgrado']:
            return jsonify({
                'success': False,
                'description': 'Tipo de carrera inválido'
            }), 400

        conn = connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO career (careerName, planYear, facultyId, type) VALUES (%s, %s, %s, %s)",
            (careerName, planYear, facultyId, type_)
        )
        conn.commit()
        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Carrera creada correctamente'
        }), 201

    except Exception as ex:
        conn.rollback()
        return jsonify({
            'success': False,
            'description': 'Error al crear la carrera',
            'error': str(ex)
        }), 500


# Conseguir todos los usuarios que estudien cierta carrera
@app.route('/user/<careerID>', methods=['GET'])
@token_required
def getUserByCareer(careerID):
    try:
        conn = connection()
        cursor = conn.cursor()
        SQL = """
            SELECT u.name, u.lastName
            FROM user u
            JOIN student s ON u.ci = s.ci
            WHERE s.careerId = %s
        """
        cursor.execute(SQL, (careerID,))
        queryResults = cursor.fetchall()
        cursor.close()

        if queryResults:
            users = [{'name': row['name'], 'lastName': row['lastName']} for row in queryResults]
            return jsonify({
                'success': True,
                'users': users,
                'message': 'Usuarios encontrados.'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'No existen usuarios para esa carrera.'
            }), 404

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'Error al obtener usuarios por carrera',
            'error': str(ex)
        }), 500


# Conseguir todos los usuarios
@app.route('/users', methods=['GET'])
@token_required
def getUsers():
    try:
        ciUser = request.ci
        conn = connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.ci, u.name, u.lastName 
            FROM user u
            JOIN login l ON u.mail = l.mail
            WHERE u.ci != %s
        ''', (ciUser,))
        queryResults = cursor.fetchall()

        tables = ['student', 'professor', 'librarian', 'administrator']
        users = []

        for row in queryResults:
            ci = row['ci']
            roles = []

            for table in tables:
                cursor.execute(f"SELECT 1 FROM {table} WHERE ci = %s LIMIT 1", (ci,))
                if cursor.fetchone():
                    roles.append(table)

            if not roles:
                roles = ['unknown']

            users.append({
                'ci': row['ci'],
                'name': row['name'],
                'lastName': row['lastName'],
                'roles': roles
            })

        output = jsonify({'users': users, 'success': True})
        output.headers.add("Access-Control-Allow-Origin", "*")
        return output

    except Exception as ex:
        return jsonify({'description': 'Error', 'error': str(ex)})


# Conseguir todas las carreras
@app.route('/career', methods=['GET'])
def getCareers():
    try:
        conn = connection()
        cursor = conn.cursor()
        cursor.execute("SELECT careerId, careerName, planYear, facultyId, type FROM career")
        results = cursor.fetchall()
        cursor.close()

        careers = []
        for row in results:
            careers.append({
                'careerId': row['careerId'],
                'careerName': row['careerName'],
                'planYear': row['planYear'],
                'facultyId': row['facultyId'],
                'type': row['type']
            })

        return jsonify({'careers': careers, 'success': True}), 200

    except Exception as ex:
        return jsonify({'success': False, 'description': 'Error', 'error': str(ex)}), 500


@app.route('/deleteUserByCi/<ci>', methods=['DELETE'])
@token_required
def deleteUserByCi(ci):
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado"
            }), 401

        ci = int(ci)

        conn = connection()
        cursor = conn.cursor()

    
        cursor.execute("SELECT mail FROM user WHERE ci = %s", (ci,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return jsonify({
                "success": False,
                "description": f"Usuario con CI {ci} no encontrado"
            }), 404

        user_mail = user["mail"]

        cursor.execute("DELETE FROM login WHERE mail = %s", (user_mail,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "description": f"Usuario {ci} eliminado correctamente"
        }), 200

    except Exception as ex:
        try:
            conn.rollback()
            cursor.close()
            conn.close()
        except:
            pass
        
        return jsonify({
            "success": False,
            "description": "Error al intentar eliminar el usuario del login",
            "error": str(ex)
        }), 500


# Registro de usuario
@app.route('/register', methods=['POST'])
def postRegister():
    try:
        data = request.get_json()

        ci = data.get('ci')
        name = data.get('name')
        lastname = data.get('lastName')
        email = data.get('email')
        password = data.get('password')
        careerId = data.get('career')
        second_career = data.get('secondCareer')
        campus = data.get('campus')

        if not all([ci, name, lastname, email, password, careerId, campus]):
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400

        if len(ci) != 8:
            return jsonify({
                'success': False,
                'description': 'ci invalida'
            }), 400

        valueCheck = 0
        digitoVerificador = ci[7]
        multiplicador = '2987634'
        for i in range(len(ci) - 1):
            valueCheck += int(ci[i]) * int(multiplicador[i])
        digitoVerificadorChequeada = valueCheck % 10
        digitoVerificadorChequeada = (10 - digitoVerificadorChequeada) % 10


        if int(digitoVerificador) != int(digitoVerificadorChequeada):
            return jsonify({
                'success': False,
                'description': 'La ci es invalida'
            }), 400



        if len(password) <= 8:
            return jsonify({
                'success': False,
                'description': 'La contraseña es muy corta (mínimo 9 caracteres)'
            }), 400

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("SELECT ci FROM user WHERE ci = %s", (ci,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({
                'success': False,
                'description': 'La cédula ya está en uso'
            }), 409

        cursor.execute("SELECT mail FROM user WHERE mail = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({
                'success': False,
                'description': 'El correo electrónico ya está en uso'
            }), 409

        cursor.execute("SELECT careerId FROM career WHERE careerId = %s", (careerId,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            return jsonify({
                'success': False,
                'description': f'No se encontró la carrera \"{careerId}\"'
            }), 404

        careerId = result['careerId']

        passwordHash = hash_pwd(password)

        cursor.execute(
            "INSERT INTO user (ci, name, lastName, mail) VALUES (%s, %s, %s, %s)",
            (ci, name, lastname, email)
        )

        cursor.execute(
            "INSERT INTO login (mail, password) VALUES (%s, %s)",
            (email, passwordHash)
        )

        cursor.execute(
            "INSERT INTO student (ci, careerId, campus) VALUES (%s, %s, %s)",
            (ci, careerId, campus)
        )

        if second_career:
            cursor.execute(
                "INSERT INTO student (ci, careerId) VALUES (%s, %s)",
                (ci, second_career)
            )

        conn.commit()
        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Usuario registrado correctamente'
        }), 201

    except Exception as ex:
        conn.rollback()
        print("ERROR EN /register:", ex)
        return jsonify({
            'success': False,
            'description': 'Error al registrar el usuario',
            'error': str(ex)
        }), 500

@app.route('/getUserGroupRequest', methods=['GET'])
@token_required
def getUserGroupRequest():
    try:
       ci = request.ci
       conn = connection()
       cursor = conn.cursor()

       cursor.execute("SELECT studyGroup.studyGroupName, groupRequest.requestDate, studyGroup.studyGroupId FROM groupRequest JOIN studyGroup on studyGroup.studyGroupId = groupRequest.studyGroupId WHERE groupRequest.status = 'Pendiente' AND receiver = %s", (ci,))
       result = cursor.fetchall()


       if not result:
            return jsonify({
                'success': True,
                'grupoRequest': []
            }), 200

       return jsonify({
           'success': True,
           'grupoRequest': result
       }), 200

    except Exception as ex:
        return jsonify({'success' : False, 'description': str(ex)}), 404
# Registro de usuarios por administrador
@app.route('/registerAdmin', methods=['POST'])
@token_required 
def postRegisterAdmin():
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        data = request.get_json()

        ci = data.get('ci')
        name = data.get('name')
        lastname = data.get('lastname')
        email = data.get('email')
        password = data.get('password')
        career_name = data.get('career')
        second_career = data.get('secondCareer')

        if not all([ci, name, lastname, email, password, career_name]):
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400

        if len(ci) != 8:
            return jsonify({
                'success': False,
                'description': 'ci invalida'
            }), 400

        valueCheck = 0
        digitoVerificador = ci[7]
        multiplicador = '2987634'
        for i in range(len(ci) - 1):
            valueCheck += int(ci[i]) * int(multiplicador[i])
        digitoVerificadorChequeada = valueCheck % 10
        digitoVerificadorChequeada = (10 - digitoVerificadorChequeada) % 10

        if int(digitoVerificador) != int(digitoVerificadorChequeada):
            return jsonify({
                'success': False,
                'description': 'La ci es invalida'
            }), 400

        if len(password) <= 8:
            return jsonify({
                'success': False,
                'description': 'La contraseña es muy corta (mínimo 9 caracteres)'
            }), 400

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("SELECT careerId FROM career WHERE careerName = %s", (career_name,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            return jsonify({
                'success': False,
                'description': f'No se encontró la carrera \"{career_name}\"'
            }), 404

        careerId = result['careerId']

        passwordHash = hash_pwd(password)

        cursor.execute(
            "INSERT INTO user (ci, name, lastName, mail) VALUES (%s, %s, %s, %s)",
            (ci, name, lastname, email)
        )

        cursor.execute(
            "INSERT INTO login (mail, password) VALUES (%s, %s)",
            (email, passwordHash)
        )

        cursor.execute(
            "INSERT INTO student (ci, careerId) VALUES (%s, %s)",
            (ci, careerId)
        )
        if second_career:
            cursor.execute(
                "INSERT INTO student (ci, careerId) VALUES (%s, %s)",
                (ci, second_career)
            )
        conn.commit()
        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Usuario registrado correctamente'
        }), 201

    except Exception as ex:
        conn.rollback()
        print("ERROR EN /registerAdmin:", ex)
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

        if not email or not password:
            return jsonify({
                'success': False,
                'description': 'Faltan email o contraseña'
            }), 400

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("SELECT password FROM login WHERE mail = %s", (email,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            return jsonify({'success': False, 'description': 'Credenciales inválidas'}), 401

        stored_hash = result['password']
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode()

        if not bcrypt.checkpw(password.encode(), stored_hash):
            cursor.close()
            return jsonify({'success': False, 'description': 'Credenciales inválidas'}), 401

        cursor.execute("SELECT ci FROM user WHERE mail = %s", (email,))
        ci_result = cursor.fetchone()
        if not ci_result:
            cursor.close()
            return jsonify({'success': False, 'description': 'Usuario no encontrado'}), 404

        ci = ci_result['ci']

        
        roles = []
        tables = ['student', 'professor', 'librarian', 'administrator']
        for table in tables:
            cursor.execute(f"SELECT ci FROM {table} WHERE ci = %s", (ci,))
            if cursor.fetchone():
                roles.append(table)

        if not roles:
            roles = ['unknown']
            
        prioridad = ['administrator', 'librarian', 'professor', 'student']
        main_role = None
        for r in prioridad:
            if r in roles:
                main_role = r
                break
        if not main_role:
            main_role = roles[0]

        now = datetime.now(timezone.utc)
        access_payload = {
            'email': email,
            'ci': ci,
            'role': main_role, 
            'roles': roles,
            'exp': now + timedelta(minutes=120)
        }

        access_token = jwt.encode(access_payload, SECRET_KEY, algorithm='HS256')

        cursor.close()

        return jsonify({
            'success': True,
            'access_token': access_token,
            'role': main_role,
            'roles': roles,
            'ci': ci,
            'description': 'Login correcto'
        }), 200

    except Exception as ex:
        print("ERROR EN /login:", ex)
        return jsonify({
            'success': False,
            'description': 'Error en el login',
            'error': str(ex)
        }), 500


# Hacer una nueva reserva
@app.route('/newReservation', methods=['POST'])
#@token_required
def newReservation():
    try:
        data = request.get_json()
        studyGroupID = data.get('StudyGroupID')
        studyRoomId = data.get('studyRoomId')
        date = data.get('date')
        shiftId = data.get('shiftId')
        reservationCreateDate = datetime.now()
        state = 'Activa'

        if not all([studyGroupID, studyRoomId, date, shiftId]):
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400

        conn = connection()
        cursor = conn.cursor()

        if datetime.strptime(date, "%Y-%m-%d").date() < datetime.now().date():
            cursor.close()
            return jsonify({
                'success': False,
                'description': 'No se puede reservar para una fecha que ya pasó'
            }), 400

        cursor.execute("SELECT studyGroupId FROM studyGroup WHERE studyGroupId = %s", (studyGroupID,))
        result = cursor.fetchone()
        if not result:
            cursor.close()
            return jsonify({
                'success': False,
                'description': f'No se encontró el grupo \"{studyGroupID}\"'
            }), 404

        cursor.execute("SELECT studyRoomId FROM studyRoom WHERE studyRoomId = %s", (studyRoomId,))
        result = cursor.fetchone()
        if not result:
            cursor.close()
            return jsonify({
                'success': False,
                'description': f'No se encontró la sala \"{studyRoomId}\"'
            }), 404

        cursor.execute("SELECT shiftId FROM shift WHERE shiftId = %s", (shiftId,))
        result = cursor.fetchone()
        if not result:
            cursor.close()
            return jsonify({
                'success': False,
                'description': f'No se encontró el turno \"{shiftId}\"'
            }), 404

        cursor.execute("""
            INSERT INTO reservation 
                (studyGroupId, studyRoomId, date, shiftId, assignedLibrarian, reservationCreateDate, state)
            VALUES (%s, %s, %s, %s, null, %s, %s)
        """, (studyGroupID, studyRoomId, date, shiftId, reservationCreateDate.date(), state))

        conn.commit()
        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Reservación creada exitosamente'
        }), 201

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'Error en la creación de la reserva',
            'error': str(ex)
        }), 500


# Conseguir información de un grupo cuando se es parte
@app.route('/myGroup/<groupId>', methods=['GET'])
@token_required
def getGroupUser(groupId):
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()
        ci = request.ci
        groupId = int(groupId)

        cursor.execute("""
            SELECT 1
            FROM studyGroup sg
            LEFT JOIN studyGroupParticipant sgp 
                ON sg.studyGroupId = sgp.studyGroupId
            WHERE sg.studyGroupId = %s
              AND (sg.leader = %s OR sgp.member = %s)
        """, (groupId, ci, ci))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            return jsonify({
                'success': False,
                'description': 'No eres miembro del grupo.'
            }), 404

        cursor.execute("""
            SELECT 
                sg.studyGroupName,
                sg.status,
                sg.leader,
                u.name AS leaderName,
                u.mail AS leaderMail,
                p.member,
                u2.name AS memberName,
                u2.mail AS memberMail
            FROM studyGroup sg
            JOIN user u ON sg.leader = u.ci
            LEFT JOIN studyGroupParticipant p ON sg.studyGroupId = p.studyGroupId
            LEFT JOIN user u2 ON p.member = u2.ci
            WHERE sg.studyGroupId = %s
        """, (groupId,))
        results = cursor.fetchall()
        cursor.close()

        if not results:
            return jsonify({
                'success': False,
                'description': f'No se encontró el grupo con ID {groupId}'
            }), 404

        group_info = {
            'studyGroupName': results[0]['studyGroupName'],
            'status': results[0]['status'],
            'leader': {
                'ci': results[0]['leader'],
                'name': results[0]['leaderName'],
                'mail': results[0]['leaderMail']
            },
            'members': []
        }

        for row in results:
            if row['member'] is not None:
                group_info['members'].append({
                    'ci': row['member'],
                    'name': row['memberName'],
                    'mail': row['memberMail']
                })

        return jsonify({
            'success': True,
            'grupo': group_info
        }), 200

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'Error al obtener la información del grupo',
            'error': str(ex)
        }), 500


# Enviar una solicitud
@app.route('/sendGroupRequest', methods=['POST'])
@token_required
def sendGroupRequest():
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        data = request.get_json()

        ci_sender = request.ci
        studyGroupId = data.get('studyGroupId')
        receiver = data.get('receiver')

        if not all([studyGroupId, receiver]):
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400
        conn = connection()
        cursor = conn.cursor()

        cursor.execute("SELECT ci FROM administrator WHERE ci = %s", (receiver,))
        is_admin = cursor.fetchone()

        cursor.execute("SELECT ci FROM librarian WHERE ci = %s", (receiver,))
        is_librarian = cursor.fetchone()

        if is_admin or is_librarian:
            return jsonify({
                'success': False,
                'description': 'No puedes enviar solicitudes a administradores o bibliotecarios'
            }), 400

        cursor.execute("SELECT leader FROM studyGroup WHERE studyGroupId = %s", (studyGroupId,))
        result = cursor.fetchone()

        leader = result['leader'] if result else None

        if leader != ci_sender:
            return jsonify({
                'success': False,
                'description': 'No eres el líder del equipo'
            }), 400

        cursor.execute("INSERT INTO groupRequest VALUES (%s, %s, DEFAULT, DEFAULT, DEFAULT)", (studyGroupId, receiver,))

        conn.commit()
        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Solicitud realizada correctamente'
        }), 201
    except Exception as ex:
        conn.rollback()
        print("ERROR EN /createGroupRequest:", ex)
        return jsonify({
            'success': False,
            'description': 'Error al realizar la solicitud',
            'error': str(ex)
        }), 500


# Conseguir usuarios por nombre, apellido o mail
@app.route('/users/<name>&<lastName>&<mail>', methods=['GET'])
def getUserByNameLastMail(name, lastName, mail):
    try:
        conn = connection()
        cursor = conn.cursor()
        name = str(name)
        lastName = str(lastName)
        mail = str(mail)

        cursor.execute('''
            SELECT 
                u.ci AS ci, 
                u.name AS name, 
                u.lastName AS lastName, 
                u.mail AS mail, 
                u.profilePicture AS profilePicture
            FROM (SELECT s.ci
            FROM student s
            UNION
            SELECT p.ci
            FROM professor p) ps
            JOIN user u ON ps.ci = u.ci
            WHERE u.name = %s AND u.lastName = %s AND u.mail = %s;
        ''', (name, lastName, mail))
        results = cursor.fetchone()
        cursor.close()

        if not results:
            return jsonify({
                'success': False,
                'description': f'No se pudo encontrar un estudiante con las credenciales {name}, {lastName}, {mail}'
            }), 404
        else:
            estudiante = {
                'userCi': results['ci'],
                'userName': results['name'],
                'userLastName': results['lastName'],
                'userMail': results['mail'],
                'userProfilePicture': results['profilePicture']
            }

            return jsonify({
                'success': True,
                'description': 'Estudiante encontrado.',
                'estudiante': estudiante
            })

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'Error al obtener usuario.',
            'error': str(ex)
        }), 500


# Conseguir todas las salas libres en cierta fecha y edificio
@app.route('/freeRooms/<date>&<building>', methods=['GET'])
def getFreeRooms(date, building):
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT sR.roomName AS Sala, sR.buildingName AS Edificio, s.startTime AS Inicio, s.endTime AS Fin
                FROM studyRoom sR
                JOIN shift s
                WHERE sR.buildingName = %s AND (sR.studyRoomId, s.shiftId) NOT IN (
                    SELECT r.studyRoomId, r.shiftId
                    FROM reservation r
                    WHERE r.date = %s
                )
                ORDER BY Inicio, Fin DESC;
            """

            cursor.execute(query, (building, date))
            free_rooms = cursor.fetchall()

            for room in free_rooms:
                if isinstance(room["Inicio"], (bytes, bytearray)) is False:
                    room["Inicio"] = str(room["Inicio"])
                if isinstance(room["Fin"], (bytes, bytearray)) is False:
                    room["Fin"] = str(room["Fin"])

            return jsonify({
                "success": True,
                "building": building,
                "date": date,
                "freeRooms": free_rooms
            }), 200

    except Exception as e:
        print("Error al obtener salas libres:", e)
        return jsonify({
            "success": False,
            "description": "Error al obtener las salas libres",
            "error": str(e)
        }), 500


# Conseguir todas las reservas de un usuario con mail
@app.route('/user/<mail>/reservations', methods=['GET'])
@token_required
def getUserMailReservations(mail):
    try:
        if not user_has_role("librarian", "administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        with connection.cursor() as cursor:
            query_user = "SELECT ci FROM user WHERE mail = %s"
            cursor.execute(query_user, (mail,))
            user = cursor.fetchone()

            if not user:
                return jsonify({
                    "success": False,
                    "description": "No se encontró un usuario con ese mail."
                }), 404

            ci = user["ci"]

            query_groups = """
                SELECT DISTINCT studyGroup.studyGroupId, studyGroup.studyGroupName
                FROM studyGroup
                LEFT JOIN studyGroupParticipant ON studyGroup.studyGroupId = studyGroupParticipant.studyGroupId
                WHERE studyGroup.leader = %s OR studyGroupParticipant.member = %s
            """
            cursor.execute(query_groups, (ci, ci))
            groups = cursor.fetchall()

            if not groups:
                return jsonify({
                    "success": True,
                    "message": "El usuario no tiene grupos asociados.",
                    "reservations": []
                }), 200

            group_ids = tuple(g["studyGroupId"] for g in groups)

            query_reservations = f"""
                SELECT reservation.studyGroupId, studyGroup.studyGroupName, studyRoom.roomName, studyRoom.buildingName, reservation.date, shift.startTime, shift.endTime, reservation.state, reservation.assignedLibrarian
                FROM reservation
                INNER JOIN studyGroup ON reservation.studyGroupId = studyGroup.studyGroupId
                INNER JOIN studyRoom ON reservation.studyRoomId = studyRoom.studyRoomId
                INNER JOIN shift ON reservation.shiftId = shift.shiftId
                WHERE reservation.studyGroupId IN {group_ids}
                ORDER BY reservation.date DESC
            """

            cursor.execute(query_reservations)
            reservations = cursor.fetchall()

            for r in reservations:
                if isinstance(r["startTime"], timedelta):
                    r["startTime"] = str(r["startTime"])
                if isinstance(r["endTime"], timedelta):
                    r["endTime"] = str(r["endTime"])

            return jsonify({
                "success": True,
                "userMail": mail,
                "reservations": reservations
            }), 200

    except Exception as e:
        print("Error al obtener las reservas del usuario:", e)
        return jsonify({
            "success": False,
            "description": "Error al obtener las reservas del usuario",
            "error": str(e)
        }), 500


# Conseguir todas las reservas de un usuario con cédula
@app.route('/user/reservations', methods=['GET'])
@token_required
def getUserCiReservations():
    try:
        ci = int(request.ci)

        conn = connection()
        cursor = conn.cursor()

        query_groups = """
            SELECT DISTINCT studyGroup.studyGroupId, studyGroup.studyGroupName
            FROM studyGroup
            LEFT JOIN studyGroupParticipant 
                ON studyGroup.studyGroupId = studyGroupParticipant.studyGroupId
            WHERE studyGroup.leader = %s OR studyGroupParticipant.member = %s
        """
        cursor.execute(query_groups, (ci, ci))
        groups = cursor.fetchall()

        if not groups:
            cursor.close()
            conn.close()
            return jsonify({
                "success": True,
                "message": "El usuario no tiene grupos asociados.",
                "reservations": []
            }), 200

        group_ids = tuple(g["studyGroupId"] for g in groups)

        query_reservations = f"""
            SELECT 
                reservation.studyGroupId, 
                studyGroup.studyGroupName, 
                studyRoom.roomName, 
                studyRoom.buildingName, 
                reservation.date, 
                shift.startTime, 
                shift.endTime, 
                reservation.state, 
                reservation.assignedLibrarian
            FROM reservation
            INNER JOIN studyGroup 
                ON reservation.studyGroupId = studyGroup.studyGroupId
            INNER JOIN studyRoom 
                ON reservation.studyRoomId = studyRoom.studyRoomId
            INNER JOIN shift 
                ON reservation.shiftId = shift.shiftId
            WHERE reservation.studyGroupId IN {group_ids}
            ORDER BY reservation.date DESC
        """

        cursor.execute(query_reservations)
        reservations = cursor.fetchall()

        from datetime import timedelta
        for r in reservations:
            if isinstance(r["startTime"], timedelta):
                r["startTime"] = str(r["startTime"])
            if isinstance(r["endTime"], timedelta):
                r["endTime"] = str(r["endTime"])

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "userCi": ci,
            "reservations": reservations
        }), 200

    except Exception as e:
        print("Error al obtener las reservas del usuario:", e)
        return jsonify({
            "success": False,
            "description": "Error al obtener las reservas del usuario",
            "error": str(e)
        }), 500


# Conseguir todas las reservas de un usuario con token (alias)
@app.route('/myReservations', methods=['GET'])
@token_required
def getUserReservations():
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        ci = request.ci
        with connection.cursor() as cursor:
            query_groups = """
                SELECT DISTINCT studyGroup.studyGroupId, studyGroup.studyGroupName
                FROM studyGroup
                LEFT JOIN studyGroupParticipant ON studyGroup.studyGroupId = studyGroupParticipant.studyGroupId
                WHERE studyGroup.leader = %s OR studyGroupParticipant.member = %s
            """
            cursor.execute(query_groups, (ci, ci))
            groups = cursor.fetchall()

            if not groups:
                return jsonify({
                    "success": True,
                    "message": "El usuario no tiene grupos asociados.",
                    "reservations": []
                }), 200

            group_ids = tuple(g["studyGroupId"] for g in groups)

            query_reservations = f"""
                SELECT reservation.studyGroupId, studyGroup.studyGroupName, studyRoom.roomName, studyRoom.buildingName, reservation.date, shift.startTime, shift.endTime, reservation.state, reservation.assignedLibrarian
                FROM reservation
                INNER JOIN studyGroup ON reservation.studyGroupId = studyGroup.studyGroupId
                INNER JOIN studyRoom ON reservation.studyRoomId = studyRoom.studyRoomId
                INNER JOIN shift ON reservation.shiftId = shift.shiftId
                WHERE reservation.studyGroupId IN {group_ids}
                ORDER BY reservation.date DESC
            """

            cursor.execute(query_reservations)
            reservations = cursor.fetchall()

            for r in reservations:
                if isinstance(r["startTime"], timedelta):
                    r["startTime"] = str(r["startTime"])
                if isinstance(r["endTime"], timedelta):
                    r["endTime"] = str(r["endTime"])

            return jsonify({
                "success": True,
                "userCi": ci,
                "reservations": reservations
            }), 200

    except Exception as e:
        print("Error al obtener las reservas del usuario:", e)
        return jsonify({
            "success": False,
            "description": "Error al obtener las reservas del usuario",
            "error": str(e)
        }), 500
    
# Conseguir todas las reservas en cierta fecha
@app.route('/reservationsToday', methods = ['GET'])
#@token_required
def getReservationsByDate():
    try:
        #if not user_has_role("librarian"):
        #    return jsonify({
        #        "success": False,
        #        "description": "Usuario no autorizado",
        #}), 401
        
        conn = connection()
        cursor = conn.cursor()        
        cursor.execute(''' 
            SELECT 
                DATE_FORMAT(s.startTime, '%H:%i') AS start,
                DATE_FORMAT(s.endTime, '%H:%i') AS end,
                sR.roomName AS studyRoomName,
                sR.buildingName AS building,
                r.studyGroupId AS studyGroupId,
                r.assignedLibrarian AS librarian
            FROM reservation r
            JOIN shift s on r.shiftId = s.shiftId
            JOIN studyRoom sR on r.studyRoomId = sR.studyRoomId
            WHERE r.date = '2025-11-17';
        ''')
        results = cursor.fetchall()
        reservations = []

        if not results:
            return jsonify({
                'success': False,
                'description': 'No se pudieron procesar las reservas.'
            }), 404
        
        for row in results:
            reservations.append({
                "start": str(row['start']),
                "end": str(row['end']),
                "studyRoom": row['studyRoomName'],
                "building": row['building'],
                "studyGroupId": row['studyGroupId'],
                "assignedLibrarian": row['librarian']
            })

        # Esto es para cuando una reserva tiene dos bloques de horario
        index = 0
        while index < len(reservations) - 1:
            if reservations[index]["studyGroupId"] == reservations[index + 1]["studyGroupId"]:
                reservations[index]["end"] = reservations[index + 1]["end"]
                reservations.pop(index + 1)
            else:
                index += 1

        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'description': 'Reservas el día de hoy.',
            'reservations': reservations
        })
        
    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'No se pudo procesar la solicitud.',
            'error': str(ex)
        }), 500
    
@app.route('/manageReservation', methods=['PATCH'])
# @token_required
def patchManageReservation():
    try:
        conn = connection()
        cursor = conn.cursor()

        data = request.get_json()
        studyGroupId = data.get('studyGroupId')
        librarian = data.get('librarian')

        if not all([studyGroupId, librarian]):
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400

        cursor.execute(''' 
            UPDATE reservation
            SET assignedLibrarian = %s
            WHERE assignedLibrarian IS NULL AND studyGroupId = %s;
        ''', [librarian, studyGroupId])

        return jsonify({
            'success': True,
            'description': 'Nueva reserva administrada.'
        }), 200

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'No se pudo procesar la solicitud.',
            'error': str(ex)
        })

@app.route('/unmanageReservation', methods=['PATCH'])
# @token_required
def patchUnmanageReservation():
    try:
        conn = connection()
        cursor = conn.cursor()

        data = request.get_json()
        studyGroupId = data.get('studyGroupId')
        librarian = data.get('librarian')


        if not all([studyGroupId, librarian]):
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400
        
        cursor.execute(''' 
            UPDATE reservation
            SET assignedLibrarian = NULL
            WHERE assignedLibrarian = %s AND studyGroupId = %s;
        ''', [librarian, studyGroupId])

        return jsonify({
            'success': True,
            'description': 'Se dejó de administrar la reserva.'
        }), 200

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': "No se pudo procesar la solicitud.",
            'error': str(ex)
        })
# Conseguir todas las solicitudes de un usuario
@app.route('/myGroupRequests', methods=['GET'])
@token_required
def getAllUserGroupRequests():
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()
        ci = request.ci

        cursor.execute('''
            SELECT 
                gR.status AS requestStatus,
                gR.isValid AS requestValidity, 
                gR.requestDate AS requestDate, 
                sG.leader AS groupLeader, 
                sG.studyGroupName AS groupName, 
                sG.status AS groupStatus
            FROM groupRequest gR
            JOIN studyGroup sG ON gR.studyGroupId = sG.studyGroupId
            WHERE gR.receiver = %s;
        ''', (ci,))
        results = cursor.fetchall()
        groupRequests = []

        if not results:
            return jsonify({
                'success': False,
                'description': f'No se pudieron encontrar las solicitudes para el usuario con cédula {ci}'
            }), 404
        for row in results:
            groupRequests.append({
                'requestStatus': row['requestStatus'],
                'requestValidity': row['requestValidity'],
                'requestDate': row['requestDate'],
                'groupLeader': row['groupLeader'],
                'groupName': row['groupName'],
                'groupStatus': row['groupStatus']
            })
        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Solicitudes encontradas.',
            'notificaciones': groupRequests
        })

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'No se pudieron encontrar las solicitudes.',
            'error': str(ex)
        }), 500

# Ver todos los grupos en los que uno es parte como lider o integrante
@app.route('/myGroups', methods=['GET'])
@token_required
def getAllGroups():
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()
        ci = request.ci

        cursor.execute(''' 
            SELECT 
                sg.studyGroupName AS groupName,
                sg.status AS groupStatus,
                leader.name AS leaderName,
                leader.lastName AS leaderLastName,
                leader.mail AS leaderMail
            FROM studyGroup sg
            JOIN user leader ON sg.leader = leader.ci
            WHERE sg.leader = %s AND sg.status = 'Activo'

            UNION ALL

            SELECT 
                sg.studyGroupName AS groupName,
                sg.status AS groupStatus,
                leader.name AS leaderName,
                leader.lastName AS leaderLastName,
                leader.mail AS leaderMail
            FROM studyGroupParticipant sGp
            JOIN studyGroup sg ON sGp.studyGroupId = sg.studyGroupId
            JOIN user leader ON sg.leader = leader.ci 
            WHERE sGp.member = %s AND sg.status = 'Activo';
        ''', (ci, ci))

        results = cursor.fetchall()
        if not results:
            return jsonify({
                'success': False,
                'description': 'No se pudieron encontrar los grupos.'
            })

        groups = []
        for row in results:
            groups.append({
                'groupName': row['groupName'],
                'groupState': row['groupStatus'],
                'leaderName': row['leaderName'],
                'leaderLastName': row['leaderLastName'],
                'leaderMail': row['leaderMail']
            })
        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Grupos encontrados.',
            'grupos': groups
        })
    except Exception as ex:
        return jsonify({
            'success': False,
            'error': str(ex)
        }), 500

# Eliminar un grupo cuando se es el líder
@app.route('/deleteMyGroup/<groupId>', methods=['DELETE'])
@token_required
def deleteGroupById(groupId):
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()
        ci = request.ci
        groupId = int(groupId)

        cursor.execute(''' 
            SELECT sG.leader AS leader
            FROM studyGroup sG
            WHERE sG.studyGroupId = %s
        ''', (groupId,))
        leaderData = cursor.fetchone()
        leaderCi = leaderData['leader']

        if ci != leaderCi:
            return jsonify({
                'success': False,
                'description': 'Solo se puede eliminar un grupo si eres el líder.'
            })
        else:
            cursor.execute(''' 
                DELETE FROM studyGroup
                WHERE studyGroupId = %s AND status = 'Activo';
            ''', (groupId,))
            cursor.close()

            return jsonify({
                'success': True,
                'description': 'El grupo se ha eliminado con éxito.'
            })

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'No se ha podido eliminar el grupo.',
            'error': str(ex)
        })


# Conseguir información de un grupo donde se es el líder o un miembro
@app.route('/getMyGroupInformation/<groupId>', methods=['GET'])
@token_required
def getGroupInformation(groupId):
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()
        ci = request.ci
        groupId = int(groupId)

        cursor.execute("""
            SELECT 1
            FROM studyGroup sg
            LEFT JOIN studyGroupParticipant sgp 
                ON sg.studyGroupId = sgp.studyGroupId
            WHERE sg.studyGroupId = %s
              AND (sg.leader = %s OR sgp.member = %s)
        """, (groupId, ci, ci))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            return jsonify({
                'success': False,
                'description': 'No eres miembro del grupo'
            }), 403

        cursor.execute("""
            SELECT 
                sg.studyGroupId,
                sg.studyGroupName,
                sg.status,
                u_leader.ci AS leaderCi,
                CONCAT(u_leader.name, ' ', u_leader.lastname) AS leaderName
            FROM studyGroup sg
            JOIN user u_leader ON sg.leader = u_leader.ci
            WHERE sg.studyGroupId = %s
        """, (groupId,))
        group_info = cursor.fetchone()

        cursor.execute("""
            SELECT 
                u.ci,
                CONCAT(u.name, ' ', u.lastname) AS fullName
            FROM studyGroupParticipant sgp
            JOIN user u ON sgp.member = u.ci
            WHERE sgp.studyGroupId = %s
        """, (groupId,))
        members = cursor.fetchall()

        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Información del grupo obtenida con éxito',
            'data': {
                'studyGroupId': group_info['studyGroupId'],
                'studyGroupName': group_info['studyGroupName'],
                'status': group_info['status'],
                'leader': {
                    'ci': group_info['leaderCi'],
                    'name': group_info['leaderName']
                },
                'members': members
            }
        }), 200

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'No se pudo obtener la información del grupo.',
            'error': str(ex)
        }), 500


# Aceptar una solicitud
@app.route('/group/<groupId>/acceptRequest', methods=['PATCH'])
@token_required
def acceptUserRequest(groupId):
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()
        ci = request.ci
        groupId = int(groupId)


        cursor.execute(''' 
            UPDATE groupRequest
            SET status = 'Aceptada'
            WHERE receiver = %s AND studyGroupId = %s;
        ''', (ci, groupId))

    
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'description': 'No se encontró una solicitud pendiente para este grupo.'
            }), 404

    
        cursor.execute(''' 
            INSERT INTO studyGroupParticipant (studyGroupId, member)
            VALUES (%s, %s)
        ''', (groupId, ci))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'description': 'Se ha aceptado la solicitud.'
        }), 200

    except Exception as ex:
        try:
            conn.rollback()
        except:
            pass

        return jsonify({
            'success': False,
            'description': 'No se pudo procesar la solicitud.',
            'error': str(ex)
        }), 500


# Rechazar una solicitud
@app.route('/group/<groupId>/denyRequest', methods=['PATCH'])
@token_required
def denyGroupRequest(groupId):
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()
        ci = request.ci
        groupId = int(groupId)

        cursor.execute(''' 
            UPDATE groupRequest
            SET status = 'Rechazada'
            WHERE receiver = %s AND studyGroupId = %s;
        ''', (ci, groupId))
        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Se ha rechazado la solicitud.'
        })
    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'No se pudo procesar la solicitud.'
        }), 500


# Eliminar un usuario de un grupo
@app.route('/deleteUser/<studyGroupId>/<userId>', methods=['DELETE'])
@token_required
def deleteUserById(studyGroupId, userId):
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()

        ci_sender = request.ci

        cursor.execute("SELECT leader, status FROM studyGroup WHERE studyGroupId = %s", (studyGroupId,))
        result = cursor.fetchone()

        if not result:
            return jsonify({
                "success": False,
                "description": "El grupo no existe"
            }), 404

        leader = result["leader"]
        status = result["status"]

        if status != 'Activo':
            return jsonify({
                "success": False,
                "description": "No se pueden eliminar usuarios de un grupo inactivo"
            }), 400

        if leader != ci_sender:
            return jsonify({
                "success": False,
                "description": "No sos el lider del grupo, no podes eliminar usuarios"
            }), 403

        cursor.execute("""
            SELECT * FROM studyGroupParticipant
            WHERE studyGroupId = %s AND member = %s
        """, (studyGroupId, userId))
        member = cursor.fetchone()

        if not member:
            return jsonify({
                "success": False,
                "description": "El usuario no pertenece a este grupo"
            }), 404

        cursor.execute("""
            DELETE FROM studyGroupParticipant
            WHERE studyGroupId = %s AND member = %s
        """, (studyGroupId, userId))
        conn.commit()

        return jsonify({
            "success": True,
            "description": f"Usuario {userId} eliminado del grupo {studyGroupId} correctamente"
        }), 200

    except Exception as e:
        print("Error al eliminar usuario del grupo", e)
        return jsonify({
            "success": False,
            "description": "Error al eliminar usuario del grupo",
            "error": str(e)
        }), 500

# Conseguir todas las campus
@app.route('/campus', methods=['GET'])
def getCampus():
    try:
        conn = connection()
        cursor = conn.cursor()
        cursor.execute("SELECT campusName FROM campus")
        results = cursor.fetchall()
        cursor.close()

        campus = []
        for row in results:
            campus.append({
                'campusName': row['campusName'],
            })

        return jsonify({'campus': campus, 'success': True}), 200

    except Exception as ex:
        return jsonify({'success': False, 'description': 'Error', 'error': str(ex)}), 500

@app.route('/userByCi', methods=['GET'])
@token_required
def getUserbyCi():
    try:
        role = request.role
        ci = request.ci
        conn = connection()
        cursor = conn.cursor()
        result = None

        if role == 'administrator':
            cursor.execute(
                f"""
                SELECT u.ci, u.name, u.lastName, u.mail 
                FROM user u
                JOIN administrator ON administrator.ci = u.ci 
                WHERE u.ci = %s
                """,
                (ci,)
            )
            result = cursor.fetchone()
        elif role == 'librarian':
            cursor.execute(
                f"""
                SELECT u.ci, u.name, u.lastName, u.mail, buildingName
                FROM user u
                JOIN librarian ON librarian.ci = u.ci 
                WHERE u.ci = %s
                """,
                (ci,)
            )
            result = cursor.fetchone()
        elif role == 'professor':
            cursor.execute(
                f"""
                SELECT u.ci, u.name, u.lastName, u.mail, campus
                FROM user u
                JOIN professor ON professor.ci = u.ci 
                WHERE u.ci = %s
                """,
                (ci,)
            )
            result = cursor.fetchone()
        else:
            cursor.execute(
                f"""
                SELECT u.ci, u.name, u.lastName, u.mail, campus, careerId
                FROM user u
                JOIN student ON student.ci = u.ci 
                WHERE u.ci = %s
                """,
                (ci,)
            )
            result = cursor.fetchone()
        

        if not result:
            cursor.close()
            return jsonify({
                'success': False,
                'description': 'usuario no encontrado'
            }), 403

        cursor.close()
        return jsonify({
            "success": True,
            "user": result
        }), 200
    
    except Exception as ex:
        return jsonify({'success': False, 'description': 'Error', 'error': str(ex)}), 500

#Buscar
@app.route('/searchUsersRequest', methods=['GET'])
@token_required
def searchUsersRequest():
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        role = request.role
        current_ci = request.ci

        conn = connection()
        cursor = conn.cursor()

        text = request.args.get("text", "").strip()
        search = f"%{text}%"

        if role == 'student':
            cursor.execute("""
                SELECT 
                    u.ci, u.name, u.lastName, u.mail
                FROM user u
                INNER JOIN student s ON u.ci = s.ci
                WHERE 
                    u.mail LIKE %s
                    AND u.ci <> %s
                ORDER BY u.name ASC
            """, (search, current_ci))

        if role == 'professor':
            cursor.execute("""
                SELECT 
                    u.ci, u.name, u.lastName, u.mail,
                    CASE
                        WHEN s.ci IS NOT NULL THEN 'student'
                        WHEN p.ci IS NOT NULL THEN 'professor'
                    END AS role
                FROM user u
                LEFT JOIN student s ON u.ci = s.ci
                LEFT JOIN professor p ON u.ci = p.ci
                WHERE 
                    u.mail LIKE %s
                    AND u.ci <> %s
                    AND (s.ci IS NOT NULL OR p.ci IS NOT NULL)
                ORDER BY u.name ASC
            """, (search, current_ci))

        users = cursor.fetchall()
        cursor.close()

        return jsonify({
            "success": True,
            "users": users
        })

    except Exception as ex:
        return jsonify({'success': False, 'description': 'Error', 'error': str(ex)}), 500


@app.route('/createGroup', methods=['POST'])
@token_required
def createGroup():
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        data = request.json
        nombre = data.get("studyGroupName")
        leader_ci = request.ci

        if not nombre:
            return jsonify({
                "success": False,
                "description": "El nombre del grupo es obligatorio"
            }), 400

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO studyGroup (studyGroupName, leader)
            VALUES (%s, %s)
        """, (nombre, leader_ci))
        conn.commit()

        cursor.execute("""
            SELECT studyGroupId, studyGroupName, leader, status
            FROM studyGroup
            WHERE studyGroupName = %s AND leader = %s
            ORDER BY studyGroupId DESC LIMIT 1
        """, (nombre, leader_ci))

        row = cursor.fetchone()
        cursor.close()

        return jsonify({
            "success": True,
            "description": "Grupo creado correctamente",
            "grupo": {
                "id": row["studyGroupId"],
                "groupName": row["studyGroupName"],
                "leader": row["leader"],
                "status": row["status"]
            }
        })
    except Exception as ex:
        return jsonify({
            "success": False,
            "error": str(ex)
        }), 500


@app.route('/myCareer', methods=['GET'])
@token_required
def getMyCareer():
    try:
        # sólo estudiantes
        if not user_has_role("student"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado"
            }), 401

        ci = request.ci

        conn = connection()
        cursor = conn.cursor()

        SQL = """
            SELECT 
                c.careerName,
                c.type,
                c.planYear,
                f.facultyName
            FROM student s
            JOIN career c   ON s.careerId = c.careerId
            JOIN faculty f  ON c.facultyId = f.facultyId
            WHERE s.ci = %s
        """

        cursor.execute(SQL, (ci,))
        results = cursor.fetchall()
        cursor.close()

        if not results:
            return jsonify({
                "success": False,
                "description": "El usuario no tiene carreras asociadas"
            }), 404

        careers = []
        for row in results:
            careers.append({
                "careerName":  row["careerName"],
                "type":        row["type"],
                "planYear":    row["planYear"],
                "facultyName": row["facultyName"]
            })

        return jsonify({
            "success": True,
            "ci": ci,
            "careers": careers
        }), 200

    except Exception as ex:
        return jsonify({
            "success": False,
            "description": "Error al obtener la información de la carrera",
            "error": str(ex)
        }), 500


if __name__ == '__main__':
    app.register_error_handler(404, pageNotFound)
