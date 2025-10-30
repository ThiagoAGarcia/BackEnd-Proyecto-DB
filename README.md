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
