from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "segredo_super_secreto"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tarefas.db"
db = SQLAlchemy(app)

# --- MODELOS ---

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

    usuario = db.relationship("Usuario", backref="conquistas")
    conquista = db.relationship("Conquista", backref="usuarios")

# --- Inicializar conquistas ---
with app.app_context():
    conquistas = [
        Conquista(nome="Primeira Tarefa", descricao="Concluiu sua primeira tarefa!", icone="/static/icons/task1.png"),
        Conquista(nome="Nível 2", descricao="Alcançou o nível 2!", icone="/static/icons/level2.png"),
        Conquista(nome="Nível 5", descricao="Alcançou o nível 5!", icone="/static/icons/level5.png"),
    ]
    for c in conquistas:
        if not Conquista.query.filter_by(nome=c.nome).first():
            db.session.add(c)
    db.session.commit()

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
    if "usuario_id" in session:
        usuario = Usuario.query.get(session["usuario_id"])
    return render_template("index.html", usuario=usuario)

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
    tarefa = Tarefa(descricao=descricao, usuario_id=session["usuario_id"])
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
    jogadores = Usuario.query.order_by(Usuario.xp.desc()).all()
    return render_template("ranking.html", jogadores=jogadores, usuario=usuario)

# --- CRIAR BANCO ---
with app.app_context():
    db.create_all()

# --- RODAR SERVIDOR ---
if __name__ == "__main__":
    app.run(debug=True)

















