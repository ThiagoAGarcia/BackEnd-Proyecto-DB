# BackEnd-Proyecto-DB

**Para correr docker:**

¡¡¡ Seguir en orden los siguientes pasos !!!

1. Entrar al directorio `src`

   ```powershell
   cd src
   ```
2. Crear y activar el entorno virtual

   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Instalar dependencias

   ```powershell
   pip install -r requirements.txt
   ```
4. Construir la imagen de Docker

   ```powershell
   docker build -t flask-backend .
   ```
5. Levantar los contenedores con Docker Compose

   ```powershell
   docker-compose up --build
   ```
---


USUARIO ADMIN:
veronica.posadas@ucu.edu.uy

USUARIO BIBLIOTECARIO:
lourdes.machado@ucu.edu.uy

USUARIO PROFESOR:
saul.esquivel@ucu.edu.uy

USUARIO ESTUDIANTE:
agostina.etchebarren@correo.ucu.edu.uy
thiago.garcia@correo.ucu.edu.uy
santiago.aguerre@correo.ucu.edu.uy

CONTRASEÑAS:
agostina2006

NO SE ENOJEN ERA UNA CONTRASEÑA QUE COMO LA EMPEZAMOS A USAR TODOS AL INICIO NOS QUEDO ENTONCES QUEDO ESA PARA TODO :)
