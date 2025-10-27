DROP DATABASE IF EXISTS ObligatorioBDD;
CREATE DATABASE ObligatorioBDD;
USE ObligatorioBDD;

CREATE FUNCTION validarCi(ci VARCHAR(20))
RETURNS BOOLEAN
DETERMINISTIC
BEGIN
  DECLARE numeros VARCHAR(20);
  DECLARE base VARCHAR(20);
  DECLARE verificador INT;
  DECLARE factores VARCHAR(14) DEFAULT '2987634';
  DECLARE suma INT DEFAULT 0;
  DECLARE i INT DEFAULT 1;
  DECLARE digito INT;
  DECLARE factor INT;
  DECLARE resto INT;
  DECLARE esperado INT;

  -- Asignamos el parámetro de entrada a la variable local
  SET numeros = ci;

  -- Chequeamos que la cédula tenga 8 dígitos
  IF CHAR_LENGTH(numeros) <> 8 THEN
    RETURN FALSE;
  END IF;

  -- Conseguimos el último dígito (verificador)
  SET verificador = CAST(RIGHT(numeros, 1) AS UNSIGNED);
  SET base = LEFT(numeros, CHAR_LENGTH(numeros) - 1);

  -- Lógica del cálculo del dígito verificador
  WHILE i <= CHAR_LENGTH(base) DO
    SET digito = CAST(SUBSTRING(base, i, 1) AS UNSIGNED);
    SET factor = CAST(SUBSTRING(factores, i, 1) AS UNSIGNED);
    SET suma = suma + digito * factor;
    SET i = i + 1;
  END WHILE;

  SET resto = suma MOD 10;
  SET esperado = IF(resto = 0, 0, 10 - resto);

  -- Verificamos si coincide el dígito verificador
  RETURN esperado = verificador;
END;

/**/

CREATE TABLE user (
    ci INT PRIMARY KEY,
    name VARCHAR(32) NOT NULL CHECK ( CHAR_LENGTH(name) >= 3 ),
    lastName VARCHAR(32) NOT NULL CHECK ( CHAR_LENGTH(lastName) >= 3 ),
    mail VARCHAR(50) UNIQUE CHECK ( LOWER(mail) LIKE '%@correo.ucu.edu.uy' ),
    profile VARCHAR(100) UNIQUE,
    type ENUM('Participante', 'Administrador') DEFAULT 'Participante'
);

    CREATE TRIGGER validate_ci_user
    BEFORE INSERT ON user
    FOR EACH ROW
        BEGIN
            IF NOT validarCi(CAST(NEW.ci AS CHAR(8))) THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'La cédula tiene que ser válida.';
            END IF;
        END;
    DELIMITER ;

/**/

CREATE TABLE login (
    mail VARCHAR(50) CHECK ( LOWER(mail) LIKE '%@correo.ucu.edu.uy' ) PRIMARY KEY,
    password VARCHAR(32) NOT NULL CHECK ( CHAR_LENGTH(password) >= 8 ),
    FOREIGN KEY (mail) REFERENCES user(mail)
);

/**/

CREATE TABLE building (
    buildingName VARCHAR(32) PRIMARY KEY,
    address VARCHAR(32) NOT NULL,
    campus VARCHAR(32) NOT NULL CHECK ( CHAR_LENGTH(campus) >= 5 )
);

/**/

CREATE TABLE studyRooms (
    roomName VARCHAR(8) UNIQUE,
    building VARCHAR(32),
    capacity INT NOT NULL CHECK ( capacity > 0 ),
    roomType ENUM('Libre', 'Posgrado', 'Docente') DEFAULT 'Libre',
    FOREIGN KEY (building) REFERENCES building(buildingName),
    PRIMARY KEY(roomName, building)
);

/**/

CREATE TABLE shift (
    shiftId INT AUTO_INCREMENT PRIMARY KEY,
    startTime TIME NOT NULL,
    endTime TIME NOT NULL,
    CONSTRAINT validate_times CHECK (endTime > startTime)
);

    CREATE TRIGGER validate_shift
    BEFORE INSERT ON shift
    FOR EACH ROW
        BEGIN
            IF TIME(NEW.startTime) < '08:00:00' || TIME(NEW.endTime) > '23:00:00' THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'El turno debe ser entre las 8 de la mañana y las 11 de la noche.';
            END IF;
            IF NEW.startTime > NEW.endTime THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'El turno de inicio no puede estar despues del de fin.';
            END IF;
        END;
    DELIMITER ;

/**/

CREATE TABLE reservation (
    reservationId INT AUTO_INCREMENT PRIMARY KEY,
    roomName VARCHAR(32) NOT NULL UNIQUE,
    date DATE NOT NULL,
    shiftId INT NOT NULL,
    state ENUM('Activa', 'Cancelada', 'Sin asistencia', 'Finalizada') DEFAULT 'Activa',
    FOREIGN KEY (roomName) REFERENCES studyRooms(roomName),
    FOREIGN KEY (shiftId) REFERENCES shift(shiftId)
);

    CREATE TRIGGER validate_year_reservation
    BEFORE INSERT ON reservation
    FOR EACH ROW
        BEGIN
            IF NEW.date > DATE_ADD(NOW(), INTERVAL 7 DAY) OR NEW.date < CURDATE() THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'La reserva no se puede hacer antes de la fecha de hoy ni para dentro de 7 dias';
            END IF;

        END;
    DELIMITER ;

/**/

CREATE TABLE studyGroup (
    studyGroupId INT PRIMARY KEY AUTO_INCREMENT,
    studyGroupName VARCHAR(50) UNIQUE,
    roomName VARCHAR(32),
    reservationId INT NOT NULL,
    status ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    leader INT NOT NULL,
    FOREIGN KEY (roomName) REFERENCES studyRooms(roomName),
    FOREIGN KEY (reservationId) REFERENCES reservation(reservationId),
    FOREIGN KEY (leader) REFERENCES user(ci)
);

-- Hay que meter un minimo de integrantes en las salas, ya que una persona con una sala de 10 personas en las que hayan solo 3 personas es inutil

-- Primero se tiene que crear un grupo con tus compañeros y despues la reserva donde elegis uno de los grupos que hayas creado

CREATE TABLE participantGroup(
    studyGroupId INT,
    member INT,
    FOREIGN KEY (studyGroupId) REFERENCES studyGroup(studyGroupId),
    FOREIGN KEY (member) REFERENCES user(ci),
    PRIMARY KEY (studyGroupId, member)
);

-- Descartamos la tabla de login y la fusionamos con participant poner en el informe

/* El requestId hace que se puedan enviar multiples request a una persona incluso si esta ya está en el grupo, estaba pensando hacer una primary key compuesta y sacar a la mierda el requestid, y maybe poner de primary a la reserva, el que envia y el que recibe*/
/* Lo cambiamos pero en caso de problemas, volvemos al groupRequestId*/

CREATE TABLE groupRequest (
    reservationId INT NOT NULL,
    sender INT NOT NULL,
    receiver INT NOT NULL,
    status ENUM('Aceptada', 'Pendiente', 'Rechazada') DEFAULT 'Pendiente',
    requestDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reservationId) REFERENCES reservation(reservationId),
    FOREIGN KEY (sender) REFERENCES user(ci),
    FOREIGN KEY (receiver) REFERENCES user(ci),
    PRIMARY KEY (reservationId, sender, receiver)
);

CREATE TABLE faculty (
    facultyId INT PRIMARY KEY AUTO_INCREMENT,
    facultyName VARCHAR(32) CHECK ( CHAR_LENGTH(facultyName) >= 3 )
);

/************* Agreamos como primary id ***************/

CREATE TABLE academicPlan (
    academicPlanId INT PRIMARY KEY AUTO_INCREMENT,
    planName YEAR,
    facultyId INT,
    careerName VARCHAR(100),
    type ENUM('Grado', 'Posgrado') NOT NULL,
    FOREIGN KEY (facultyId) REFERENCES faculty(facultyId)
);

    CREATE TRIGGER validate_year_academicPlan
    BEFORE INSERT ON academicPlan
    FOR EACH ROW
    BEGIN
        IF NEW.planName <= 1985 OR NEW.planName >= YEAR(CURDATE()) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El año del plan debe estar entre 1985 y el año actual';
        END IF;
    END;

-- Ver el tema de que no podemos usar CURDATE para hacer los chequeos ponerlo en el informe, no se pueden usar funciones deterministas en los checks

/************* Cambiamos el planname por el id de academicplan ***************/

CREATE TABLE academicPlanParticipant (
    studentPlanID INT PRIMARY KEY AUTO_INCREMENT,
    participantCi INT,
    academicPlanId INT NOT NULL,
    role ENUM('Alumno', 'Docente') NOT NULL,
    FOREIGN KEY (participantCi) REFERENCES user(ci),
    FOREIGN KEY (academicPlanId) REFERENCES academicPlan(academicPlanId)
);

/****** REVISAR DESPUES CON THIAGO ******/
CREATE TABLE participantReservation (
    participantCi INT NOT NULL,
    shiftId INT NOT NULL,
    requestDate DATE NOT NULL,
    attendance ENUM('Asiste', 'Por confirmar', 'No asiste') DEFAULT 'Por confirmar',
    FOREIGN KEY (participantCi) REFERENCES user(ci),
    FOREIGN KEY (shiftId) REFERENCES shift(shiftId)
);

    CREATE TRIGGER validate_year_participantReservation
    BEFORE INSERT ON participantReservation
    FOR EACH ROW
    BEGIN
        IF NEW.requestDate > CURDATE() THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'La fecha de la solicitud tiene que ser menor que la fecha actual';
        END IF;
    END;

-- ¿Es necesario tener la fecha de solicitud de reserva? ¿Para qué la podemos usar?

/****** HASTA ACÁ ******/

CREATE TABLE participantSanction (
    sanctionId INT PRIMARY KEY AUTO_INCREMENT,
    participantCi INT NOT NULL,
    description ENUM('Comer', 'Ruidoso', 'Vandalismo', 'Imprudencia', 'Ocupar') NOT NULL,
    startDate DATE NOT NULL,
    endDate DATE NOT NULL,
    FOREIGN KEY (participantCi) REFERENCES user(ci)
);

    CREATE TRIGGER validate_participantSanction
    BEFORE INSERT ON participantSanction
    FOR EACH ROW
        BEGIN
            IF NEW.startDate > NEW.endDate THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'La sanción no puede empezar despues de que terminó';
            END IF;
        END;
    DELIMITER ;

/**** INSERTAR VALORES EN LAS TABLAS ****/

INSERT INTO user
VALUES(55531973, 'Santiago', 'Aguerre', 'santiago.aguerre@correo.ucu.edu.uy', NULL, NULL),
      (57004718, 'Thiago', 'García', 'thiago.garcia@correo.ucu.edu.uy', NULL,NULL),
      (55897692, 'Agostina', 'Etchebarren', 'agostina.etchebarren@correo.ucu.edu.uy', NULL,NULL),
      (12345672, 'Francisco', 'Brun', 'francisco.brun@correo.ucu.edu.uy', NULL, NULL);

INSERT INTO login
VALUES ('santiago.aguerre@correo.ucu.edu.uy', '12345678');

INSERT INTO building
VALUES('Edificio Mullin', 'Comandante Braga 2745', 'Salto');

INSERT INTO studyRooms
VALUES ('Sala 1', 'Edificio Mullin', 10, NULL),
       ('Sala 2', 'Edificio Mullin', 4, NULL),
       ('Sala 3', 'Edificio Mullin', 8, NULL);

INSERT INTO shift
VALUES (NULL, '08:00:00', '23:00:00');

INSERT INTO reservation
VALUES (NULL, 'Sala 1', '2025-10-27', 1, NULL),
       (NULL, 'Sala 2', CURDATE(), 1, NULL),
       (NULL, 'Sala 3', '2025-11-01', 1, NULL);

INSERT INTO studyGroup
VALUES (NULL, 'Grupo Redes', 'Sala 1', 1, 55531973),
       (NULL, 'Grupo Bases','Sala 2', 2, 57004718),
       (NULL, 'Grupo Desarrollo','Sala 3', 3, 55897692);

INSERT INTO participantGroup
VALUES (1, 55897692),
       (1, 57004718),
       (2, 55531973),
       (3, 12345672);

INSERT INTO groupRequest
VALUES (1, 55531973, 12345672, NULL, NULL);

INSERT INTO faculty
VALUES (NULL, 'Ingenieria'),
       (NULL, 'Ciencias Humanas'),
       (NULL, 'Comunicación');

INSERT INTO career
VALUES ('Ingenieria en Informática', 1),
       ('Psicología', 2),
       ('Licenciatura en Comunicación', 3);

INSERT INTO academicPlan
VALUES (NULL, 2021, 'Ingenieria en Informática', 'Grado'),
       (NULL, 2022, 'Psicología', 'Grado'),
       (NULL, 2023, 'Licenciatura en Comunicación', 'Grado');

INSERT INTO academicPlanParticipant
VALUES (NULL, 55531973, 1, 'Alumno'),
       (NULL, 57004718, 1, 'Alumno'),
       (NULL, 55897692, 3, 'Alumno'),
       (NULL, 12345672, 1, 'Alumno');

INSERT INTO participantSanction
VALUES (NULL, 57004718, 'Comer', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY));

/* Consultas */

/* Hay que hacer un update table cuando cambien el estado */

SELECT reservation.roomName, COUNT(reservation.roomName) AS reservas
FROM reservation
GROUP BY reservation.roomName
ORDER BY reservas DESC;

SELECT shift.startTime, shift.endTime, COUNT(reservation.reservationId) AS demandas
FROM shift
JOIN reservation ON reservation.shiftId = shift.shiftId
GROUP BY shift.startTime, shift.endTime
ORDER BY demandas DESC;

SELECT AVG(participantes)
FROM (
    SELECT COUNT(DISTINCT studyGroup.leader)+COUNT(participantGroup.member) AS participantes
    FROM participantGroup
    JOIN studyGroup ON participantGroup.studyGroupId = studyGroup.studyGroupId
    JOIN reservation ON studyGroup.reservationId = reservation.reservationId
    GROUP BY studyGroup.studyGroupId
) AS alias;

SELECT COUNT(reservation.reservationId), career.careerName, faculty.facultyName
FROM reservation
JOIN studyGroup ON reservation.reservationId = studyGroup.reservationId
JOIN user ON studyGroup.leader = user.ci
JOIN academicPlanParticipant ON user.ci = academicPlanParticipant.participantCi
JOIN academicPlan ON academicPlanParticipant.academicPlanId = academicPlan.academicPlanId
JOIN career ON academicPlan.careerName = career.careerName
JOIN faculty ON career.facultyId = faculty.facultyId
GROUP BY career.careerName, faculty.facultyName;
