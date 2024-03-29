from flask import jsonify, abort, g, request
from flask_httpauth import HTTPBasicAuth
from app import app, db, models, sched, mqtt

auth = HTTPBasicAuth()


def model_to_dict(model):
    dict = {}
    for x in model:
        x = x.__dict__
        del x['_sa_instance_state']
        dict[x['id']] = x
    return dict

@app.route('/')
def hello_word():
    return "Hello Word"

##USERS##

@app.route('/Data/api/v1.0/Users')
@auth.login_required
def get_users():
    allUsers = models.User.query.all()
    return jsonify(model_to_dict(allUsers))


@app.route('/Data/api/v1.0/User/<id>')
@auth.login_required
def get_user(id):
    user = models.User.query.filter_by(email=id).first()
    if not user:
        user = models.User.query.filter_by(nickName=id).first()
    if not user:
        abort(500)
    user = user.__dict__
    del user['_sa_instance_state']
    return jsonify(user)


@app.route('/Data/api/v1.0/User', methods=['POST'])
@auth.login_required
def add_user():
    if g.user.nickName != 'admin': abort(401)
    nickName = request.json['nickName']
    email = request.json['email']
    password = request.json['password']
    if models.User.query.filter_by(nickName=nickName).first() or models.User.query.filter_by(email=email).first():
        abort(500)
    nwUser = models.User(nickName=nickName, email=email)
    nwUser.mods = []
    nwUser.hash_password(password)
    db.session.add(nwUser)
    db.session.commit()
    return "OK", 200


@app.route('/Data/api/v1.0/User', methods=['PUT'])
@auth.login_required
def ch_user():
    nickName = None
    email = None
    password = None
    userNick = None
    userEmail = None
    if 'nickName' in request.json:
        nickName = request.json['nickName']
        userNick = models.User.query.filter_by(nickName=nickName).first()
    if 'email' in request.json:
        email = request.json['email']
        userEmail = models.User.query.filter_by(email=email).first()
    if 'password' in request.json: password = request.json['password']
    if userEmail or userEmail:
        abort(500)
    g.user.ch(nickName=nickName, email=email, password=password)
    db.session.add(g.user)
    db.session.commit()
    return "OK", 200


@app.route('/Data/api/v1.0/User', methods=['DELETE'])
@auth.login_required
def del_user():
    db.session.delete(g.user)
    db.session.commit()
    return "OK", 200


@app.route('/Data/api/v1.0/User/<idUser>/mod', methods=['POST'])
@auth.login_required
def add_mod_to_user(idUser):
    user = models.User.query.filter_by(id=idUser).first()
    idMod = request.json['idMod']
    if models.Mods.query.filter_by(id=idMod).first() is None or user is None :
        abort(500)
    if idMod not in user.mods:
        user.mods.append(idMod)
        db.session.add(user)
        db.session.commit()
        return "OK", 200
    abort(400)


@app.route('/Data/api/v1.0/User/mod', methods=['DELETE'])
@auth.login_required
def dell_mod_to_user():
    idMod = request.json['idMod']
    if models.Mods.query.filter_by(id=idMod).first() is None: abort(500)
    try:
        g.user.mods.remove(idMod)
        db.session.add(g.user)
        db.session.commit()
    except ValueError:
        abort(401)
    return "OK", 200


##MODULOS##
@app.route('/Data/api/v1.0/Mods')
@auth.login_required
def get_mods():
    return jsonify(model_to_dict(models.Mods.query.all()))


@app.route('/Data/api/v1.0/Mod/<id>')
@auth.login_required
def get_mod(id):
    if models.Mods.query.filter_by(id=id).first() is None: abort(500)
    return jsonify(model_to_dict(models.Mods.query.filter_by(id=id)))


@app.route('/Data/api/v1.0/Mod', methods=['POST'])
@auth.login_required
def add_mod():
    if g.user.nickName != 'admin':
        abort(401)
    try:
        uniqueID = request.json['uniqueID']
    except KeyError:
        abort(500)
    db.session.add(models.Mods(uniqueID=uniqueID, new=True, state=0))
    db.session.commit()
    return "OK", 200

@app.route('/Data/api/v1.0/Mod', methods=['PUT'])
@auth.login_required
def change_mod():
    try:
        uniqueID = request.json['uniqueID']
        newState = request.json['newState']
    except KeyError:
        abort(500)
    mod = models.Mods.query.filter_by(uniqueID=uniqueID).first()
    if mod is None or mod.id not in g.user.mods:
        abort(401)
    mod.execute_change(newState)
    return "OK", 200

@app.route('/Data/api/v1.0/UMod/<uniqueID>/<newState>', methods=['PUT'])
def update_mod(uniqueID, newState):
    mod = models.Mods.query.filter_by(uniqueID=uniqueID).first()
    if mod is None:
        abort(401)
    mod.state = newState
    db.session.commit()
    return "OK", 200


@app.route('/Data/api/v1.0/Mod', methods=['DELETE'])
@auth.login_required
def del_mod():
    if g.user.nickName != 'admin':
        abort(401)
    if('idMod' in request.json):
        idMod = request.json['idMod']
        mod = models.Mods.query.filter_by(id=idMod).first()
    if('uniqueId' in request.json):
        uniqueId = request.json['uniqueId']
        mod = models.Mods.query.filter_by(uniqueID=idMod).first()
    if mod is None: abort(500)
    for user in models.User.query.all():
        if idMod in user.mods:
            user.mods.remove(idMod)
            db.session.add(user)
            db.session.commit()
    db.session.delete(mod)
    db.session.commit()
    return "OK", 200


##TASKS##
@app.route('/Data/api/v1.0/Mod/<idMod>/task')
@auth.login_required
def get_task_of(idMod):
    if models.Mods.query.filter_by(id=idMod).first() is None: abort(500)
    tasks=models.Task.query.filter_by(idMod=idMod).all()
    return jsonify(model_to_dict(tasks))


@app.route('/Data/api/v1.0/Mod/<idMod>/task', methods=['POST'])
@auth.login_required
def add_task_to(idMod):
    mod = models.Mods.query.filter_by(id=idMod).first()
    task = models.Task()
    if mod is None: abort(500)
    if mod.id not in g.user.mods: abort(401)
    task.idMod = idMod
    task.hour = request.json['hour']
    task.minute = request.json['minute']
    task.wDay = request.json['wDay']
    task.newState = request.json['newState']
    task.save(mod)
    db.session.add(task)
    db.session.commit()
    return "OK", 200


@app.route('/Data/api/v1.0/Mod/<idMod>/task', methods=['DELETE'])
@auth.login_required
def del_task_of(idMod):
    mod = models.Mods.query.filter_by(id=idMod).firts()
    task = models.Task().query.filter_by(id=request.json('id'))
    if mod is None: abort(500)
    if mod.id not in g.user.mods: abort(401)
    task.delete()
    db.session.delete(task)
    db.session.commit()
    return "OK", 200


@auth.verify_password
def verify_password(id, password):
    user = models.User.query.filter_by(email=id).first()
    if not user:
        user = models.User.query.filter_by(nickName=id).first()
    if not user or not user.verify_password(password):
        return False
    g.user = user
    return True
