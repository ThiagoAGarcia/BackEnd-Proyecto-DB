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
            extra_data = {
                "careerId": None,
                "campus": None,
                "buildingName": None
            }

            # cada rol
            for table in tables:
                cursor.execute(f"SELECT * FROM {table} WHERE ci = %s LIMIT 1", (ci,))
                data = cursor.fetchone()
                if data:
                    roles.append(table)

                    if table == "student":
                        extra_data["careerId"] = data["careerId"]
                        extra_data["campus"] = data["campus"]

                    if table == "professor":
                        extra_data["campus"] = data["campus"]

                    if table == "librarian":
                        extra_data["buildingName"] = data["buildingName"]

            if not roles:
                roles = ["unknown"]

            users.append({
                "ci": row["ci"],
                "name": row["name"],
                "lastName": row["lastName"],
                "roles": roles,
                "careerId": extra_data["careerId"],
                "campus": extra_data["campus"],
                "buildingName": extra_data["buildingName"]
            })

        output = jsonify({"users": users, "success": True})
        output.headers.add("Access-Control-Allow-Origin", "*")
        return output

    except Exception as ex:
        return jsonify({"description": "Error", "error": str(ex)})



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
        name = name.replace(' ', '')
        lastname = data.get('lastName')
        lastname = lastname.replace(' ', '')
        email = data.get('email')
        password = data.get('password')
        confirmPassword = data.get('confirmPassword')
        careerId = data.get('career')
        second_career = data.get('secondCareer')
        campus = data.get('campus')

        if not all([ci, name, lastname, email, password, confirmPassword, careerId, campus]):
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400
        if password != confirmPassword:
            return jsonify({
                'success': False,
                'description': 'Las contraseñas deben coincidir'
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

        cursor.execute('SELECT 1 FROM career WHERE careerId = %s', (careerId,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'description': 'No se encontro la carrera'
            }), 400

        cursor.execute('SELECT 1 FROM campus WHERE campusName = %s', (campus,))
        result = cursor.fetchone()
        valido = email.endswith(("@correo.ucu.edu.uy", "@ucu.edu.uy"))

        if not valido:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'description': 'correo invalido'
            }), 400

        if not result:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'description': 'No se encontro el campus'
            }), 400

        if len(name) < 3 or not name.isalpha():
            return jsonify({
                'success': False,
                'description': 'Formato de nombre invalido'
            }), 400

        if len(lastname) < 3 or not lastname.isalpha():
            return jsonify({
                'success': False,
                'description': 'Formato de apellido invalido'
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


        cursor.execute("SELECT 1 FROM student WHERE ci = %s", (ci,))
        if cursor.fetchone():
            roles.append("student")


        cursor.execute("SELECT 1 FROM professor WHERE ci = %s", (ci,))
        if cursor.fetchone():
            roles.append("professor")


        cursor.execute("SELECT 1 FROM librarian WHERE ci = %s", (ci,))
        if cursor.fetchone():
            roles.append("librarian")


        cursor.execute("SELECT 1 FROM administrator WHERE ci = %s", (ci,))
        if cursor.fetchone():
            roles.append("administrator")

        if not roles:
            roles = ["unknown"]


        prioridad = ['administrator', 'librarian', 'professor', 'student']
        main_role = next((r for r in prioridad if r in roles), roles[0])

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
@token_required
def newReservation():
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        data = request.get_json()
        studyGroupId = data.get('studyGroupId')
        studyRoomId = data.get('studyRoomId')
        date = data.get('date')
        shiftId = data.get('shiftId')
        reservationCreateDate = datetime.now()
        state = 'Activa'

        if not all([studyGroupId, studyRoomId, date, shiftId]):
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

        cursor.execute("SELECT studyGroupId FROM studyGroup WHERE studyGroupId = %s", (studyGroupId,))
        result = cursor.fetchone()
        if not result:
            cursor.close()
            return jsonify({
                'success': False,
                'description': f'No se encontró el grupo \"{studyGroupId}\"'
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
        """, (studyGroupId, studyRoomId, date, shiftId, reservationCreateDate.date(), state))

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
                sg.studyGroupId,
                sg.studyGroupName,
                sg.status,
                sg.leader,
                u.name AS leaderName,
                u.lastName AS leaderLastName,
                u.mail AS leaderMail,
                p.member,
                u2.name AS memberName,
                u2.lastName AS memberLastName,
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
            'id': results[0]['studyGroupId'],
            'studyGroupName': results[0]['studyGroupName'],
            'status': results[0]['status'],
            'leader': {
                'ci': results[0]['leader'],
                'name': results[0]['leaderName'],
                'lastName': results[0]['leaderLastName'],
                'mail': results[0]['leaderMail']
            },
            'members': []
        }

        for row in results:
            if row['member'] is not None:
                group_info['members'].append({
                    'ci': row['member'],
                    'name': row['memberName'],
                    'lastName': row['memberLastName'],
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

        # ACÁ VERIFICA QUE ESTEN LOS DATOS OBLIGATORIOS

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

        # ACÁ VERIFICA QUE EL QUE RECIBE LA SOLICITUD NO SEA UN BIBLIOTECARIO O ADMINISTRADOR (Porque no tiene sentido)
        # SI EL USUARIO TIENE EL ROL ADMIN AUNQUE TAMBIEN SEA USUARIO SE ROMPE, DEBEMOS CHEQUEAR QUE EL USUARIO SEA USER O PROFESOR
        cursor.execute("SELECT ci FROM student WHERE ci = %s", (receiver,))
        is_student = cursor.fetchone()

        cursor.execute("SELECT ci FROM professor WHERE ci = %s", (receiver,))
        is_professor = cursor.fetchone()

        if not is_student and not is_professor:
          return jsonify({
               'success': False,
               'description': 'No puedes enviar solicitudes a administradores o bibliotecarios'
           }), 400

        # ACÁ VERIFICA QUE UN ESTUDIANTE NO LE ENVIE SOLICITUD A UN PROFESOR

        # Ver quién envía
        cursor.execute("SELECT ci FROM student WHERE ci = %s", (ci_sender,))
        sender_is_student = cursor.fetchone() is not None

        # Ver roles del receptor
        cursor.execute("SELECT ci FROM student WHERE ci = %s", (receiver,))
        receiver_is_student = cursor.fetchone() is not None

        cursor.execute("SELECT ci FROM professor WHERE ci = %s", (receiver,))
        receiver_is_professor = cursor.fetchone() is not None

        # Bloquear solo si:
        # - el que envía es estudiante
        # - el receptor es profesor
        # - y NO es estudiante (o sea, solo profesor)
        if sender_is_student and receiver_is_professor and not receiver_is_student:
            return jsonify({
                'success': False,
                'description': 'Un estudiante no puede enviarle una solicitud a un profesor "solo profesor".'
            }), 400

        # ACÁ VERIFICA QUE UN MIEMBRO NO INVITE A GENTE RANDOM AL GRUPO DE ESTUDIO

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
@app.route('/freeRooms/<building>&<date>', methods=['GET'])
@token_required
def getFreeRooms(building, date):
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401
        
        conn = connection()
        cursor = conn.cursor()
        
        cursor.execute(''' 
            SELECT 
                sR.roomName AS Sala, 
                sR.buildingName AS Edificio, 
                DATE_FORMAT(s.startTime, '%%H:%%i') AS Inicio,
                DATE_FORMAT(s.endTime, '%%H:%%i') AS Fin,
                sR.capacity AS Capacidad
            FROM studyRoom sR
            JOIN shift s
            WHERE sR.buildingName = %s AND (sR.studyRoomId, s.shiftId) NOT IN (
                SELECT r.studyRoomId, r.shiftId
                FROM reservation r
                WHERE r.date = %s
            )
            ORDER BY Inicio, Fin DESC;
        ''', (building, date))
        
        results = cursor.fetchall()

        if not results:
            return jsonify({
                'success': False,
                'description': 'No se encontraron salas libres.'
            }), 404
        
        freeRooms = []

        id = 0
        for row in results:
            freeRooms.append({
                "studyRoom": row['Sala'],
                "building": row['Edificio'],
                "start": str(row['Inicio']),
                "end": str(row['Fin']),
                "date": str(date),
                "capacity": row['Capacidad'],
                "id": id
            })
            id = id + 1

        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Salas libres.',
            'building': building,
            'rooms': freeRooms
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "description": "No se pudo procesar la solicitud.",
            "error": str(e)
        }), 500


# Devolverá todos los turnos y salas libres dependiendo del turno que se haya elegido o de la sala que se haya elegido
@app.route('/roomShift/<building>&<date>&<shiftId>&<roomId>', methods=['GET'])
@token_required
def roomShift(building, date, shiftId, roomId):
    try:
        if not user_has_role("student", "professor"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()

        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
        today = (datetime.now(timezone.utc) + timedelta(days=1)).date()

        if selected_date < today:
            return jsonify({
                'success': False,
                'description': 'No se puede elegir una fecha anterior a mañana'
            }), 400

        shiftId = None if shiftId == "null" or shiftId == "0" else shiftId
        roomId = None if roomId == "null" or roomId == "0" else roomId

        # ACÁ VA A DEVOLVER TODAS LAS SALAS Y TURNOS SI NO HAY NADA SELECCIONADO DE LOS TURNOS Y SALAS
        if not shiftId and not roomId:
            cursor.execute('''
                SELECT sR.roomName AS Sala, sR.capacity AS Capacidad, sR.studyRoomId AS SalaId
                FROM studyRoom sR
                WHERE sR.buildingName = %s AND EXISTS (
                    SELECT *
                    FROM shift sh
                    WHERE sh.shiftId NOT IN (
                        SELECT r.shiftId
                        FROM reservation r
                        WHERE r.date = %s AND r.studyRoomId = sR.studyRoomId
                    )
                )
                ORDER BY Sala
            ''', (building, date))

            salas_libres = cursor.fetchall()

            cursor.execute('''
                SELECT s.shiftId, DATE_FORMAT(s.startTime, '%%H:%%i') AS Inicio, DATE_FORMAT(s.endTime, '%%H:%%i') AS Fin
                FROM shift s
                WHERE EXISTS (
                    SELECT *
                    FROM studyRoom sr
                    WHERE sr.buildingName = %s AND sr.studyRoomId NOT IN (
                        SELECT r.studyRoomId
                        FROM reservation r
                        WHERE r.date = %s AND r.shiftId = s.shiftId
                    )
                )
                ORDER BY Inicio
            ''', (building, date))

            turnos_libres = cursor.fetchall()

            cursor.close()

            return jsonify({
                "success": True,
                "description": "Salas y turnos libres",
                "salas": [{
                    "roomId": r["SalaId"],
                    "roomName": r["Sala"],
                    "capacity": r["Capacidad"]
                } for r in salas_libres],
                "turnos": [{
                    "shiftId": s["shiftId"],
                    "start": s["Inicio"],
                    "end": s["Fin"]
                } for s in turnos_libres]
            }), 200

        # ACÁ VA A DEVOLVER TODAS LAS SALAS LIBRES PARA UN TURNO
        if shiftId and not roomId:
            cursor.execute('''
                SELECT sR.roomName AS Sala, sR.capacity AS Capacidad, sR.studyRoomId AS SalaId
                FROM studyRoom sR
                WHERE sR.buildingName = %s AND sR.studyRoomId NOT IN (
                    SELECT r.studyRoomId
                    FROM reservation r
                    WHERE r.date = %s AND r.shiftId = %s
                )
                ORDER BY Sala
            ''', (building, date, shiftId))

            salas = cursor.fetchall()

            cursor.close()

            return jsonify({
                "success": True,
                "salas": [{
                    "roomId": r["SalaId"],
                    "roomName": r["Sala"],
                    "capacity": r["Capacidad"]
                } for r in salas],
            }), 200

        # ACÁ VA A DEVOLVER TODOS LOS TURNOS LIBRES PARA UNA SALA

        if roomId and not shiftId:
            cursor.execute('''
                SELECT s.shiftId, DATE_FORMAT(s.startTime, '%%H:%%i') AS Inicio, DATE_FORMAT(s.endTime, '%%H:%%i') AS Fin
                FROM shift s
                WHERE s.shiftId NOT IN (
                    SELECT r.shiftId
                    FROM reservation r
                    JOIN studyRoom sr ON sr.studyRoomId = r.studyRoomId
                    WHERE r.date = %s AND sr.studyRoomId = %s
                )
                ORDER BY Inicio
            ''', (date, roomId))

            turnos = cursor.fetchall()

            cursor.close()

            return jsonify({
                "success": True,
                "turnos": [{
                    "shiftId": r["shiftId"],
                    "start": r["Inicio"],
                    "end": r["Fin"]
                } for r in turnos]
            }), 200

        # ACÁ VA A DEVOLVER LA INTERSECCION DE AMBOS

        if shiftId and roomId:
            cursor.execute('''
                SELECT sR.roomName AS Sala, sR.capacity AS Capacidad, sR.studyRoomId AS SalaId
                FROM studyRoom sR
                WHERE sR.buildingName = %s AND sR.studyRoomId = %s AND sR.studyRoomId NOT IN (
                    SELECT r.studyRoomId
                    FROM reservation r
                    WHERE r.date = %s AND r.shiftId = %s
                )
            ''', (building, roomId, date, shiftId))

            sala = cursor.fetchone()

            turno = None
            if sala:
                cursor.execute('''
                    SELECT s.shiftId, DATE_FORMAT(s.startTime, '%%H:%%i') AS Inicio, DATE_FORMAT(s.endTime, '%%H:%%i') AS Fin
                    FROM shift s
                    WHERE s.shiftId = %s
                ''', (shiftId,))
                turno = cursor.fetchone()

            cursor.close()

            return jsonify({
                "success": True,
                "description": "Salas y turnos libres",

                "salas": [{
                    "roomId": sala["SalaId"],
                    "roomName": sala["Sala"],
                    "capacity": sala["Capacidad"]
                }] if sala else [],

                "turnos": [{
                    "shiftId": turno["shiftId"],
                    "start": turno["Inicio"],
                    "end": turno["Fin"]
                }] if turno else []
            }), 200

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'No se pudo procesar la solicitud.',
            'error': str(ex)
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
    

# Conseguir todas las reservas sin bibliotecario asignado en cierta fecha
from datetime import date

@app.route('/reservationsAvailableToday', methods=['GET'])
@token_required
def getAvailableReservationsByDate():
    try:
        """
        if not user_has_role("librarian"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401
        """

        conn = connection()
        cursor = conn.cursor()

        today = date.today().strftime("%Y-%m-%d")

        cursor.execute(
            ''' 
            SELECT 
                DATE_FORMAT(s.startTime, '%%H:%%i') AS start,
                DATE_FORMAT(s.endTime, '%%H:%%i') AS end,
                sR.roomName AS studyRoomName,
                sR.buildingName AS building,
                r.studyGroupId AS studyGroupId,
                r.assignedLibrarian AS librarian
            FROM reservation r
            JOIN shift s ON r.shiftId = s.shiftId
            JOIN studyRoom sR ON r.studyRoomId = sR.studyRoomId
            WHERE r.date = %s
              AND r.assignedLibrarian IS NULL;
            ''',
            (today,)
        )

        results = cursor.fetchall()
        reservations = []


        if not results:
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'description': 'No hay reservas disponibles para hoy.',
                'reservations': []
            }), 200

    
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
            'description': 'Reservas disponibles para hoy.',
            'reservations': reservations
        }), 200

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'No se pudo procesar la solicitud.',
            'error': str(ex)
        }), 500

    
# Conseguir todas las reservas sin bibliotecario asignado en cierta fecha
from datetime import date

@app.route('/reservationsManagedToday', methods=['GET'])
@token_required
def getManagedReservationsByDate():
    try:
        
        if not user_has_role("librarian"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
        }), 401
        
        ci = request.ci

        today = date.today().strftime("%Y-%m-%d")

        conn = connection()
        cursor = conn.cursor()

        cursor.execute(
            ''' 
            SELECT 
                DATE_FORMAT(s.startTime, '%%H:%%i') AS start,
                DATE_FORMAT(s.endTime,   '%%H:%%i') AS end,
                sR.roomName   AS studyRoomName,
                sR.buildingName AS building,
                r.studyGroupId   AS studyGroupId,
                r.assignedLibrarian AS librarian
            FROM reservation r
            JOIN shift s     ON r.shiftId = s.shiftId
            JOIN studyRoom sR ON r.studyRoomId = sR.studyRoomId
            WHERE r.date = %s
              AND r.assignedLibrarian = %s;
            ''',
            (today, ci)
        )

        results = cursor.fetchall()
        reservations = []

        if results:
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
        }), 200

    except Exception as ex:
        print("ERROR en /reservationsManagedToday:", ex)
        return jsonify({
            'success': False,
            'description': 'No se pudo procesar la solicitud.',
            'error': str(ex)
        }), 500


# Asignarle un bibliotecario una reserva por medio de su cédula
@app.route('/manageReservation', methods=['PATCH'])
@token_required
def patchManageReservation():
    try:
        if not user_has_role("librarian"):
            return jsonify({'success': False, 'Description': 'unauthorized'}), 401

        conn = connection()
        cursor = conn.cursor()

        data = request.get_json()
        studyGroupId = data.get('studyGroupId')
        librarian = data.get('librarian')

        if not all([studyGroupId, librarian]):
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400

        cursor.execute(''' 
            UPDATE reservation
            SET assignedLibrarian = %s
            WHERE assignedLibrarian IS NULL AND studyGroupId = %s;
        ''', [librarian, studyGroupId])

        conn.commit()

        cursor.execute(''' 
            SELECT r.studyGroupId, r.assignedLibrarian
            FROM reservation r
            WHERE r.studyGroupId = %s;
        ''', [studyGroupId])

        resultado = cursor.fetchone()

        cursor.close()
        conn.close()

        if not resultado:
            return jsonify({
                'success': False,
                'description': 'No se encontró la reserva actualizada'
            }), 404

        return jsonify({
            'success': True,
            'description': 'Nueva reserva administrada.',
            "result": resultado
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


# Quitarle la cédula del bibliotecario asignado a una reserva
@app.route('/unmanageReservation', methods=['PATCH'])
@token_required
def patchUnmanageReservation():
    try:
        conn = connection()
        cursor = conn.cursor()

        data = request.get_json()
        studyGroupId = data.get('studyGroupId')
        librarian = data.get('librarian')

        if not all([studyGroupId, librarian]):
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400
        
        cursor.execute(''' 
            UPDATE reservation
            SET assignedLibrarian = NULL
            WHERE assignedLibrarian = %s AND studyGroupId = %s;
        ''', [librarian, studyGroupId])

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'description': 'Se dejó de administrar la reserva.'
        }), 200

    except Exception as ex:
        try:
            conn.rollback()
        except:
            pass
        return jsonify({
            'success': False,
            'description': "No se pudo procesar la solicitud.",
            'error': str(ex)
        }), 500


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
                sg.studyGroupId AS id,
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
                sg.studyGroupId AS id,
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
                'id': row['id'],
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
            }), 401
        
        cursor.execute(''' 
            SELECT studyGroupId
            FROM studyGroup sG
            WHERE sG.studyGroupId = %s AND status = 'Activo';
        ''', (groupId))

        res = cursor.fetchone()
        if res is not None:
            cursor.execute(''' 
                DELETE FROM groupRequest
                WHERE studyGroupId = %s
            ''', (groupId))
            conn.commit()

            cursor.execute(''' 
                DELETE FROM studyGroupParticipant
                WHERE studyGroupId = %s
            ''', (groupId))
            conn.commit()

            cursor.execute(''' 
                SELECT r.studyGroupId
                FROM reservation r
                WHERE r.studyGroupId = %s;
            ''', (groupId))
            reservation = cursor.fetchone()
            if reservation is not None:
                cursor.execute(''' 
                    DELETE FROM reservation
                    WHERE studyGroupId = %s
                ''', (groupId))
                conn.commit()

            cursor.execute(''' 
                DELETE FROM studyGroup
                WHERE studyGroupId = %s AND status = 'Activo';
            ''', (groupId))
            conn.commit()
            cursor.close()

            return jsonify({
                'success': True,
                'description': 'El grupo se ha eliminado con éxito.'
            }), 200
        else:
            return jsonify({
                'success': False,
                'description': 'No se puede eliminar un grupo inactivo'
            }), 401
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
                u_leader.name,
                u_leader.lastName
            FROM studyGroup sg
            JOIN user u_leader ON sg.leader = u_leader.ci
            WHERE sg.studyGroupId = %s
        """, (groupId,))
        group_info = cursor.fetchone()

        cursor.execute("""
            SELECT 
                u.ci,
                u.name
                u.lastName
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

@app.route('/leaveGroup/<groupId>', methods=['DELETE'])
@token_required
def leaveGroup(groupId):
    try:
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

        if ci == leaderCi:
            return jsonify({
                'success': False,
                'description': 'No puedes abandonar un grupo del que eres líder.'
            }), 401
        
        cursor.execute(''' 
            DELETE FROM studyGroupParticipant sGP
            WHERE sGP.member = %s AND sGP.studyGroupId = %s;
        ''', (ci, groupId))
        conn.commit()
        cursor.close()

        return jsonify({
            'success': True, 
            'description': 'Has abandonado el grupo.'
        }), 200

    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'No se pudo procesar la solicitud.'
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
        conn.commit()
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
        cursor.close()

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

@app.route('/switchRole', methods=['POST'])
@token_required
def switch_role():
    try:
        data = request.get_json()
        new_role = data.get('role')

        if not new_role:
            return jsonify({
                'success': False,
                'description': 'Rol no especificado'
            }), 400

        roles = getattr(request, 'roles', [])

        if new_role not in roles:
            return jsonify({
                'success': False,
                'description': 'No tienes ese rol'
            }), 400

        auth_header = request.headers.get('Authorization', '')
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        email = None
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            email = payload.get('email')

        now = datetime.now(timezone.utc)
        access_payload = {
            'email': email,
            'ci': request.ci,
            'role': new_role,
            'roles': roles,
            'exp': now + timedelta(minutes=120)
        }

        access_token = jwt.encode(access_payload, SECRET_KEY, algorithm='HS256')

        return jsonify({
            'success': True,
            'access_token': access_token,
            'role': new_role,
            'roles': roles
        }), 200

    except Exception as ex:
        print("ERROR EN /switchRole:", ex)
        return jsonify({
            'success': False,
            'description': 'Error al cambiar rol',
            'error': str(ex)
        }), 500

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

@app.route('/updateUser', methods=['PATCH'])
@token_required
def patchUpdateDataUser():
    try:
        if not user_has_role("administrator"):
            return jsonify({'success': False, 'Description': 'unauthorized'}), 401

        conn = connection()
        cursor = conn.cursor()

        data = request.get_json()

        ci = data.get('ci')
        roles = data.get('roles')
        name = data.get('name', "").replace(" ", "")
        lastName = data.get('lastName', "").replace(" ", "")
        careerId = data.get('careerId')
        campus = data.get('campus')
        buildingName = data.get('buildingName')

        if not ci or not roles or not name or not lastName:
            return jsonify({'success': False, 'description': 'Faltan datos obligatorios'}), 400

        if len(name) < 3 or not name.isalpha():
            return jsonify({'success': False, 'description': 'Nombre inválido'}), 400

        if len(lastName) < 3 or not lastName.isalpha():
            return jsonify({'success': False, 'description': 'Apellido inválido'}), 400

        cursor.execute(
            "UPDATE user SET name = %s, lastName = %s WHERE ci = %s",
            (name, lastName, ci)
        )
        conn.commit()

        current_roles = set()

        tables = {
            "student": "student",
            "professor": "professor",
            "librarian": "librarian",
            "administrator": "administrator",
        }

        for role, table in tables.items():
            cursor.execute(f"SELECT 1 FROM {table} WHERE ci = %s", (ci,))
            if cursor.fetchone():
                current_roles.add(role)

        new_roles = set(roles)

        for r in current_roles - new_roles:
            cursor.execute(f"DELETE FROM {tables[r]} WHERE ci = %s", (ci,))
            conn.commit()

        for r in new_roles - current_roles:
            if r == "student":
                cursor.execute(
                    "INSERT INTO student (ci, careerId, campus) VALUES (%s, %s, %s)",
                    (ci, careerId, campus)
                )

            elif r == "professor":
                cursor.execute(
                    "INSERT INTO professor (ci, campus) VALUES (%s, %s)",
                    (ci, campus)
                )

            elif r == "librarian":
                cursor.execute(
                    "INSERT INTO librarian (ci, buildingName) VALUES (%s, %s)",
                    (ci, buildingName)
                )

            elif r == "administrator":
                cursor.execute(
                    "INSERT INTO administrator (ci) VALUES (%s)", (ci,)
                )

            conn.commit()


        if "student" in new_roles:
            cursor.execute(
                "UPDATE student SET careerId = %s, campus = %s WHERE ci = %s",
                (careerId, campus, ci)
            )
            conn.commit()

        if "professor" in new_roles:
            cursor.execute(
                "UPDATE professor SET campus = %s WHERE ci = %s",
                (campus, ci)
            )
            conn.commit()

        if "librarian" in new_roles:
            cursor.execute(
                "UPDATE librarian SET buildingName = %s WHERE ci = %s",
                (buildingName, ci)
            )
            conn.commit()

        return jsonify({
            'success': True,
            'description': 'Usuario y roles actualizados correctamente.'
        }), 200

    except Exception as ex:
        try:
            conn.rollback()
        except:
            pass

        return jsonify({
            'success': False,
            'description': 'Error interno.',
            'error': str(ex)
        }), 500

@app.route('/buildings', methods=['GET'])
@token_required
def getBuildings():
    try:
        conn = connection()
        cursor = conn.cursor()

        cursor.execute("SELECT buildingName, address, campus FROM building")
        buildings = cursor.fetchall()

        buildings_list = [
            {
                "buildingName": b["buildingName"],
                "address": b["address"],
                "campus": b["campus"]
            }
            for b in buildings
        ]

        return jsonify({
            "success": True,
            "buildings": buildings_list
        }), 200

    except Exception as ex:
        return jsonify({
            "success": False,
            "description": "Error al obtener los edificios",
            "error": str(ex)
        }), 500
    
    
# ESTADISTICAS

@app.route('/room/getSalasMasReservadas', methods=['GET'])
@token_required
def getSalasMasReservadas():
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401
        conn = connection()
        cursor = conn.cursor()


        cursor.execute("""SELECT COUNT(r.studyRoomId) AS CantidadDeReservasPor, sR.roomName AS Sala, sR.buildingName AS Edificio
        FROM reservation r
        JOIN studyRoom sR on r.studyRoomId = sR.studyRoomId
        GROUP BY r.studyRoomId
        ORDER BY CantidadDeReservasPor DESC""")

        resultado = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({
            'success': True,
            'salasMasReservadas': resultado,
        })

    except Exception as ex:
        return jsonify({'description': 'Error', 'error': str(ex)}), 500

@app.route('/shifts/mostDemanded', methods=['GET'])
@token_required
def getTurnosMasDemandados():
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                COUNT(*) AS cantidad_reservas,
                DATE_FORMAT(s.startTime, '%H:%i:%s') AS startTime,
                DATE_FORMAT(s.endTime, '%H:%i:%s') AS endTime
            FROM reservation r
            JOIN shift s ON r.shiftId = s.shiftId
            GROUP BY s.startTime, s.endTime
            ORDER BY cantidad_reservas DESC;
        """)

        resultado = cursor.fetchall()
        cursor.close()
        conn.close()


        turnos = []
        id = 0

        for row in resultado:
            turnos.append({
                "id": id,
                "reservas": row["cantidad_reservas"],
                "start": str(row["startTime"]),
                "end":  str(row["endTime"]),
            })
            id += 1

        return jsonify({
            'success': True,
            'shiftMostDemanded': turnos,
        }), 200

    except Exception as ex:
        print("ERROR en /shifts/mostDemanded:", ex)
        return jsonify({'description': 'Error', 'error': str(ex)}), 500

@app.route('/promedioParticipantesPorSalas', methods=['GET'])
@token_required
def getPromedioParticipantesPorSala():
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, AVG(cantidad) AS promedio_participantes
            FROM (
                SELECT studyroom.studyRoomId, roomName as name, COUNT(studyGroupParticipant.member) AS cantidad
                FROM reservation
                JOIN studyroom ON reservation.studyRoomId = studyroom.studyRoomId
                JOIN obligatoriobdd.studygroup ON reservation.studyGroupId = studygroup.studyGroupId
                JOIN studygroupparticipant ON studygroup.studyGroupId = studygroupparticipant.studyGroupId
                GROUP BY studyroom.studyRoomId, reservation.studyGroupId
            ) AS sub
            GROUP BY name;
        """)

        resultado = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'promedioPorSalas': resultado,
        }), 200

    except Exception as ex:
        print("ERROR en /promedioParticipantesPorSalas:", ex)
        return jsonify({'description': 'Error', 'error': str(ex)}), 500


@app.route('/reservasPorCarreraYFacultad', methods=['GET'])
@token_required
def getReservasPorCarreraYFacultad():
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) AS CantidadReservasPor, c.careerName AS Carrera, f.facultyName AS Facultad
            FROM reservation r
            JOIN studyGroup sG ON r.studyGroupId = sG.studyGroupId
            JOIN student s ON sG.leader = s.ci
            JOIN career c ON s.careerId = c.careerId
            JOIN faculty f on c.facultyId = f.facultyId
            GROUP BY Carrera, Facultad;

        """)

        resultado = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'reservasPorCarreraYFacultad': resultado,
        }), 200

    except Exception as ex:
        print("ERROR en /reservasPorCarreraYFacultad:", ex)
        return jsonify({'description': 'Error', 'error': str(ex)}), 500

@app.route('/porcentajeOcupacionPorEdificio', methods=['GET'])
@token_required
def getPorcentajeOcupacionPorEdificio():
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT building.buildingName, (
            COUNT(DISTINCT studyroom.studyRoomId) * 100.0 / (
                    SELECT COUNT(*)
                    FROM studyRoom
                    WHERE studyroom.buildingName = building.buildingName
                )
            ) AS porcentaje_ocupacion
        FROM building
        JOIN studyRoom ON building.buildingName = studyroom.buildingName
        JOIN reservation ON studyroom.studyRoomId = reservation.studyRoomId
        WHERE reservation.state IN ('Activa', 'Finalizada', 'Sin asistencia')
        GROUP BY building.buildingName;
        """)

        resultado = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'porcentajeDeOcupacion': resultado,
        }), 200

    except Exception as ex:
        print("ERROR en /porcentajeOcupacionPorEdificio:", ex)
        return jsonify({'description': 'Error', 'error': str(ex)}), 500

@app.route('/cantidadReservasAlumnosYProfesores', methods=['GET'])
@token_required
def getCantidadReservasAlumnosYProfesores():
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) AS CantidadReservas
            FROM reservation r
            WHERE r.state = 'Finalizada' OR r.state = 'Activa';
        """)

        resultado = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'cantidadReservas': resultado,
        }), 200
    except Exception as ex:
        print("ERROR en /cantidadReservasAlumnosYProfesores:", ex)
        return jsonify({'description': 'Error', 'error': str(ex)}), 500

@app.route('/sancionesProfesoresYAlumnos', methods=['GET'])
@token_required
def getSancionesProfesoresYAlumnos():
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT u.ci, u.name, u.lastName, COUNT(*) AS sanciones
            FROM sanction sa
            JOIN user u ON sa.ci = u.ci
            LEFT JOIN student s ON u.ci = s.ci
            LEFT JOIN professor p ON u.ci = p.ci
            WHERE s.ci IS NOT NULL OR p.ci IS NOT NULL
            GROUP BY u.ci
            ORDER BY sanciones DESC;
        """)

        resultado = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'sanciones': resultado,
        }), 200
    except Exception as ex:
        print("ERROR en /getSancionesProfesoresYAlumnos:", ex)
        return jsonify({'description': 'Error', 'error': str(ex)}), 500

@app.route('/porcentajeReservasEfectivasYNoEfectivas', methods=['GET'])
@token_required
def getPorcentajeReservasEfectivasYNoEfectivas():
    try:
        if not user_has_role("administrator"):
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401

        conn = connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                SUM(CASE WHEN state = 'Finalizada' THEN 1 ELSE 0 END)/COUNT(*) * 100 AS Finalizada,
                SUM(CASE WHEN state = 'Cancelada' THEN 1 ELSE 0 END)/COUNT(*) * 100 AS Cancelada
            FROM reservation;
        """)

        resultado = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'reservas': resultado,
        }), 200
    except Exception as ex:
        print("ERROR en /porcentajeReservasEfectivasYNoEfectivas:", ex)
        return jsonify({'description': 'Error', 'error': str(ex)}), 500
if __name__ == '__main__':
    app.register_error_handler(404, pageNotFound)
