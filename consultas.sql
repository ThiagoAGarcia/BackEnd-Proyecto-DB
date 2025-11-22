USE ObligatorioBDD;

-- Salas mas reservadas --
SELECT COUNT(r.studyRoomId) AS CantidadDeReservasPor, sR.roomName AS Sala, sR.buildingName AS Edificio
FROM reservation r
JOIN studyRoom sR on r.studyRoomId = sR.studyRoomId
GROUP BY r.studyRoomId
ORDER BY CantidadDeReservasPor DESC;

-- Turnos más demandados --
SELECT COUNT() AS cantidad_reservas, s.startTime, s.endTime FROM reservation r
JOIN shift s on r.shiftId = s.shiftId
GROUP BY s.startTime, s.endTime
ORDER BY cantidad_reservas DESC;

-- Promedio de participantes por sala --
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

-- Cantidad de reservas por carrera y facultad (Los grupos no tienen por qué ser de una carrera en especial, esta consulta devuelve las reservas teniendo en cuenta la carrera del líder de cada grupo) --
SELECT COUNT(*) AS CantidadReservasPor, c.careerName AS Carrera, f.facultyName AS Facultad
FROM reservation r
JOIN studyGroup sG ON r.studyGroupId = sG.studyGroupId
JOIN student s ON sG.leader = s.ci
JOIN career c ON s.careerId = c.careerId
JOIN faculty f on c.facultyId = f.facultyId
GROUP BY Carrera, Facultad;

-- Porcentaje de ocupación de salas por edificio --
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

-- Cantidad de reservas y asistencias de profesores y alumnos (grado y posgrado) --
SELECT COUNT(*) AS CantidadReservas
FROM reservation r
WHERE r.state = 'Finalizada' OR r.state = 'Activa';

-- Cantidad de sanciones para profesores y alumnos (grado y posgrado) --
SELECT u.ci, u.name, u.lastName, COUNT() AS sanciones
FROM sanction sa
JOIN user u ON sa.ci = u.ci
LEFT JOIN student s ON u.ci = s.ci
LEFT JOIN professor p ON u.ci = p.ci
WHERE s.ci IS NOT NULL OR p.ci IS NOT NULL
GROUP BY u.ci
ORDER BY sanciones DESC;

-- Porcentaje de reservas efectivamente utilizadas vs. canceladas/no asistidas --
SELECT
    SUM(CASE WHEN state = 'Finalizada' THEN 1 ELSE 0 END)/COUNT(*) * 100 AS Finalizada,
    SUM(CASE WHEN state = 'Cancelada' THEN 1 ELSE 0 END)/COUNT(*) * 100 AS Cancelada
FROM reservation;

-- Salas libres por fecha --
SELECT sR.roomName AS Sala, sR.buildingName AS Edificio, s.startTime AS Inicio, s.endTime AS Fin
FROM studyRoom sR
JOIN shift s
WHERE (sR.studyRoomId, s.shiftId) NOT IN (
        SELECT r.studyRoomId, r.shiftId
        FROM reservation r
        WHERE r.date = '2024-04-29'
    )
ORDER BY Inicio, Fin DESC;

/* De acá para abajo ver algunos mas utiles */
-- Mostrar los usuarios que no formen parte de cierto grupo --
SELECT CONCAT(u.name, ' ', u.lastName) AS MiembroNoFormaParteDeGrupoDado
FROM user u
WHERE CONCAT(u.name, ' ', u.lastName) NOT IN (
    SELECT CONCAT(u.name, ' ', u.lastName)
    FROM user u
    JOIN groupRequest gR ON u.ci = gR.receiver
    WHERE gR.studyGroupId = 1
        UNION
    SELECT CONCAT(u.name, ' ', u.lastName)
    FROM user u
    JOIN studyGroup sG ON u.ci = sG.leader
    WHERE sG.studyGroupId = 1
);;

-- Mostrar todas las reservas que administró un bibliotecario --
SELECT * FROM reservation r
WHERE r.assignedLibrarian = 32124436;

-- Cantidad de grupos por carrera (Los grupos no tienen por qué ser de una carrera en especial, esta consulta devuelve los grupos agrupados por la carrera del líder) --
SELECT COUNT(studyGroup.studyGroupName) AS CantidadDeGruposPor, c.careerName AS Carrera
FROM studyGroup
JOIN student s ON studyGroup.leader = s.ci
JOIN career c ON s.careerId = c.careerId
GROUP BY c.careerName;