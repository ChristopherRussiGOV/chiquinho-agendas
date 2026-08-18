import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = os.environ.get("SECRET_KEY", "chave-secreta-agendamento-salas-2026")
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'agendamento.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# E-mails institucionais permitidos (ajuste o domínio da sua escola)
ALLOWED_EMAIL_DOMAINS = ["escola.edu.br", "etec.edu.br", "edu.br"]

# SMTP para notificações (opcional — deixe vazio para registrar no console)
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "agendamento@escola.edu.br")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

DEFAULT_TIME_LIST_1 = [
    "07:00", "07:50", "08:40", "09:30", "10:20", "11:10", "12:00", "12:50", "13:40"
]
DEFAULT_TIME_LIST_2 = [
    "13:00", "13:50", "14:40", "15:30", "16:20", "17:10", "18:00", "18:50", "19:40"
]

ROOMS = ["01", "02", "03", "04"]
ROLES = ["admin", "moderador", "professor", "visualizador"]
BOOKING_STATUSES = ["pendente", "agendado", "reagendado", "presente"]
