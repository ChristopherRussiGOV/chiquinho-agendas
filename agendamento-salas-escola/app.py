import os
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

import config
from email_utils import send_notification
from extensions import db
from models import Booking, NotificationEmail, SystemConfig, User, init_default_data

app = Flask(__name__)
app.config.from_object(config)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Faça login para continuar."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash("Você não tem permissão para acessar esta página.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def validate_institutional_email(email: str) -> bool:
    email = email.strip().lower()
    if "@" not in email:
        return False
    domain = email.split("@", 1)[1]
    return any(domain == d or domain.endswith("." + d) for d in config.ALLOWED_EMAIL_DOMAINS)


def parse_booking_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def times_overlap(start1, end1, start2, end2) -> bool:
    return start1 < end2 and start2 < end1


@app.context_processor
def inject_globals():
    return {
        "ROLES": config.ROLES,
        "ROOMS": config.ROOMS,
        "STATUSES": config.BOOKING_STATUSES,
    }


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if not user:
            flash("Usuário ou e-mail não encontrado.", "error")
            return render_template("login.html")

        if user.must_reset_password or not user.password_hash:
            return render_template("set_password.html", user=user, forced=True)

        if not user.check_password(password):
            flash("Senha incorreta.", "error")
            return render_template("login.html")

        login_user(user)
        flash(f"Bem-vindo(a), {user.username}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if len(username) < 3:
            flash("Nome de usuário deve ter pelo menos 3 caracteres.", "error")
        elif not validate_institutional_email(email):
            flash(
                "Use um e-mail institucional válido (domínios permitidos: "
                + ", ".join(config.ALLOWED_EMAIL_DOMAINS)
                + ").",
                "error",
            )
        elif len(password) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "error")
        elif password != confirm:
            flash("As senhas não coincidem.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Este nome de usuário já está em uso.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Este e-mail já está cadastrado.", "error")
        else:
            user = User(username=username, email=email, role="visualizador")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Cadastro realizado! Faça login para continuar.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/set-password", methods=["POST"])
def set_password():
    user_id = request.form.get("user_id", type=int)
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    user = db.session.get(User, user_id)
    if not user:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("login"))

    if len(password) < 6:
        flash("A senha deve ter pelo menos 6 caracteres.", "error")
        return render_template("set_password.html", user=user, forced=True)

    if password != confirm:
        flash("As senhas não coincidem.", "error")
        return render_template("set_password.html", user=user, forced=True)

    user.set_password(password)
    db.session.commit()
    login_user(user)
    flash("Senha definida com sucesso!", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/delete-user/<int:user_id>", methods=["POST"])
@role_required("admin")  # Alterado para "admin" conforme seu models.py
def admin_delete_user(user_id):
    # Impede que o admin logado exclua a si mesmo
    if user_id == current_user.id:
        flash("Você não pode excluir sua própria conta.", "error")
        return redirect(url_for("admin_dashboard"))

    user = db.session.get(User, user_id)
    if not user:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        # Remove todos os agendamentos vinculados a esse usuário antes de deletá-lo
        Booking.query.filter_by(teacher_id=user.id).delete()
        
        # Deleta o usuário de fato
        db.session.delete(user)
        db.session.commit()
        
        flash(f"Usuário {user.username} e seus agendamentos foram removidos com sucesso.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao excluir usuário. Tente novamente.", "error")

    return redirect(url_for("admin_dashboard"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/agendar", methods=["GET", "POST"])
@role_required("professor")
def agendar():
    time_slots = SystemConfig.get_active_time_slots()

    if request.method == "POST":
        room = request.form.get("room", "")
        booking_date_str = request.form.get("booking_date", "")
        start_time = request.form.get("start_time", "")
        end_time = request.form.get("end_time", "")

        booking_date = parse_booking_date(booking_date_str)

        if room not in config.ROOMS:
            flash("Sala inválida.", "error")
        elif not booking_date:
            flash("Data inválida.", "error")
        elif booking_date < date.today():
            flash("Não é possível agendar em datas passadas.", "error")
        elif start_time not in time_slots or end_time not in time_slots:
            flash("Horário inválido.", "error")
        elif start_time >= end_time:
            flash("O horário final deve ser posterior ao inicial.", "error")
        else:
            conflict = Booking.query.filter_by(
                room=room, booking_date=booking_date
            ).all()
            has_conflict = any(
                times_overlap(start_time, end_time, b.start_time, b.end_time)
                for b in conflict
            )
            if has_conflict:
                flash("Já existe um agendamento neste horário para esta sala.", "error")
            else:
                booking = Booking(
                    room=room,
                    booking_date=booking_date,
                    start_time=start_time,
                    end_time=end_time,
                    status="agendado",
                    teacher_id=current_user.id,
                )
                db.session.add(booking)
                db.session.commit()

                recipients = [e.email for e in NotificationEmail.query.all()]
                if recipients:
                    body = (
                        f"Novo agendamento registrado:\n\n"
                        f"Professor: {current_user.username}\n"
                        f"Sala: {room}\n"
                        f"Data: {booking_date.strftime('%d/%m/%Y')}\n"
                        f"Horário: {start_time} às {end_time}\n"
                        f"Status: agendado"
                    )
                    send_notification(
                        "Novo agendamento de sala",
                        body,
                        recipients,
                    )

                flash("Agendamento realizado com sucesso!", "success")
                return redirect(url_for("agendamentos"))

    return render_template(
        "agendar.html",
        time_slots=time_slots,
        min_date=date.today().isoformat(),
    )


@app.route("/agendamentos")
@login_required
def agendamentos():
    if not current_user.can_view_bookings():
        flash("Você não tem permissão para ver agendamentos.", "error")
        return redirect(url_for("dashboard"))

    filter_date = request.args.get("date", "")
    query = Booking.query

    if filter_date:
        parsed = parse_booking_date(filter_date)
        if parsed:
            query = query.filter_by(booking_date=parsed)

    bookings = query.order_by(
        Booking.booking_date.desc(), Booking.start_time
    ).all()

    return render_template("agendamentos.html", bookings=bookings, filter_date=filter_date)


@app.route("/agendamentos/<int:booking_id>/presente", methods=["POST"])
@role_required("professor")
def marcar_presente(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash("Agendamento não encontrado.", "error")
        return redirect(url_for("agendamentos"))

    if booking.teacher_id != current_user.id:
        flash("Somente o autor do agendamento pode marcar presença.", "error")
        return redirect(url_for("agendamentos"))

    booking.status = "presente"
    db.session.commit()
    flash("Presença registrada!", "success")
    return redirect(url_for("agendamentos"))


@app.route("/admin")
@role_required("admin", "moderador")
def admin_panel():
    bookings = Booking.query.order_by(
        Booking.booking_date.desc(), Booking.start_time
    ).all()
    users = User.query.order_by(User.username).all()
    time_config = SystemConfig.get_time_config()
    notification_emails = NotificationEmail.query.order_by(NotificationEmail.email).all()

    return render_template(
        "admin.html",
        bookings=bookings,
        users=users,
        time_config=time_config,
        notification_emails=notification_emails,
        is_admin=current_user.is_admin,
    )


@app.route("/admin/booking/<int:booking_id>/status", methods=["POST"])
@role_required("admin")
def admin_update_status(booking_id):
    status = request.form.get("status", "")
    if status not in config.BOOKING_STATUSES:
        flash("Status inválido.", "error")
        return redirect(url_for("admin_panel"))

    booking = db.session.get(Booking, booking_id)
    if booking:
        booking.status = status
        db.session.commit()
        flash("Status atualizado.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/booking/<int:booking_id>/delete", methods=["POST"])
@role_required("admin")
def admin_delete_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking:
        db.session.delete(booking)
        db.session.commit()
        flash("Agendamento excluído.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/bookings/delete-all", methods=["POST"])
@role_required("admin")
def admin_delete_all_bookings():
    Booking.query.delete()
    db.session.commit()
    flash("Todos os agendamentos foram excluídos.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/users/<int:user_id>/role", methods=["POST"])
@role_required("admin")
def admin_update_role(user_id):
    role = request.form.get("role", "")
    if role not in config.ROLES:
        flash("Função inválida.", "error")
        return redirect(url_for("admin_panel"))

    user = db.session.get(User, user_id)
    if user and user.id != current_user.id:
        user.role = role
        db.session.commit()
        flash(f"Função de {user.username} atualizada para {role}.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@role_required("admin", "moderador")
def admin_reset_password(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.password_hash = None
        user.must_reset_password = True
        db.session.commit()
        flash(
            f"Senha de {user.username} removida. O usuário deverá definir uma nova senha no próximo login.",
            "success",
        )
    return redirect(url_for("admin_panel"))


@app.route("/admin/time-slots", methods=["POST"])
@role_required("admin")
def admin_update_time_slots():
    lista1_raw = request.form.get("lista1", "")
    lista2_raw = request.form.get("lista2", "")

    def parse_times(raw):
        return [t.strip() for t in raw.replace("\r", "").split("\n") if t.strip()]

    lista1 = parse_times(lista1_raw)
    lista2 = parse_times(lista2_raw)

    if not lista1 or not lista2:
        flash("Ambas as listas devem ter pelo menos um horário.", "error")
        return redirect(url_for("admin_panel"))

    config_data = SystemConfig.get_time_config()
    config_data["lista1"] = lista1
    config_data["lista2"] = lista2
    SystemConfig.set("time_slots", config_data)
    db.session.commit()
    flash("Horários atualizados.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/time-slots/switch", methods=["POST"])
@role_required("admin", "moderador")
def admin_switch_time_list():
    config_data = SystemConfig.get_time_config()
    config_data["active_list"] = (
        "lista2" if config_data.get("active_list") == "lista1" else "lista1"
    )
    SystemConfig.set("time_slots", config_data)
    db.session.commit()
    active = config_data["active_list"]
    flash(f"Lista ativa alterada para {active}.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/notifications/add", methods=["POST"])
@role_required("admin")
def admin_add_notification_email():
    email = request.form.get("email", "").strip().lower()
    if not email or "@" not in email:
        flash("E-mail inválido.", "error")
    elif NotificationEmail.query.filter_by(email=email).first():
        flash("Este e-mail já está cadastrado.", "error")
    else:
        db.session.add(NotificationEmail(email=email))
        db.session.commit()
        flash("E-mail adicionado para notificações.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/notifications/<int:email_id>/delete", methods=["POST"])
@role_required("admin")
def admin_delete_notification_email(email_id):
    row = db.session.get(NotificationEmail, email_id)
    if row:
        db.session.delete(row)
        db.session.commit()
        flash("E-mail removido.", "success")
    return redirect(url_for("admin_panel"))


with app.app_context():
    db.create_all()
    init_default_data()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
