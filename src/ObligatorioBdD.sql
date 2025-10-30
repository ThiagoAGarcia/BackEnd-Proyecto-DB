DROP DATABASE IF EXISTS ObligatorioBDD;
CREATE DATABASE ObligatorioBDD;
USE ObligatorioBDD;

CREATE TABLE user (
	ci INT PRIMARY KEY,
	name VARCHAR(32) NOT NULL CHECK ( CHAR_LENGTH(name) >= 3 ),
    lastName VARCHAR(32) NOT NULL CHECK ( CHAR_LENGTH(lastName) >= 3 ),
    mail VARCHAR(50) UNIQUE CHECK ( LOWER(mail) LIKE '%@correo.ucu.edu.uy' OR LOWER(mail) LIKE '%@ucu.edu.uy'),
	profilePicture VARCHAR(100)
);

CREATE TABLE faculty (
	facultyId INT PRIMARY KEY AUTO_INCREMENT,
	facultyName VARCHAR(100) CHECK ( CHAR_LENGTH(facultyName) >= 3 )
);

/*** Le cambiamos el nombre de 'academicPlan' a 'career', porque una de las consultas solicitadas pide la carrera, y es más fácil de entender la tabla si se llama 'career'***/

CREATE TABLE career (
    careerId INT PRIMARY KEY AUTO_INCREMENT,
	careerName VARCHAR(100),
    planYear YEAR,
    facultyId INT,
    type ENUM('Grado', 'Posgrado') NOT NULL,
    FOREIGN KEY (facultyId) REFERENCES faculty(facultyId)
);

	DELIMITER $$
    CREATE TRIGGER validate_year_academicPlan
    BEFORE INSERT ON career
    FOR EACH ROW
    BEGIN
    IF NEW.planYear <= 1985 OR NEW.planYear > YEAR(CURDATE()) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'El año del plan debe estar entre 1985 y el año actual.';
    END IF;
    END$$
    DELIMITER ;


CREATE TABLE login (
    mail VARCHAR(50) PRIMARY KEY,
    password VARCHAR(200) NOT NULL,
    FOREIGN KEY (mail) REFERENCES user(mail)
);

CREATE TABLE building (
	buildingName VARCHAR(32) PRIMARY KEY,
	address VARCHAR(32) NOT NULL,
	campus VARCHAR(32) NOT NULL CHECK ( CHAR_LENGTH(campus) >= 5 )
);

CREATE TABLE shift (
    shiftId INT AUTO_INCREMENT PRIMARY KEY,
    startTime TIME NOT NULL,
    endTime TIME NOT NULL,
    CONSTRAINT validate_times CHECK (endTime > startTime)
);

CREATE TABLE studyRoom (
	studyRoomId INT PRIMARY KEY AUTO_INCREMENT,
	roomName VARCHAR(8) NOT NULL,
	buildingName VARCHAR(32),
	capacity INT NOT NULL CHECK ( capacity > 0 ),
    roomType ENUM('Libre', 'Posgrado', 'Docente') DEFAULT 'Libre',
	FOREIGN KEY (buildingName) REFERENCES building(buildingName)
);

CREATE TABLE studyGroup (
    studyGroupId INT PRIMARY KEY AUTO_INCREMENT,
    studyGroupName VARCHAR(50) NOT NULL,
    status ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    leader INT NOT NULL,
    FOREIGN KEY (leader) REFERENCES user(ci)
);

CREATE TABLE studyGroupParticipant (
	studyGroupId INT,
    member INT,
    FOREIGN KEY (studyGroupId) REFERENCES studyGroup(studyGroupId),
    FOREIGN KEY (member) REFERENCES user(ci),
    PRIMARY KEY (studyGroupId, member)
);

CREATE TABLE student (
	ci INT PRIMARY KEY,
	careerId INT NOT NULL,
	FOREIGN KEY (ci) REFERENCES user(ci),
	FOREIGN KEY (careerId) REFERENCES career(careerId)
);

CREATE TABLE professor (
	ci INT PRIMARY KEY,
	FOREIGN KEY (ci) REFERENCES user(ci)
);

CREATE TABLE administrator (
	ci INT PRIMARY KEY,
	FOREIGN KEY (ci) REFERENCES user(ci)
);

CREATE TABLE librarian (
	ci INT PRIMARY KEY,
	FOREIGN KEY (ci) REFERENCES user(ci)
);

CREATE TABLE reservation (
    studyGroupId INT NOT NULL,
	studyRoomId INT NOT NULL,
	date DATE NOT NULL,
    shiftId INT NOT NULL,
    assignedLibrarian INT,
    reservationCreateDate DATE NOT NULL DEFAULT (CURRENT_DATE),
	state ENUM('Activa', 'Cancelada', 'Sin asistencia', 'Finalizada') DEFAULT 'Activa',
    FOREIGN KEY (studyGroupId) REFERENCES studyGroup(studyGroupId),
	FOREIGN KEY (studyRoomId) REFERENCES studyRoom(studyRoomId),
    FOREIGN KEY (shiftId) REFERENCES shift(shiftId),
    FOREIGN KEY (assignedLibrarian) REFERENCES librarian(ci),
    PRIMARY KEY (studyGroupId, studyRoomId, date, shiftId)
);

CREATE TABLE groupRequest (
    studyGroupId INT,
	receiver INT,
	status ENUM('Aceptada', 'Pendiente', 'Rechazada') DEFAULT 'Pendiente',
    isValid BOOLEAN DEFAULT TRUE,
    requestDate DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (studyGroupId) REFERENCES studyGroup(studyGroupId),
	FOREIGN KEY (receiver) REFERENCES user(ci),
    PRIMARY KEY (studyGroupId, receiver)
);

CREATE TABLE sanction (
	sanctionId INT PRIMARY KEY AUTO_INCREMENT,
	ci INT NOT NULL,
	librarianCi INT,
	description ENUM('Comer', 'Ruidoso', 'Vandalismo', 'Imprudencia', 'Ocupar') NOT NULL,
	startDate DATE NOT NULL,
    endDate DATE NOT NULL,
    FOREIGN KEY (ci) REFERENCES user(ci),
	FOREIGN KEY (librarianCi) REFERENCES librarian(ci)
);

/**** INSERTAR VALORES EN LAS TABLAS ****/

INSERT INTO user VALUES
(55897692, 'Agostina', 'Etchebarren', 'agostina.etchebarren@correo.ucu.edu.uy', NULL),
(55531973, 'Santiago', 'Aguerre', 'santiago.aguerre@correo.ucu.edu.uy', NULL),
(57004718, 'Thiago', 'Garcia', 'thiago.garcia@correo.ucu.edu.uy', NULL),
(55299080, 'Martina', 'Caetano', 'martina.caetano@correo.ucu.edu.uy', NULL),
(56309531, 'Pilar', 'Antelo', 'pilar.antelo@correo.ucu.edu.uy', NULL),
(56902752, 'Facundo', 'Píriz', 'facundo.piriz@correo.ucu.edu.uy', NULL),
(59283629, 'Diego', 'de Oliveira', 'diego.deoliveira@correo.ucu.edu.uy', NULL),
(52435831, 'Santiago', 'Blanco', 'santiago.blanco@correo.ucu.edu.uy', NULL),
(54729274, 'Lucia', 'Mallada', 'lucia.mallada@correo.ucu.edu.uy', NULL),
(52737428, 'Luana', 'Biurarrena', 'luana.biurarrena@correo.ucu.edu.uy', NULL),
(57389261, 'Ramiro', 'Casco', 'ramiro.casco@correo.ucu.edu.uy', NULL),
(32124436, 'Lourdes', 'Machado', 'lourdes.machado@ucu.edu.uy', NULL),
(36907777, 'David', 'Liesegang', 'david.liesegang@ucu.edu.uy', NULL),
(34567836, 'Rodrigo', 'Díaz', 'rodrigo.diaz@ucu.edu.uy', NULL),
(45615815, 'Martha', 'Lauria', 'martha.lauria@ucu.edu.uy', NULL),
(12345678, 'Verónica', 'Posadas', 'veronica.posadas@ucu.edu.uy', NULL),
(45673829, 'Franco', 'Portela', 'franco.portela@ucu.edu.uy', NULL),
(32749352, 'Saúl', 'Esquivel', 'saul.esquivel@ucu.edu.uy', NULL);

INSERT INTO faculty VALUES
(NULL, 'Facultad de Psicología y Bienestar Humano'),
(NULL, 'Facultad de Derecho y Artes Liberales'),
(NULL, 'Facultad de la Salud'),
(NULL, 'Facultad de Ciencias Empresariales'),
(NULL, 'Facultad de Ingeniería y Tecnologías');

INSERT INTO career VALUES
(NULL, 'Psicología', 2024, 1, 'Grado'),
(NULL, 'Abogacía', 2024, 2, 'Grado'),
(NULL, 'Notariado', 2021, 2, 'Grado'),
(NULL, 'Medicina', 2024, 3, 'Grado'),
(NULL, 'Comunicación y Marketing', 2023, 4, 'Grado'),
(NULL, 'Ingeniería en Informática', 2021, 5, 'Grado'),
(NULL, 'Inteligencia Artificial y Ciencias de Datos', 2021, 5, 'Grado'),
(NULL, 'Ingeniería en Alimentos', 2023, 5, 'Grado'),
(NULL, 'Doctorado en Psicología', 2021, 1, 'Posgrado'),
(NULL, 'Doctorado en Ciencia Política', 2021, 2, 'Posgrado'),
(NULL, 'Especialidad médica en Cirugía General', 2024, 3, 'Posgrado'),
(NULL, 'Diploma en Reputación Corporativa y Sostenibilidad', 2021, 4, 'Posgrado'),
(NULL, 'Doctorado en Ingeniería', 2024, 5, 'Posgrado');

INSERT INTO login VALUES
('agostina.etchebarren@correo.ucu.edu.uy', 'agostina2006'),
('santiago.aguerre@correo.ucu.edu.uy', 'plantasvszombies2011'),
('thiago.garcia@correo.ucu.edu.uy', 'levimicasita02'),
('martina.caetano@correo.ucu.edu.uy', 'toyotaCorolla1998'),
('pilar.antelo@correo.ucu.edu.uy', '90resultadosRedondos'),
('facundo.piriz@correo.ucu.edu.uy', 'minasElMejorDepartamento'),
('diego.deoliveira@correo.ucu.edu.uy', 'pan&ciruela'),
('santiago.blanco@correo.ucu.edu.uy', '10111010011'),
('lucia.mallada@correo.ucu.edu.uy', 'jshs8294mjdns999'),
('luana.biurarrena@correo.ucu.edu.uy', 'ajdcn765cks1123'),
('ramiro.casco@correo.ucu.edu.uy', 'lush8888'),
('lourdes.machado@ucu.edu.uy', 'jupiter1974'),
('david.liesegang@ucu.edu.uy', 'chocolate1972'),
('rodrigo.diaz@ucu.edu.uy', 'soyUnNPC2333'),
('martha.lauria@ucu.edu.uy', 'iAmGoingToKillBill'),
('veronica.posadas@ucu.edu.uy', 'basesLaMejorMateria11111'),
('saul.esquivel@ucu.edu.uy', 'elInfiernoSonLosOtros2004');

INSERT INTO building VALUES
('Central', 'Av. 8 de Octubre 2738', 'Montevideo'),
('San Ignacio', 'Cornelio Cantera 2731', 'Montevideo'),
('Mullin', 'Cmdt. Braga 2745', 'Montevideo'),
('San José', 'Av. 8 de Octubre 2733', 'Montevideo'),
('Business School', 'Estero Bellaco 2771', 'Montevideo'),
('Athanasius', 'Gral. Urquiza 2871', 'Montevideo');

INSERT INTO shift VALUES
(NULL, '08:00:00', '09:00:00'),
(NULL, '09:00:00', '10:00:00'),
(NULL, '10:00:00', '11:00:00'),
(NULL, '11:00:00', '12:00:00'),
(NULL, '12:00:00', '13:00:00'),
(NULL, '13:00:00', '14:00:00'),
(NULL, '14:00:00', '15:00:00'),
(NULL, '15:00:00', '16:00:00'),
(NULL, '16:00:00', '17:00:00'),
(NULL, '17:00:00', '18:00:00'),
(NULL, '18:00:00', '19:00:00'),
(NULL, '20:00:00', '21:00:00'),
(NULL, '21:00:00', '22:00:00'),
(NULL, '22:00:00', '23:00:00');

INSERT INTO studyRoom VALUES
(NULL, 'Sala 1', 'Central', 6, 'Libre'),
(NULL, 'Sala 2', 'Central', 8, 'Posgrado'),
(NULL, 'Sala 3', 'Central', 4, 'Docente'),
(NULL, 'Sala 1', 'San Ignacio', 4, 'Libre'),
(NULL, 'Sala 2', 'San Ignacio', 4, 'Posgrado'),
(NULL, 'Sala 3', 'San Ignacio', 4, 'Docente'),
(NULL, 'Sala 1', 'Mullin', 3, 'Libre'),
(NULL, 'Sala 2', 'Mullin', 4, 'Posgrado'),
(NULL, 'Sala 3', 'Mullin', 4, 'Docente'),
(NULL, 'Sala 1', 'San José', 5, 'Libre'),
(NULL, 'Sala 2', 'San José', 5, 'Posgrado'),
(NULL, 'Sala 3', 'San José', 5, 'Docente'),
(NULL, 'Sala 1', 'Business School', 6, 'Libre'),
(NULL, 'Sala 2', 'Business School', 6, 'Posgrado'),
(NULL, 'Sala 3', 'Business School', 6, 'Docente'),
(NULL, 'Sala 1', 'Athanasius', 5, 'Libre'),
(NULL, 'Sala 2', 'Athanasius', 5, 'Posgrado'),
(NULL, 'Sala 3', 'Athanasius', 5, 'Docente');

INSERT INTO studyGroup VALUES
(NULL, 'Equipo Programación I', 'Inactivo', 55897692),
(NULL, 'Grupo Prog I', 'Inactivo', 55531973),
(NULL, 'TI3 proyecto final', 'Inactivo', 56309531),
(NULL, 'Los más capos', 'Activo', 57004718),
(NULL, 'Celíacos Anónimos', 'Activo', 59283629),
(NULL, 'Preparación matemática', 'Inactivo', 52435831),
(NULL, 'BDD Proyecto final', 'Activo', 55897692),
(NULL, 'Apoyo tesis', 'Activo', 36907777),
(NULL, 'Deberes de inglés', 'Activo', 57004718),
(NULL, 'Macroeconomía deberes', 'Activo', 52737428),
(NULL, 'Física I preparación parcial', 'Activo', 57389261);

INSERT INTO studyGroupParticipant VALUES
(1, 56309531),
(1, 59283629),
(1, 54729274),
(2, 57004718),
(2, 56902752),
(2, 52435831),
(3, 55299080),
(3, 56902752),
(3, 59283629),
(3, 55897692),
(4, 55531973),
(4, 56902752),
(4, 56309531),
(4, 55299080),
(5, 52737428),
(5, 57389261),
(6, 55897692),
(6, 55531973),
(6, 56902752),
(6, 57389261),
(7, 55531973),
(7, 57004718),
(8, 54729274),
(8, 34567836),
(8, 45673829),
(9, 56902752),
(9, 55299080),
(9, 52435831),
(10, 54729274),
(11, 52435831),
(11, 54729274);

INSERT INTO student VALUES
(55897692, 6),
(55531973, 6),
(57004718, 6),
(55299080, 7),
(56309531, 6),
(56902752, 6),
(59283629, 6),
(52435831, 6),
(54729274, 3),
(52737428, 3),
(57389261, 4);

INSERT INTO professor VALUES
(36907777),
(34567836),
(45615815),
(45673829),
(32749352);

INSERT INTO administrator VALUES
(12345678);

INSERT INTO librarian VALUES
(32124436);

INSERT INTO reservation VALUES
(1, 4, '2024-04-29', 5, 32124436, '2024-04-26', 'Finalizada'),
(2, 4, '2024-04-29', 6, 32124436, '2024-04-25', 'Finalizada'),
(1, 4, '2024-05-17', 7, 32124436, '2024-05-15', 'Finalizada'),
(5, 4, '2025-05-21', 9, 32124436, '2025-05-20', 'Finalizada'),
(11, 7, '2025-06-09', 6, 32124436, '2025-06-07', 'Finalizada'),
(4, 10, '2025-07-15', 5, 32124436, '2025-07-14', 'Finalizada'),
(7, 7, '2025-10-31', 8, 32124436, '2025-10-27', 'Activa');

INSERT INTO groupRequest VALUES
(1, 56309531, 'Aceptada', FALSE, '2024-04-01 10:00:00'),
(1, 59283629, 'Aceptada', FALSE,'2024-04-01 10:05:00'),
(1, 54729274, 'Aceptada', FALSE,'2024-04-01 10:10:00'),
(2, 57004718, 'Aceptada', FALSE,'2024-04-02 11:00:00'),
(2, 56902752, 'Aceptada', FALSE,'2024-04-02 11:05:00'),
(2, 52435831, 'Aceptada', FALSE,'2024-04-02 11:10:00'),
(3, 55299080, 'Aceptada', FALSE,'2024-04-03 12:00:00'),
(3, 56902752, 'Aceptada', FALSE,'2024-04-03 12:05:00'),
(3, 59283629, 'Aceptada', FALSE,'2024-04-03 12:10:00'),
(3, 55897692, 'Aceptada', FALSE,'2024-04-03 12:15:00'),
(4, 55531973, 'Aceptada', FALSE,'2024-04-04 13:00:00'),
(4, 56902752, 'Aceptada', FALSE,'2024-04-04 13:05:00'),
(4, 56309531, 'Aceptada', FALSE,'2024-04-04 13:10:00'),
(4, 55299080, 'Aceptada', FALSE,'2024-04-04 13:15:00'),
(5, 52737428, 'Aceptada', FALSE,'2024-04-05 14:00:00'),
(5, 57389261, 'Aceptada', FALSE,'2024-04-05 14:05:00'),
(6, 55897692, 'Aceptada', FALSE,'2024-04-06 15:00:00'),
(6, 55531973, 'Aceptada', FALSE,'2024-04-06 15:05:00'),
(6, 56902752, 'Aceptada', FALSE,'2024-04-06 15:10:00'),
(6, 57389261, 'Aceptada', FALSE,'2024-04-06 15:15:00'),
(7, 55531973, 'Aceptada', FALSE,'2024-04-07 16:00:00'),
(7, 57004718, 'Aceptada', FALSE,'2024-04-07 16:05:00'),
(8, 54729274, 'Aceptada', FALSE,'2024-04-08 17:00:00'),
(8, 34567836, 'Aceptada', FALSE,'2024-04-08 17:05:00'),
(8, 45673829, 'Aceptada', FALSE,'2024-04-08 17:10:00'),
(9, 56902752, 'Aceptada', FALSE,'2024-04-09 18:00:00'),
(9, 55299080, 'Aceptada', FALSE,'2024-04-09 18:05:00'),
(9, 52435831, 'Aceptada', FALSE,'2024-04-09 18:10:00'),
(10, 54729274, 'Aceptada', FALSE,'2024-04-10 19:00:00'),
(11, 52435831, 'Aceptada', FALSE,'2024-04-11 20:00:00'),
(11, 54729274, 'Aceptada', FALSE,'2024-04-11 20:05:00'),
(1, 32749352, 'Pendiente', TRUE,'2025-10-01 12:00:00'),
(2, 32124436, 'Pendiente', TRUE,'2025-09-20 09:30:00'),
(4, 52737428, 'Pendiente', TRUE,'2025-08-15 14:45:00'),
(3, 54729274, 'Rechazada', FALSE,'2024-05-01 14:00:00'),
(5, 55531973, 'Rechazada', FALSE,'2024-05-02 15:30:00');

INSERT INTO sanction VALUES
(NULL, 55531973, 32124436, 'Ruidoso', '2025-06-01', '2025-08-01'),
(NULL, 56902752, 32124436, 'Ocupar', '2025-07-15', '2025-09-15');

-- Consulta de que salas estan libres x dia

SELECT studyRoom.roomName, s.startTime, s.endTime
FROM studyRoom
JOIN reservation r on studyRoom.studyRoomId = r.studyRoomId
JOIN shift s on r.shiftId = s.shiftId
WHERE studyRoom.studyRoomId NOT IN (
    SELECT studyRoom.roomName, s.startTime, s.endTime
    FROM studyRoom
    JOIN reservation r on studyRoom.studyRoomId = r.studyRoomId
    JOIN shift s on r.shiftId = s.shiftId
    WHERE r.date = '2024-04-29'
);

SELECT studyRoom.roomName, s.startTime, s.endTime
FROM studyRoom
JOIN reservation r on studyRoom.studyRoomId = r.studyRoomId
JOIN shift s on r.shiftId = s.shiftId
WHERE r.date = '2024-04-29';

SELECT studyRoom.roomName, s.startTime, s.endTime
FROM studyRoom
LEFT JOIN reservation r on studyRoom.studyRoomId = r.studyRoomId
JOIN shift s on r.shiftId = s.shiftId

/*INSERT INTO user
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
/*
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
GROUP BY career.careerName, faculty.facultyName;*/
