from flask import Flask, jsonify, request
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from encrypt import hash_pwd
from config import config
from db import connection
from functools import wraps
from pymysql.cursors import DictCursor

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
            
            request.user = data['role']
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

app = Flask(__name__)

app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

@app.after_request
def set_charset(response):
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

app.config.from_object(config['development'])
SECRET_KEY = 'JWT_SECRET_KEY=dIeocMZ1BzPxMcgmkLLPweME31lpx4XP3bsAXpqgt3SLrpKF2a0X6cdUOYr7joIJQwgcL1ht3GFpijm8qFcm4pHyAjie0rCpWEbqUEyYB4W5p36YjqYLhykwjIctJmcoQwF7R8uL9Z3eC34jlgki9dA57EuzT06E6gamcrHbJSmYykfkDwOE5uEeerYGQqzKBFOw9esDhiC1g0v0gWtTcDEPbbg6XMlxhe4MKgZsTfyb7rvUyLRYITcFykegU2tCZDKY'


def pageNotFound(error):
    return "<h1>La página que buscas no existe.</h1>"

# Conseguir todas las sanciones de un usuario por mail OBSOLETO
@app.route('/user/<mail>/sanctions', methods=['GET'])
@token_required
def getUserMailSanctions(mail):
    try:
        rol = request.role
        if rol != "librarian" or rol != "administrator" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
                
            }), 401
        
        cursor = connection.cursor(DictCursor)
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
    
# Conseguir todas las sanciones de un usuario por mail OBSOLETO
@app.route('/user/<ci>/sanctions', methods=['GET'])
@token_required
def getUserCiSanctions(ci):
    try:
        rol = request.role
        if rol != "librarian" or rol != "administrator" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401
        
        cursor = connection.cursor()
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
        connection.rollback()
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
        rol = request.role
        if rol != "student" or rol != "professor" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
            }), 401
        
        cursor = connection.cursor()
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
        connection.rollback()
        return jsonify({
            'success': False,
            'description': 'No se pudieron ver tus sanciones',
            'error': str(ex)
        }), 500

# Insertar nuevas carreras OBSOLETO
@app.route('/careerInsert', methods=['POST'])
@token_required
def createCareer():
    try:
        rol = request.role
        if rol != "administrator" :
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

        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO career (careerName, planYear, facultyId, type) VALUES (%s, %s, %s, %s)",
            (careerName, planYear, facultyId, type_)
        )
        connection.commit()
        cursor.close()

        return jsonify({
            'success': True,
            'description': 'Carrera creada correctamente'
        }), 201

    except Exception as ex:
        connection.rollback()
        return jsonify({
            'success': False,
            'description': 'Error al crear la carrera',
            'error': str(ex)
        }), 500

# Conseguir todos los usuarios que estudien cierta carrera OBSOLETO
@app.route('/user/<careerID>', methods=['GET'])
@token_required
def getUserByCareer(careerID):
    try:
        cursor = connection.cursor(DictCursor)
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
        cursor = connection.cursor()
        cursor.execute("SELECT name, lastName FROM user")
        queryResults = cursor.fetchall()
        users = []
        for row in queryResults:
            user = {'name': row['name'], 'lastName': row['lastName']}
            users.append(user)
        return jsonify({'users': users, 'desc': 'listo.'})
    except Exception as ex:
        return jsonify({'description': 'Error', 'error': str(ex)})

# Conseguir todas las carreras OBSOLETO
@app.route('/career', methods=['GET'])
def getCareers():
    try:
        cursor = connection.cursor()
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

# Registro de usuarios
@app.route('/register', methods=['POST'])
def postRegister():
    try:
        rol = request.role
        if rol != "administrator" :
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

        # Validar datos obligatorios
        if not all([ci, name, lastname, email, password, career_name]):
            return jsonify({
                'success': False,
                'description': 'Faltan datos obligatorios'
            }), 400

        # Validar longitud de contraseña
        if len(password) <= 8:
            return jsonify({
                'success': False,
                'description': 'La contraseña es muy corta (mínimo 9 caracteres)'
            }), 400

        cursor = connection.cursor()

        # Buscar carrera
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

        # Insertar en user
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
        print("ERROR EN /register:", ex)
        return jsonify({
            'success': False,
            'description': 'Error al registrar el usuario',
            'error': str(ex)
        }), 500

# Inicio de sesión
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

        cursor = connection.cursor()

        # Buscar el hash de la contraseña
        cursor.execute("SELECT password FROM login WHERE mail = %s", (email,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            return jsonify({'success': False, 'description': 'Credenciales inválidas'}), 401

        stored_hash = result['password']
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode()

        # Verificar contraseña
        if not bcrypt.checkpw(password.encode(), stored_hash):
            cursor.close()
            return jsonify({'success': False, 'description': 'Credenciales inválidas'}), 401

        # Obtener CI del usuario
        cursor.execute("SELECT ci FROM user WHERE mail = %s", (email,))
        ci_result = cursor.fetchone()
        if not ci_result:
            cursor.close()
            return jsonify({'success': False, 'description': 'Usuario no encontrado'}), 404

        ci = ci_result['ci']

        # Determinar tipo de usuario
        role = None
        tables = ['student', 'professor', 'librarian', 'administrator']
        for table in tables:
            cursor.execute(f"SELECT ci FROM {table} WHERE ci = %s", (ci,))
            if cursor.fetchone():
                role = table
                break
        if not role:
            role = 'unknown'
        
        now = datetime.now(timezone.utc)
        access_payload = {
            'email': email,
            'ci': ci,
            'role': role,
            'exp': now + timedelta(minutes=30)
        }

        access_token = jwt.encode(access_payload, SECRET_KEY, algorithm='HS256')

        cursor.close()

        return jsonify({
            'success': True,
            'access_token': access_token,
            'role': role,
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

        cursor = connection.cursor()
            
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
        
        connection.commit()
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
        rol = request.role
        if rol != "student" or rol != "professor" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
                
            }), 401
        
        cursor = connection.cursor(DictCursor)
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
        rol = request.role
        if rol != "student" or rol != "professor" :
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
        cursor = connection.cursor()

        cursor.execute("SELECT leader FROM studyGroup WHERE studyGroupId = %s", (studyGroupId,))
        
        result = cursor.fetchone()
        
        leader = result['leader'] if result else None

        if leader != ci_sender:
            return jsonify({
                'success': False,
                'description': 'No eres el líder del equipo'
            }), 400

        cursor.execute("INSERT INTO groupRequest VALUES (%s, %s, DEFAULT, DEFAULT, DEFAULT)", (studyGroupId, receiver, ))
        
        connection.commit()
        cursor.close()
        
        return jsonify({
            'success': True,
            'description': 'Solicitud realizada correctamente'
        }), 201
    except Exception as ex:
        connection.rollback()
        print("ERROR EN /createGroupRequest:", ex)
        return jsonify({
            'success': False,
            'description': 'Error al realizar la solicitud',
            'error': str(ex)
        }), 500
    
# Conseguir usuarios por nombre, apellido o mail
@app.route('/users/<name>&<lastName>&<mail>', methods = ['GET'])
def getUserByNameLastMail(name, lastName, mail):
    try:
        cursor = connection.cursor(DictCursor)
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
            cursor.close()

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
        rol = request.role
        if rol != "librarian" or rol != "administrator" :
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
@app.route('/user/<ci>/reservations', methods=['GET'])
@token_required
def getUserCiReservations(ci):
    try:
        rol = request.role
        if rol != "librarian" or rol != "administrator" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
                
            }), 401
        
        ci = int(ci)
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

# Conseguir todas las reservas de un usuario con token
@app.route('/myReservations', methods=['GET'])
@token_required
def getUserReservations():
    try:
        rol = request.role
        if rol != "student" or rol != "professor" :
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
    
# Conseguir todas las solicitudes de un usuario
@app.route('/myGroupRequests', methods = ['GET'])
@token_required
def getAllUserGroupRequests():
    try:
        rol = request.role
        if rol != "student" or rol != "professor" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
                
            }), 401
        
        cursor = connection.cursor(DictCursor)
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
        ''', (ci))
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

# Conseguir información de todo grupo del que se es parte
@app.route('/myGroups', methods = ['GET'])
@token_required
def getAllGroups():
    try:
        rol = request.role
        if rol != "student" or rol != "professor" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
                
            }), 401
        
        cursor = connection.cursor(DictCursor)
        ci = request.ci

        cursor.execute(''' 
            SELECT 
                sG.studyGroupName AS groupName, 
                sG.status AS groupStatus, 
                u.name AS userName, 
                u.lastName AS userLastName, 
                u.mail AS userMail, 
                u.profilePicture AS userPicture
            FROM studyGroup sG
            JOIN user u ON sG.leader = u.ci
            WHERE u.ci = %s
                UNION
            SELECT 
                sG.studyGroupName AS groupName, 
                sG.status AS groupStatus, 
                u.name AS userName, 
                u.lastName AS userLastName, 
                u.mail AS userMail, 
                u.profilePicture AS userPicture
                FROM studyGroupParticipant sGp
            JOIN user u ON sGp.member = u.ci
            JOIN studyGroup sG ON sGp.studyGroupId = sG.studyGroupId
            WHERE sGp.member = %s;
        ''', (ci))

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
                'groupState': row['groupState'],
                'userName': row['userName'],
                'userLastName': row['userLastName'],
                'mail': row['userMail'],
                'profilePicture': row['userPicture']
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
@app.route('/deleteMyGroup/<groupId>', methods = ['DELETE'])
@token_required
def deleteGroupById(groupId):
    try:
        rol = request.role
        if rol != "student" or rol != "professor" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
                
            }), 401
        
        cursor = connection.cursor()
        ci = request.ci
        groupId = int(groupId)

        cursor.execute(''' 
            SELECT sG.leader AS leader
            FROM studyGroup sG
            WHERE sG.studyGroupId = %s
        ''', (groupId))
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
            ''', (groupId))
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
        rol = request.role
        if rol != "student" or rol != "professor" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
                
            }), 401
        
        cursor = connection.cursor(DictCursor)
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
@app.route('/group/<groupId>/acceptRequest', methods = ['PATCH'])
@token_required
def acceptUserRequest(groupId):
    try:
        rol = request.role
        if rol != "student" or rol != "professor" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
                
            }), 401
        
        cursor = connection.cursor()
        ci = request.ci
        groupId = int(groupId)
        
        cursor.execute(''' 
            UPDATE groupRequest
            SET status = 'Aceptada'
            WHERE receiver = %s AND studyGroupId = %s;
        ''', (ci, groupId))

        cursor.execute(''' 
            INSERT INTO studyGroupParticipant VALUES
            (%s, %s)
        ''', (groupId, ci))
        cursor.close()

        return jsonify({
            'success': True, 
            'description': 'Se ha aceptado la solicitud.'
        })
    except Exception as ex:
        return jsonify({
            'success': False,
            'description': 'No se pudo procesar la solicitud.',
            'error': str(ex)
        }), 500
    
# Rechazar una solicitud
@app.route('/group/<groupId>/denyRequest', methods = ['PATCH'])
@token_required
def denyGroupRequest(groupId):
    try:
        rol = request.role
        if rol != "student" or rol != "professor" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
                
            }), 401
        
        cursor = connection.cursor()
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
        rol = request.role
        if rol != "student" or rol != "professor" :
            return jsonify({
                "success": False,
                "description": "Usuario no autorizado",
                
            }), 401
        cursor = connection.cursor()

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
        connection.commit()

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

if __name__ == '__main__':
    app.register_error_handler(404, pageNotFound)
