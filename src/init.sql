DROP DATABASE IF EXISTS ObligatorioBDD;
CREATE DATABASE ObligatorioBDD CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ObligatorioBDD;
SET NAMES utf8mb4;
SET character_set_client = utf8mb4;
SET character_set_connection = utf8mb4;
SET character_set_results = utf8mb4;

CREATE TABLE campus (
    campusName VARCHAR(32) PRIMARY KEY CHECK ( CHAR_LENGTH(campusName) >= 5 )
);

CREATE TABLE user (
	ci INT PRIMARY KEY,
	name VARCHAR(32) NOT NULL CHECK ( CHAR_LENGTH(name) >= 3 ),
    lastName VARCHAR(32) NOT NULL CHECK ( CHAR_LENGTH(lastName) >= 3 ),
    isActive BOOLEAN NOT NULL DEFAULT TRUE,
    mail VARCHAR(50) UNIQUE CHECK ( LOWER(mail) LIKE '%@correo.ucu.edu.uy' OR LOWER(mail) LIKE '%@ucu.edu.uy')
);

CREATE TABLE faculty (
	facultyId INT PRIMARY KEY AUTO_INCREMENT,
	facultyName VARCHAR(100) CHECK ( CHAR_LENGTH(facultyName) >= 3 )
);

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
	campus VARCHAR(32) NOT NULL,
    image VARCHAR(300) DEFAULT 'https://www.fivebranches.edu/wp-content/uploads/2021/08/default-image.jpg',
    FOREIGN KEY (campus) REFERENCES campus(campusName)
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
    roomType ENUM('Libre', 'Posgrado', 'Docente') DEFAULT 'Libre' NOT NULL,
    status ENUM('Activo', 'Inactivo') DEFAULT 'Activo' NOT NULL,
	FOREIGN KEY (buildingName) REFERENCES building(buildingName)
);

CREATE TABLE studyGroup (
    studyGroupId INT PRIMARY KEY AUTO_INCREMENT,
    studyGroupName VARCHAR(50) NOT NULL,
    status ENUM('Activo', 'Inactivo') DEFAULT 'Activo' NOT NULL,
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
	ci INT NOT NULL,
	careerId INT NOT NULL,
    campus VARCHAR(32),
    FOREIGN KEY (campus) REFERENCES campus(campusName),
	FOREIGN KEY (ci) REFERENCES user(ci),
	FOREIGN KEY (careerId) REFERENCES career(careerId),
    PRIMARY KEY(ci, careerId)
);

CREATE TABLE professor (
	ci INT PRIMARY KEY,
    campus VARCHAR(32),
    FOREIGN KEY (campus) REFERENCES campus(campusName),
	FOREIGN KEY (ci) REFERENCES user(ci)
);

CREATE TABLE administrator (
	ci INT PRIMARY KEY,
	FOREIGN KEY (ci) REFERENCES user(ci)
);

CREATE TABLE librarian (
	ci INT PRIMARY KEY,
    buildingName VARCHAR(32),
    FOREIGN KEY (buildingName) REFERENCES building(buildingName),
	FOREIGN KEY (ci) REFERENCES user(ci)
);

CREATE TABLE reservation (
    studyGroupId INT NOT NULL,
	studyRoomId INT NOT NULL,
	date DATE NOT NULL,
    shiftId INT NOT NULL,
    assignedLibrarian INT,
    reservationCreateDate DATE NOT NULL DEFAULT (CURRENT_DATE),
	state ENUM('Activa', 'Cancelada', 'Sin asistencia', 'Finalizada') DEFAULT 'Activa' NOT NULL,
    FOREIGN KEY (studyGroupId) REFERENCES studyGroup(studyGroupId),
	FOREIGN KEY (studyRoomId) REFERENCES studyRoom(studyRoomId),
    FOREIGN KEY (shiftId) REFERENCES shift(shiftId),
    FOREIGN KEY (assignedLibrarian) REFERENCES librarian(ci),
    PRIMARY KEY (studyGroupId, studyRoomId, date, shiftId)
);

CREATE TABLE groupRequest (
    studyGroupId INT,
	receiver INT,
	status ENUM('Aceptada', 'Pendiente', 'Rechazada') DEFAULT 'Pendiente' NOT NULL,
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
	description ENUM('Comer', 'Ruidoso', 'Vandalismo', 'Imprudencia', 'Ocupar', 'No Asiste') NOT NULL,
	startDate DATE NOT NULL,
    endDate DATE NOT NULL,
    FOREIGN KEY (ci) REFERENCES user(ci),
	FOREIGN KEY (librarianCi) REFERENCES librarian(ci)
);

/**** INSERTIONS ****/

INSERT INTO campus VALUES
('Montevideo'),
('Punta del Este'),
('Salto');

INSERT INTO user (ci, name, lastName, mail) VALUES
(55897692, 'Agostina', 'Etchebarren', 'agostina.etchebarren@correo.ucu.edu.uy'),
(55531973, 'Santiago', 'Aguerre', 'santiago.aguerre@correo.ucu.edu.uy'),
(57004718, 'Thiago', 'Garcia', 'thiago.garcia@correo.ucu.edu.uy'),
(55299080, 'Martina', 'Caetano', 'martina.caetano@correo.ucu.edu.uy'),
(56309531, 'Pilar', 'Antelo', 'pilar.antelo@correo.ucu.edu.uy'),
(56902752, 'Facundo', 'Píriz', 'facundo.piriz@correo.ucu.edu.uy'),
(59283629, 'Diego', 'de Oliveira', 'diego.deoliveira@correo.ucu.edu.uy'),
(52435831, 'Santiago', 'Blanco', 'santiago.blanco@correo.ucu.edu.uy'),
(54729274, 'Lucia', 'Mallada', 'lucia.mallada@correo.ucu.edu.uy'),
(52737428, 'Luana', 'Biurarrena', 'luana.biurarrena@correo.ucu.edu.uy'),
(57389261, 'Ramiro', 'Casco', 'ramiro.casco@correo.ucu.edu.uy'),
(32124436, 'Lourdes', 'Machado', 'lourdes.machado@ucu.edu.uy'),
(36907777, 'David', 'Liesegang', 'david.liesegang@ucu.edu.uy'),
(34567836, 'Rodrigo', 'Díaz', 'rodrigo.diaz@ucu.edu.uy'),
(45615815, 'Martha', 'Lauria', 'martha.lauria@ucu.edu.uy'),
(12345678, 'Verónica', 'Posadas', 'veronica.posadas@ucu.edu.uy'),
(45673829, 'Franco', 'Portela', 'franco.portela@ucu.edu.uy'),
(32749352, 'Saúl', 'Esquivel', 'saul.esquivel@ucu.edu.uy'),
(25081560, 'Paola', 'Brun', 'paola.brun@ucu.edu.uy'),
(18595003, 'Fabián', 'Aguerre', 'fabian.aguerre@ucu.edu.uy');

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
('agostina.etchebarren@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('santiago.aguerre@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('thiago.garcia@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('martina.caetano@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('pilar.antelo@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('facundo.piriz@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('diego.deoliveira@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('santiago.blanco@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('lucia.mallada@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('luana.biurarrena@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('ramiro.casco@correo.ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('lourdes.machado@ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('david.liesegang@ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('rodrigo.diaz@ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('martha.lauria@ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('veronica.posadas@ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('saul.esquivel@ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('paola.brun@ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'), -- agostina2006
('fabian.aguerre@ucu.edu.uy', '$2b$16$XwajVoE75BbZUDEf0aFsKuWIkDMudlreTmQ2uH1yeq.z5vCbbNbSG'); -- agostina2006

INSERT INTO building VALUES
('Central', 'Av. 8 de Octubre 2738', 'Montevideo', 'https://pbs.twimg.com/media/ETCIXdTXQAEN2t8.jpg'),
('San Ignacio', 'Cornelio Cantera 2731', 'Montevideo', 'https://www.ucu.edu.uy/imgnoticias/202304/W950_H580/1596.jpg'),
('Mullin', 'Cmdt. Braga 2745', 'Montevideo', 'https://upload.wikimedia.org/wikipedia/commons/0/0b/EDIFICIO_MULLIN_UCU.jpg'),
('San José', 'Av. 8 de Octubre 2733', 'Montevideo', 'https://medios.presidencia.gub.uy/tav_portal/2025/noticias/AN_361/fgr_01.jpg'),
('Semprún', 'Estero Bellaco 2771', 'Montevideo', 'https://ciemsa.com.uy/wp-content/uploads/2022/09/37_ucu_1.jpeg'),
('Athanasius', 'Gral. Urquiza 2871', 'Montevideo', 'https://www.ucu.edu.uy/imgnoticias/202208/H950/140.jpeg'),
('Central Pta. del Este', 'equina Florencia Pda. 7 y 1/2', 'Punta del Este', 'https://www.ucu.edu.uy/imgnoticias/202411/H950/4798.jpg'),
('Central Salto', 'Artigas 1251', 'Salto', 'https://www.ucu.edu.uy/imgnoticias/202304/H950/1626.jpg');

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
(NULL, 'Sala 1', 'Central', 6, 'Libre', DEFAULT),
(NULL, 'Sala 2', 'Central', 8, 'Posgrado', DEFAULT),
(NULL, 'Sala 3', 'Central', 14, 'Docente', DEFAULT),
(NULL, 'Sala 1', 'San Ignacio', 20, 'Libre', DEFAULT),
(NULL, 'Sala 2', 'San Ignacio', 8, 'Posgrado', DEFAULT),
(NULL, 'Sala 3', 'San Ignacio', 6, 'Docente', DEFAULT),
(NULL, 'Sala 1', 'Mullin', 8, 'Libre', DEFAULT),
(NULL, 'Sala 2', 'Mullin', 6, 'Posgrado', DEFAULT),
(NULL, 'Sala 3', 'Mullin', 10, 'Docente', DEFAULT),
(NULL, 'Sala 1', 'San José', 12, 'Libre', DEFAULT),
(NULL, 'Sala 2', 'San José', 16, 'Posgrado', DEFAULT),
(NULL, 'Sala 3', 'San José', 6, 'Docente', DEFAULT),
(NULL, 'Sala 1', 'Semprún', 6, 'Libre', DEFAULT),
(NULL, 'Sala 2', 'Semprún', 6, 'Posgrado', DEFAULT),
(NULL, 'Sala 3', 'Semprún', 10, 'Docente', DEFAULT),
(NULL, 'Sala 1', 'Athanasius', 6, 'Libre', DEFAULT),
(NULL, 'Sala 2', 'Athanasius', 10, 'Posgrado', DEFAULT),
(NULL, 'Sala 3', 'Athanasius', 10, 'Docente', DEFAULT),
(NULL, 'Sala 2', 'Central Salto', 6, 'Posgrado', DEFAULT),
(NULL, 'Sala 3', 'Central Salto', 10, 'Docente', DEFAULT),
(NULL, 'Sala 1', 'Central Salto', 6, 'Libre', DEFAULT),
(NULL, 'Sala 2', 'Central Pta. del Este', 6, 'Posgrado', DEFAULT),
(NULL, 'Sala 3', 'Central Pta. del Este', 10, 'Docente', DEFAULT),
(NULL, 'Sala 1', 'Central Pta. del Este', 6, 'Libre', DEFAULT);

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
(55897692, 6, 'Montevideo'),
(55531973, 6, 'Montevideo'),
(57004718, 6, 'Montevideo'),
(55299080, 7, 'Montevideo'),
(56309531, 6, 'Montevideo'),
(56902752, 6, 'Montevideo'),
(59283629, 6, 'Punta del Este'),
(52435831, 6, 'Punta del Este'),
(54729274, 3, 'Punta del Este'),
(52737428, 3, 'Salto'),
(57389261, 4, 'Salto');

INSERT INTO professor VALUES
(36907777, 'Punta del Este'),
(34567836, 'Salto'),
(45615815, 'Punta del Este'),
(45673829, 'Montevideo'),
(32749352, 'Montevideo');

INSERT INTO administrator VALUES
(12345678);

INSERT INTO librarian VALUES
(32124436, 'Central'),
(25081560, 'Central Pta. del Este'),
(18595003, 'Central Salto');

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


CREATE USER 'unknown_user'@'%' IDENTIFIED BY 'Unknown19976543!';
CREATE USER 'student_user'@'%' IDENTIFIED BY 'Student19976543!';
CREATE USER 'professor_user'@'%' IDENTIFIED BY 'Professor19976543!';
CREATE USER 'administrator_user'@'%' IDENTIFIED BY 'Admin19976543!';
CREATE USER 'librarian_user'@'%' IDENTIFIED BY 'Librarian19976543!';


# GRANTS UNKNOWN
GRANT INSERT, SELECT ON ObligatorioBDD.login TO 'unknown_user'@'%';
GRANT INSERT, SELECT ON ObligatorioBDD.student TO 'unknown_user'@'%';
GRANT SELECT ON ObligatorioBDD.professor TO 'unknown_user'@'%';
GRANT SELECT ON ObligatorioBDD.librarian TO 'unknown_user'@'%';
GRANT SELECT ON ObligatorioBDD.administrator TO 'unknown_user'@'%';
GRANT INSERT, SELECT ON ObligatorioBDD.user TO 'unknown_user'@'%';
GRANT SELECT ON ObligatorioBDD.campus TO 'unknown_user'@'%';
GRANT SELECT ON ObligatorioBDD.career TO 'unknown_user'@'%';

# GRANTS STUDENTS
GRANT SELECT ON ObligatorioBDD.campus TO 'student_user'@'%';
GRANT SELECT, UPDATE ON ObligatorioBDD.user TO 'student_user'@'%';
GRANT SELECT ON ObligatorioBDD.faculty TO 'student_user'@'%';
GRANT SELECT ON ObligatorioBDD.career TO 'student_user'@'%';
GRANT SELECT, UPDATE ON ObligatorioBDD.login TO 'student_user'@'%';
GRANT SELECT ON ObligatorioBDD.building TO 'student_user'@'%';
GRANT SELECT ON ObligatorioBDD.shift TO 'student_user'@'%';
GRANT SELECT ON ObligatorioBDD.studyroom TO 'student_user'@'%';
GRANT INSERT, SELECT, UPDATE, DELETE ON ObligatorioBDD.studygroup TO 'student_user'@'%';
GRANT ALL PRIVILEGES ON ObligatorioBDD.studyGroupParticipant TO 'student_user'@'%';
GRANT SELECT, UPDATE ON ObligatorioBDD.student TO 'student_user'@'%';
GRANT SELECT ON ObligatorioBDD.professor TO 'student_user'@'%';
GRANT INSERT ON ObligatorioBDD.sanction TO 'student_user'@'%';
GRANT ALL PRIVILEGES ON ObligatorioBDD.reservation TO 'student_user'@'%';
GRANT SELECT ON ObligatorioBDD.librarian TO 'student_user'@'%';
GRANT ALL PRIVILEGES ON ObligatorioBDD.groupRequest TO 'student_user'@'%';
GRANT SELECT ON ObligatorioBDD.sanction TO 'student_user'@'%';

# GRANTS PORFESSOR
GRANT SELECT ON ObligatorioBDD.campus TO 'professor_user'@'%';
GRANT SELECT, UPDATE ON ObligatorioBDD.user TO 'professor_user'@'%';
GRANT SELECT ON ObligatorioBDD.faculty TO 'professor_user'@'%';
GRANT SELECT ON ObligatorioBDD.career TO 'professor_user'@'%';
GRANT SELECT, UPDATE ON ObligatorioBDD.login TO 'professor_user'@'%';
GRANT SELECT ON ObligatorioBDD.building TO 'professor_user'@'%';
GRANT INSERT ON ObligatorioBDD.sanction TO 'professor_user'@'%';
GRANT SELECT ON ObligatorioBDD.shift TO 'professor_user'@'%';
GRANT SELECT ON ObligatorioBDD.studyroom TO 'professor_user'@'%';
GRANT INSERT, SELECT, UPDATE, DELETE ON ObligatorioBDD.studygroup TO 'professor_user'@'%';
GRANT ALL PRIVILEGES ON ObligatorioBDD.studyGroupParticipant TO 'professor_user'@'%';
GRANT SELECT ON ObligatorioBDD.student TO 'professor_user'@'%';
GRANT SELECT, UPDATE ON ObligatorioBDD.professor TO 'professor_user'@'%';
GRANT ALL PRIVILEGES ON ObligatorioBDD.reservation TO 'professor_user'@'%';

GRANT SELECT ON ObligatorioBDD.librarian TO 'professor_user'@'%';

GRANT ALL PRIVILEGES ON ObligatorioBDD.groupRequest TO 'professor_user'@'%';
GRANT SELECT ON ObligatorioBDD.sanction TO 'professor_user'@'%';

# GRANTS LIBRARIAN
GRANT SELECT ON ObligatorioBDD.campus TO 'librarian_user'@'%';
GRANT SELECT, UPDATE ON ObligatorioBDD.user TO 'librarian_user'@'%';
GRANT SELECT ON ObligatorioBDD.career TO 'librarian_user'@'%';
GRANT SELECT, UPDATE ON ObligatorioBDD.login TO 'librarian_user'@'%';
GRANT SELECT ON ObligatorioBDD.building TO 'librarian_user'@'%';
GRANT SELECT ON ObligatorioBDD.shift TO 'librarian_user'@'%';
GRANT SELECT ON ObligatorioBDD.studyroom TO 'librarian_user'@'%';
GRANT ALL PRIVILEGES ON ObligatorioBDD.studygroup TO 'librarian_user'@'%';
GRANT ALL PRIVILEGES ON ObligatorioBDD.studyGroupParticipant TO 'librarian_user'@'%';
GRANT SELECT ON ObligatorioBDD.user TO 'librarian_user'@'%';
GRANT SELECT ON ObligatorioBDD.professor TO 'librarian_user'@'%';
GRANT SELECT, UPDATE ON ObligatorioBDD.librarian TO 'librarian_user'@'%';
GRANT ALL PRIVILEGES ON ObligatorioBDD.reservation TO 'librarian_user'@'%';
GRANT ALL PRIVILEGES ON ObligatorioBDD.groupRequest TO 'librarian_user'@'%';
GRANT ALL PRIVILEGES ON ObligatorioBDD.sanction TO 'librarian_user'@'%';

# GRANTS ADMINISTRATOR
GRANT ALL PRIVILEGES ON ObligatorioBDD.* TO 'administrator_user'@'%';