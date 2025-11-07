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

@app.route('/user/<mail>/sanctions', methods=['GET'])
@token_required
def getSanctionsUser(mail):
    try:
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
 
@app.route('/careerInsert', methods=['POST'])
@token_required
def createCareer():
    try:
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

@app.route('/user', methods=['GET'])
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

@app.route('/career', methods=['GET'])
@token_required
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
         
@app.route('/user/<ci>&<groupId>', methods=['GET'])
@token_required
def getGroupUser(ci, groupId):
    try:
        cursor = connection.cursor(DictCursor)
        ci = int(ci)
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
    
@app.route('/createGroupRequest', methods=['POST'])
@token_required
def createGroupRequest():
    try:
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
    
@app.route('/user/<ci>/groupRequest', methods = ['GET'])
def getAllUserGroupRequests(ci):
    try:
        cursor = connection.cursor(DictCursor)
        ci = int(ci)

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
    
@app.route('/user/<ci>/myGroups', methods = ['GET'])
def getAllGroups(ci):
    try:
        cursor = connection.cursor(DictCursor)
        ci = int(ci)

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
    
@app.route('/user/<ci>/deleteGroup/<groupId>', methods = ['DELETE'])
def deleteGroupById(ci, groupId):
    try:
        cursor = connection.cursor()
        ci = int(ci)
        groupId = int(groupId)

        cursor.execute(''' 
            SELECT sG.leader
            FROM studyGroup sG
            WHERE sG.studyGroupId = %s
        ''', (groupId))
        leaderCi = cursor.fetchone()

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
            'description': 'No se ha podido eliminar el grupo.'
        }), 500

@app.route('/user/<ci>/group/<groupId>/acceptRequest', methods = ['PATCH'])
def acceptUserRequest(ci, groupId):
    try:
        cursor = connection.cursor()
        ci = int(ci)
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
    
@app.route('/user/<ci>/group/<groupId>/denyRequest', methods = ['PATCH'])
def denyGroupRequest(ci, groupId):
    try:
        cursor = connection.cursor()
        ci = int(ci)
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

if __name__ == '__main__':
    app.register_error_handler(404, pageNotFound)
