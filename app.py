from datetime import datetime, date, timedelta
from flask import Flask, flash, render_template, request, redirect, url_for
from flask_login import UserMixin, LoginManager, login_required, login_user, logout_user, current_user
from sqlalchemy.orm import foreign
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, and_

import sqlite3

app = Flask(__name__)
app.config["DEBUG"] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../database/veiculos.db'
app.config['SECRET_KEY'] = 'password_secreta_segura'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message
login_manager.login_message_category

#Rota de Registo
@app.route('/registo', methods=['GET', 'POST'])
def registo():
    if current_user.is_authenticated:
        return redirect(url_for('index')) #Se cliente já está logado, redirecionado para a pagina inicial

    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email').lower().strip()
        password_plana = request.form.get('password')

        #Verificar se email já existe na base de dados
        email_existe = Cliente.query.filter_by(email = email).first()
        if email_existe:
            flash('Este endereço de email já está registado', 'danger')
            return redirect(url_for('registo'))

        #Encriptação de password segura antes de guardar
        password_encriptada = generate_password_hash(password_plana, method='scrypt')

        #Novo objeto Cliente
        novo_cliente = Cliente(nome=nome, email=email, password=password_encriptada)

        #Guardar dados na base de dados
        db.session.add(novo_cliente)
        db.session.commit()
        flash('Conta criada com sucesso! Pode, agora, iniciar sessão.', 'success')
        return redirect(url_for('login'))
    return render_template('registo.html')

#Rota de Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        password_plana = request.form.get('password')

        #Procurar cliente pelo email
        cliente = Cliente.query.filter_by(email = email).first()

        #Validar se cliente existe e se a password está correta
        if cliente and check_password_hash(cliente.password, password_plana):
            login_user(cliente, True) #flask-login cria automaticamente a sessão do utilizador

            flash(f'Bem-vindo de volta, {cliente.nome}!', 'success')

            #Redireciona para a página que o utilizador tentava aceder antes do Login ou redireciona para o index
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Credenciais incorretas. Tente de novo.', 'danger')
    return render_template('login.html')

#Rota de Logout
@app.route('/logout')
@login_required #Aoenas utilizadores logados podem aceder a esta rota
def logout():
    logout_user() #Limpa a sessão do flask-login
    flash('Terminou a sua sessão com sucesso!', 'info')
    return redirect(url_for('index'))

#Rota que permite ao cliente verificar as suas próprias reservas
@app.route('/minhas-reservas')
@login_required
def minhas_reservas():
    #O "lazy=dynamic" permite que possamos ordenar as reservas diretamente por aqui
    lista_reservas = current_user.reservas.order_by(Reservas.id.desc()).all()
    return render_template('minhas_reservas.html', reservas=lista_reservas)



@login_manager.user_loader
def load_user(user_id):
    return Cliente.query.get(int(user_id))

class Cliente(db.Model, UserMixin):
    __tablename__ = 'Clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    reservas=db.relationship('Reservas', backref='cliente', lazy='dynamic', foreign_keys='Reservas.cliente_id')


class Veiculo(db.Model):
    __tablename__ = "Veiculos"
    id = db.Column(db.Integer, primary_key=True)
    marca = db.Column(db.String(60), nullable=False)
    modelo = db.Column(db.String(60), nullable=False)
    categoria = db.Column(db.String(60), nullable=False)
    tipo_veiculo = db.Column(db.String(60), nullable=False)
    transmissao = db.Column(db.String(60), nullable=False)
    qtd_pessoas = db.Column(db.Integer, nullable=False)
    url_imagem = db.Column(db.String(800), nullable=False)
    valor_diaria= db.Column(db.Float, nullable=False)

    data_ultima_revisao = db.Column(db.Date, nullable=False)
    data_proxima_revisao = db.Column(db.Date, nullable=False)
    data_ultima_inspecao = db.Column(db.Date, nullable=False)

    reservas = db.relationship('Reservas', backref='veiculo_pai', lazy='dynamic')

class FormaPagamento(db.Model):
    __tablename__ = "FormaPagamento"
    id = db.Column(db.Integer, primary_key=True)
    nome=db.Column(db.String(100), unique=True ,nullable=False)

class Reservas(db.Model):
    __tablename__ = "Reservas"
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('Clientes.id'), nullable=False)
    veiculo_id = db.Column(db.Integer, db.ForeignKey('Veiculos.id'), nullable=False)
    forma_pagamento_id = db.Column(db.Integer, db.ForeignKey('FormaPagamento.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Ativa')
    veiculo = db.relationship('Veiculo', foreign_keys=[veiculo_id])

def veiculos_disponiveis(
        data_inicio: date,
        data_fim: date,
        fim_pesquisa: str=None,
        categoria: str=None,
        tipo: str=None,
        lugar: str=None,
        preco_max: str=None,
        filtrar_datas=False
) -> list[Veiculo]:
    hoje = date.today()
    um_ano_atras = hoje - timedelta(days=365)

    #Manutenção e Inspeção obrigatória
    query = Veiculo.query.filter(
        or_(Veiculo.data_proxima_revisao >= hoje, Veiculo.data_proxima_revisao.is_(None)), #Próxima revisão não pode ser inferior à data atual
        or_(Veiculo.data_ultima_inspecao >= um_ano_atras, Veiculo.data_ultima_inspecao.is_(None)) #Próxima inspeção tem de ter menos de 1 ano
    )

    if fim_pesquisa:
        query = query.filter(
            or_(
                Veiculo.marca.ilike(f'%{fim_pesquisa}%'),
        Veiculo.modelo.ilike(f'%{fim_pesquisa}%'),
            )
        )
    if categoria:
        query = query.filter(Veiculo.categoria == categoria)
    if tipo:
        query = query.filter(Veiculo.tipo_veiculo == tipo)
    if lugar:
        query = query.filter(Veiculo.qtd_pessoas >= int(lugar))
    if preco_max:
        try:
            query = query.filter(Veiculo.valor_diaria <= float(preco_max))
        except ValueError:
            pass

    #Exclusão de veículos que já possuam reservas ativas nas datas mencionadas
    if filtrar_datas:
        veiculos_ocupados = db.session.query(Reservas.veiculo_id).filter(
            Reservas.status == 'Ativa',
            Reservas.data_inicio <= data_fim,  # Lógica simplificada e correta de sobreposição
            Reservas.data_fim >= data_inicio
        ).distinct().subquery()

        query = query.filter(Veiculo.id.notin_(veiculos_ocupados))

    #Retorna apenas os veículos disponiveis
    return query.all()

@app.route('/', methods=["GET"])
def index():
    # Captura todos os argumentos do formulário
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    fim_pesquisa = request.args.get('fim_pesquisa', "").strip()
    categoria = request.args.get('categoria')
    tipo = request.args.get('tipo')
    lugar = request.args.get('lugar')
    preco_max = request.args.get('preco_max')

    # Inicializa variáveis padrão
    filtrar_datas = True if (data_inicio_str and data_fim_str) else False
    dias_reserva = None
    hoje = date.today()

    # Tratamento Seguro das Datas (Garante que existem sempre datas válidas para a query)
    try:
        if data_inicio_str and data_fim_str:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()

            # Validação caso o utilizador inverta as datas no formulário
            if data_inicio > data_fim:
                return render_template('index.html', veiculos=[], dias_reserva=None,
                                       erro="A data de início não pode ser posterior à data de fim.")

            # Calcula os dias de reserva se as datas forem válidas
            dias_reserva = (data_fim - data_inicio).days
            if dias_reserva == 0:
                dias_reserva = 1
        else:
            # Se o utilizador não inseriu datas (ex: primeira visita à página), assume Hoje e Amanhã
            data_inicio = hoje
            data_fim = hoje + timedelta(days=1)
            dias_reserva = 1

    except ValueError:
        # Se houver erro de formato nas datas, assume o padrão de segurança
        data_inicio = hoje
        data_fim = hoje + timedelta(days=1)
        dias_reserva = 1

    # UMA ÚNICA CHAMADA À FUNÇÃO DE FILTRAGEM (Com todos os parâmetros integrados)
    frota_filtrada = veiculos_disponiveis(
        data_inicio=data_inicio,
        data_fim=data_fim,
        fim_pesquisa=fim_pesquisa,
        categoria=categoria,
        tipo=tipo,
        lugar=lugar,
        preco_max=preco_max,
        filtrar_datas=filtrar_datas
    )

    # Devolve os resultados e os dias para calcular os preços dinamicamente no HTML
    return render_template('index.html', veiculos=frota_filtrada, dias_reserva=dias_reserva)


#Rota para efetuar reserva e o calculo do valor total
@app.route('/reservar/<int:veiculo_id>', methods=['POST'])
@login_required
def efetuar_reserva(veiculo_id):
    try:
        data_inicio = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date()
        data_fim = datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date()
    except ValueError:
        flash('Formato de data inválido. Por favor, tente de novo.', 'danger')
        return redirect(url_for('index'))

    forma_pagamento_id = request.form.get('forma_pagamento_id')
    cliente_id = current_user.id


    if data_inicio < date.today():
        flash('Não é possível realizar reservas para datas passadas.', 'danger')
        return redirect(url_for('index'))

    if data_fim < data_inicio:
        flash('A data de fim não pode ser anterior à data de inicio.', 'danger')
        return redirect(url_for('index'))

    conflito = Reservas.query.filter(
        Reservas.veiculo_id == veiculo_id,
        Reservas.status == 'Ativa',
        data_inicio <= Reservas.data_fim,
        data_fim >= Reservas.data_inicio
    ).first()

    if conflito:
        flash('Lamentamos, porém, este veículo já se encontra reservado nas datas que indicou.', 'danger')
        return redirect(url_for('index'))

    veiculo = db.get_or_404(Veiculo, veiculo_id)

    #Calculo dos dias e valor total
    dias = (data_fim - data_inicio).days
    if dias == 0:
        dias = 1
    valor_total = dias * veiculo.valor_diaria

    #Gravação de dados
    nova_reserva = Reservas(
        cliente_id = cliente_id,
        veiculo_id = veiculo.id,
        forma_pagamento_id = forma_pagamento_id,
        data_inicio = data_inicio,
        data_fim = data_fim,
        valor_total = valor_total,
        status = 'Ativa',
    )
    try:

        db.session.add(nova_reserva)
        db.session.commit()
        sufixo_dias = "dia" if dias == 1 else "dias"
        flash(f"A sua reserva foi criada com sucesso! Periodo de {dias} {sufixo_dias}. Valor total liquido: {valor_total:.2f}€", "success")
        return redirect(url_for("minhas_reservas"))
    except Exception as e:
        db.session.rollback()
        flash("Ocorreu um erro ao processar a sua reserva na base de dados. Tente novamente.", "danger")
        return redirect(url_for("index"))

#Rota de alteração ou cancelamento de reserva
@app.route('/reserva/editar/<int:reserva_id>', methods=['GET', 'POST'])
@login_required
def editar_reserva(reserva_id):
    reserva = db.get_or_404(Reservas, reserva_id)

    #Garantia de que a reserva é alterada apenas pelo utilizador autorizado
    if reserva.cliente_id != current_user.id:
        flash("Acesso não autorizado", "danger")
        return redirect(url_for('minhas_reservas'))

    if request.method == 'POST':
        acao = request.form.get('acao') #Cancelar ou alterar datas

        if acao == 'cancelar':
            if reserva.status != "Ativa":
                flash("Esta reserva já não se encontra ativa para ser cancelada", "warning")
                return redirect(url_for('minhas_reserva'))
            reserva.status = 'Cancelada'
            db.session.commit()
            flash(f"A reserva {reserva_id} foi cancelada com sucesso.", "success")
            return redirect(url_for('minhas_reservas'))

        elif acao == 'alterar datas':
            if reserva.status != "Ativa":
                flash("Não é possível alterar as datas de uma reserva que não está ativa.", "warning")
                return redirect(url_for('minhas_reservas'))
            try:
                nova_data_inicio = datetime.strptime(request.form['nova_data_inicio'], '%Y-%m-%d').date()
                nova_data_fim = datetime.strptime(request.form['nova_data_fim'], '%Y-%m-%d').date()
            except ValueError:
                flash("Formato de data inválido.", "danger")
                return redirect(url_for('editar_reserva', reserva_id=reserva.id))

            if nova_data_inicio < date.today():
                flash("A nova data de inicio não pode ser no passado.", "danger")
                return redirect(url_for('editar_reserva', reserva_id=reserva.id))
            if nova_data_fim < nova_data_inicio:
                flash("A data de fim deve ser posterior ou igual à data de inicio.", "danger")
                return redirect(url_for('editar_reserva', reserva_id=reserva.id))

            #Verificação de disponibilidade nas novas datas e exclusão da própria reserva atual
            conflito = Reservas.query.filter(
                Reservas.veiculo_id == reserva.veiculo_id,
                Reservas.id != reserva.id,
                Reservas.status == 'Ativa',
                nova_data_inicio <= Reservas.data_fim,
                nova_data_fim >= Reservas.data_inicio
            ).first()

            if conflito:
                flash("O veículo não está disponivel nas novas datas que indicou.", "danger")
                return redirect(url_for('editar_reserva', reserva_id=reserva.id))

            #Atualiza datas e recalcula o valor total
            dias = (nova_data_fim - nova_data_inicio).days
            if dias == 0:
                dias = 1
            reserva.data_inicio = nova_data_inicio
            reserva.data_fim = nova_data_fim
            reserva.valor_total = dias * reserva.veiculo.valor_diaria
            db.session.commit()
            flash(f"Reserva alterada com sucesso! Novo período: {dias} dia(s). Novo total: {reserva.valor_total:.2f}€", "success")
            return redirect(url_for('minhas_reservas'))
    return render_template('editar_reserva.html', reserva=reserva, hoje=date.today().isoformat())





with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)