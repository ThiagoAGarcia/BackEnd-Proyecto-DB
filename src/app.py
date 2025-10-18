from flask import Flask, jsonify
from config import config
import pymysql

app = Flask(__name__)
app.config.from_object(config['development'])

connection = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB'])

def pageNotFound(error):
    return "<h1>La página que buscas no existe.</h1>"

@app.route('/reservations', methods = ['GET'])
def getReservations():
    try:
        cursor = connection.cursor() 
        SQL = "SELECT reservationId FROM reservation"
        cursor.execute(SQL)
        queryResults = cursor.fetchall()
        reservations = []
        for row in queryResults:
            reservation = {'reservationId': row[0]}
            reservations.append(reservation)
        return jsonify({'reservations': reservations, 'description': 'Reservas listadas.'})
    except Exception as ex:
        return jsonify({'description': 'Error'})
    
@app.route('/reservations/<reservationId>', methods = ['GET'])
def getReservationByURL(reservationId):
    try:
        cursor = connection.cursor() 
        SQL = "SELECT * FROM reservation WHERE reservationId = '{0}'".format(reservationId)
        cursor.execute(SQL)
        queryResults = cursor.fetchone()
        if queryResults != None:
            reservation = {'reservationId': queryResults[0], 'roomName': queryResults[1]}
            return jsonify({'reservation': reservation, 'description': 'Reserva encontrada.'})
        else:
            return jsonify({'mensaje': 'Curso no encontrado.'})
    except Exception as ex:
        return jsonify({'description': 'Error'})

if __name__ == '__main__':
    app.register_error_handler(404, pageNotFound)
    app.run()
