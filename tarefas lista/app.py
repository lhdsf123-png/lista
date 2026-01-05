from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date


app = Flask(__name__)
app.secret_key = "segredo_super_secreto"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tarefas.db"
db = SQLAlchemy(app)

# --- MODELOS ---

class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class Amizade(db.Model):
    __tablename__ = "amizades"
    id = db.Column(db.Integer, primary_key=True)
    remetente_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    status = db.Column(db.String(20), default="pendente")  # pendente, aceito, recusado

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    xp = db.Column(db.Integer, default=0)
    nivel = db.Column(db.Integer, default=1)
    musica_url = db.Column(db.String(300), nullable=True)
    autoplay = db.Column(db.Boolean, default=True)
    tarefas = db.relationship("Tarefa", backref="usuario", lazy=True)
    ultimo_login = db.Column(db.Date, default=datetime.date.today)
    dias_consecutivos = db.Column(db.Integer, default=0)

    def ganhar_xp(self, quantidade):
        self.xp += quantidade
        while self.xp >= self.nivel * 50:
            self.nivel += 1
            # conquista de nível
            conquista = Conquista.query.filter_by(nome=f"Nível {self.nivel}").first()
            if conquista:
                if not UsuarioConquista.query.filter_by(usuario_id=self.id, conquista_id=conquista.id).first():
                    uc = UsuarioConquista(usuario_id=self.id, conquista_id=conquista.id)
                    db.session.add(uc)

class Tarefa(db.Model):
    __tablename__ = "tarefas"
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    dia = db.Column(db.Date, default=datetime.date.today)
    concluida = db.Column(db.Boolean, default=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

class Conquista(db.Model):
    __tablename__ = "conquistas"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    icone = db.Column(db.String(200), nullable=True)

class UsuarioConquista(db.Model):
    __tablename__ = "usuario_conquistas"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    conquista_id = db.Column(db.Integer, db.ForeignKey("conquistas.id"), nullable=False)
    data = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    usuario = db.relationship("Usuario", backref="conquistas")
    conquista = db.relationship("Conquista", backref="usuarios")

# --- ROTAS ---

@app.route("/")
def menu():
    return render_template("menu.html")

@app.route("/config-musica", methods=["GET", "POST"])
def config_musica():
    if "usuario_id" not in session:
        return redirect(url_for("index"))
    usuario = Usuario.query.get(session["usuario_id"])
    if request.method == "POST":
        usuario.musica_url = request.form.get("musica_url")
        usuario.autoplay = True if request.form.get("autoplay") else False
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("config_musica.html", usuario=usuario)

@app.route("/index")
def index():
    usuario = None
    usuario_amizades = []
    if "usuario_id" in session:
        usuario = Usuario.query.get(session["usuario_id"])
        usuario_amizades = Amizade.query.filter(
            (Amizade.remetente_id == usuario.id) | (Amizade.destinatario_id == usuario.id)
        ).all()
    return render_template("index.html", usuario=usuario, usuario_amizades=usuario_amizades)

@app.route("/register", methods=["POST"])
def register():
    nome = request.form.get("nome")
    email = request.form.get("email")
    senha = request.form.get("senha")

    if Usuario.query.filter_by(email=email).first():
        return "Email já registrado!"

    senha_hash = generate_password_hash(senha)
    usuario = Usuario(nome=nome, email=email, senha=senha_hash)
    db.session.add(usuario)
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    senha = request.form.get("senha")

    usuario = Usuario.query.filter_by(email=email).first()
    if usuario and check_password_hash(usuario.senha, senha):
        hoje = datetime.date.today()
        if usuario.ultimo_login == hoje - datetime.timedelta(days=1):
            usuario.dias_consecutivos += 1
        elif usuario.ultimo_login != hoje:
            usuario.dias_consecutivos = 1
        usuario.ultimo_login = hoje

        # Conquista de streak
        conquista = Conquista.query.filter_by(nome=f"{usuario.dias_consecutivos} Dias Seguidos").first()
        if conquista and not UsuarioConquista.query.filter_by(
            usuario_id=usuario.id, conquista_id=conquista.id
        ).first():
            uc = UsuarioConquista(usuario_id=usuario.id, conquista_id=conquista.id)
            db.session.add(uc)

        db.session.commit()
        session["usuario_id"] = usuario.id
        return redirect(url_for("index"))
    return "Login inválido!"

@app.route("/logout")
def logout():
    session.pop("usuario_id", None)
    return redirect(url_for("index"))

@app.route("/add", methods=["POST"])
def add_tarefa():
    if "usuario_id" not in session:
        return redirect(url_for("index"))

    descricao = request.form.get("descricao")
    dia = request.form.get("dia")
    dia = datetime.datetime.strptime(dia, "%Y-%m-%d").date() if dia else datetime.date.today()

    tarefa = Tarefa(descricao=descricao, dia=dia, usuario_id=session["usuario_id"])
    db.session.add(tarefa)
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/concluir/<int:tarefa_id>")
def concluir_tarefa(tarefa_id):
    if "usuario_id" not in session:
        return redirect(url_for("index"))

    tarefa = Tarefa.query.get(tarefa_id)
    if tarefa and not tarefa.concluida and tarefa.usuario_id == session["usuario_id"]:
        tarefa.concluida = True
        usuario = Usuario.query.get(session["usuario_id"])
        usuario.ganhar_xp(10)
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/ranking")
def ranking():
    if "usuario_id" not in session:
        return redirect(url_for("index"))
    usuario = Usuario.query.get(session["usuario_id"])

    # Ranking global
    jogadores = Usuario.query.order_by(Usuario.xp.desc()).all()

    # Ranking só entre amigos (amizades aceitas)
    amizades = Amizade.query.filter(
        ((Amizade.remetente_id == usuario.id) | (Amizade.destinatario_id == usuario.id)) &
        (Amizade.status == "aceito")
    ).all()
    amigos_ids = {
        a.remetente_id if a.remetente_id != usuario.id else a.destinatario_id
        for a in amizades
    }
    amigos = Usuario.query.filter(Usuario.id.in_(amigos_ids)).order_by(Usuario.xp.desc()).all()

    return render_template("ranking.html", jogadores=jogadores, amigos=amigos, usuario=usuario)

@app.route("/send-friend-request/<int:receiver_id>", methods=["POST"])
def send_friend_request(receiver_id):
    sender_id = current_user.id  # supondo que você tenha login
    request = FriendRequest(sender_id=sender_id, receiver_id=receiver_id)
    db.session.add(request)
    db.session.commit()
    return jsonify({"message": "Solicitação enviada!"})
    
@app.route("/respond-friend-request/<int:request_id>", methods=["POST"])
def respond_friend_request(request_id):
    action = request.json.get("action")  # "accept" ou "reject"
    request = FriendRequest.query.get(request_id)
    if action == "accept":
        request.status = "accepted"
    elif action == "reject":
        request.status = "rejected"
    db.session.commit()
    return jsonify({"message": f"Solicitação {action}!"})

@app.route("/friend-requests", methods=["GET"])
def list_friend_requests():
    requests = FriendRequest.query.filter_by(receiver_id=current_user.id, status="pending").all()
    return jsonify([{"id": r.id, "sender": r.sender_id} for r in requests])

@app.route("/amizade/enviar/<int:destinatario_id>")
def enviar_amizade(destinatario_id):
    if "usuario_id" not in session:
        return redirect(url_for("index"))

    # Evita duplicar solicitação pendente
    existente = Amizade.query.filter_by(
        remetente_id=session["usuario_id"],
        destinatario_id=destinatario_id,
        status="pendente"
    ).first()
    if not existente:
        amizade = Amizade(remetente_id=session["usuario_id"], destinatario_id=destinatario_id)
        db.session.add(amizade)
        db.session.commit()
    return redirect(url_for("ranking"))

@app.route("/amizade/aceitar/<int:amizade_id>")
def aceitar_amizade(amizade_id):
    if "usuario_id" not in session:
        return redirect(url_for("index"))

    amizade = Amizade.query.get(amizade_id)
    if amizade and amizade.destinatario_id == session["usuario_id"]:
        amizade.status = "aceito"
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/amizade/recusar/<int:amizade_id>")
def recusar_amizade(amizade_id):
    if "usuario_id" not in session:
        return redirect(url_for("index"))

    amizade = Amizade.query.get(amizade_id)
    if amizade and amizade.destinatario_id == session["usuario_id"]:
        amizade.status = "recusado"
        db.session.commit()
    return redirect(url_for("index"))@app.route("/")


# --- CRIAR BANCO ---
with app.app_context():
    db.create_all()

# --- RODAR SERVIDOR ---
if __name__ == "__main__":

    app.run(debug=True)









