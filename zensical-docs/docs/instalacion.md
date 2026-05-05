---
icon: lucide/package
---

# Instalación

## Requisitos previos

- Python 3.13+
- PostgreSQL 14+
- Git

## Pasos

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd Gestor-de-flujo-de-trabajo/taskflow/taskmanager
```

### 2. Crear y activar el entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate  # Linux / macOS
venv\Scripts\activate     # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crea un fichero `.env` en la raíz del proyecto (`taskflow/taskmanager/`):

```ini
SECRET_KEY=cambia-esto-por-una-clave-segura
DEBUG=True
DATABASE_URL=postgres://usuario:contraseña@localhost:5432/easydb
ALLOWED_HOSTS=127.0.0.1,localhost
```

!!! tip "python-decouple"
    E-asy usa `python-decouple` para leer variables de entorno desde `.env`. No necesitas exportarlas en la shell.

### 5. Crear la base de datos

```bash
createdb easydb  # con el usuario de PostgreSQL adecuado
```

### 6. Aplicar migraciones

```bash
python manage.py migrate
```

### 7. Crear superusuario

```bash
python manage.py createsuperuser
```

### 8. Arrancar el servidor

```bash
python manage.py runserver
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000) en el navegador.

---

## Ficheros estáticos en producción

WhiteNoise sirve los estáticos directamente desde Django sin necesitar un servidor web separado. Para producción:

```bash
python manage.py collectstatic
```

Y establece `DEBUG=False` en el `.env`.

## Dependencias principales

| Paquete | Versión | Función |
|---------|---------|---------|
| Django | 5.0.4 | Framework web |
| psycopg2-binary | ≥ 2.9.10 | Driver PostgreSQL |
| djangorestframework | ≥ 3.15.0 | API REST |
| djangorestframework-simplejwt | ≥ 5.3.0 | Autenticación JWT |
| django-otp | ≥ 1.5.0 | Autenticación de dos factores |
| django-ratelimit | ≥ 4.1.0 | Límite de peticiones |
| Pillow | ≥ 10.3.0 | Avatares e imágenes |
| openpyxl | ≥ 3.1.0 | Exportación a Excel |
| python-decouple | 3.8 | Configuración por entorno |
| whitenoise | 6.6.0 | Estáticos en producción |
