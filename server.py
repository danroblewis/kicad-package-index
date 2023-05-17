from flask import Flask, jsonify, request, render_template, send_from_directory
import json
import shutil
import datetime
import os
import re


# This is the worst possible implementation of a registry server. 


app = Flask(__name__,
    		static_url_path='/public', 
            template_folder='templates',
            static_folder='public',)

app.config.update(
    TEMPLATES_AUTO_RELOAD = True
)


def get_registry():
    registry_json_path = "./registry.json"
    with open(registry_json_path) as f:
        return json.load(f)


def get_users():
    users_path = "./users.json"
    with open(users_path) as f:
        return json.load(f)


CDN_PREFIX = 'http://kihub.info'
if os.path.exists('cdn_prefix'):
    with open('cdn_prefix') as f:
    	CDN_PREFIX = f.read().strip()


def reg_get_package(packagename):
    pkg = None
    registry_packages = get_registry()
    for package in registry_packages:
    	if package['name'].lower() == packagename.lower():
    		pkg = package
    if pkg is None:
    	return None
    for release in pkg['releases']:
    	if release['artifact_url'][0] == '/':
    		release['artifact_url'] = CDN_PREFIX + release['artifact_url']
    return pkg


def reg_get_user_by_token(token):
    users = get_users()
    for user in users:
    	if user['token'] == token:
    		return user
    return None


def validate_package_schema(package):
    required_package_fields = set(['homepage', 'owner', 'name'])
    required_release_fields = set(['artifact_url', 'author', 'dependencies', 'version'])
    missing_package_keys = required_package_fields - set(package.keys())
    if missing_package_keys:
    	return f"package missing keys: {', '.join(missing_package_keys)}"
    for release in package['releases']:
    	missing_release_fields = required_release_fields - set(release.keys())
    	if missing_release_fields:
    		return f"release missing keys: {', '.join(missing_release_keys)}"

@app.route("/package/<packagename>", methods=['GET'])
def get_package(packagename):
    p = reg_get_package(packagename)
    if p:
    	return p
    return "Package no found by that name", 404


@app.route("/package/<packagename>", methods=['PUT'])
def write_package(packagename):
    registry_packages = get_registry()

    package = reg_get_package(packagename)
    token = request.headers.get("Authorization")
    user = reg_get_user_by_token(token)
    new_pkg = request.json
    new_pkg['name'] = packagename

    # validation_error = validate_package_schema(new_pkg)
    # if validation_error:
    # 	return validation_error, 400

    # if a package by that name exists, test authentication
    if package is not None:
    	print(package)
    	if user is None:
    		# if a package exists, then a user must exist for it
    		return f"No user with token {token} was found", 401
    	elif package['owner'] != user['name']:
    		return f"You are not the owner of this package, {package['owner']} is", 401

    # if a package by that doesn't exist, ensure the user exists
    users = get_users()
    if package is None:
    	# if this is a new package, ensure a user exists
    	if user is None:
    		u = { "name": new_pkg['owner'], "token": token }
    		users.append(u)
    		with open('users.json', 'w') as f:
    			f.write(json.dumps(users))

    # remove all other packages by that name, append the new one
    registry_packages = [ p for p in registry_packages if p['name'] != new_pkg['name'] ]

    # add new package to list
    registry_packages.append(request.json)

    # write file
    shutil.copyfile("registry.json", f"registry.json.{datetime.datetime.now().timestamp()}")
    s = json.dumps(registry_packages)
    with open('registry.json', 'w') as f:
    	f.write(s)

    return "Success"


@app.route("/packages", methods=['GET'])
def search_packages():
    registry_packages = get_registry()
    term = request.args.get('term')
    if term is None:
        term = ''
    term = term.lower().replace(' ', '.*')
    ps = []
    for p in registry_packages:
        if re.match('.*'+term+'.*', p['name'].lower()):
            ps.append(p)
    return jsonify(ps)


@app.route("/package/<packagename>/release/<version>", methods=['PUT'])
def write_artifact(packagename, version):
    dirpath = f"public/{packagename}/{version}"
    os.makedirs(dirpath, exist_ok=True)
    f = request.files['file']
    path = f"{dirpath}/{f.filename}"
    if '..' in path:
    	return "nah", 403
    #if os.path.exists(path):
   # 	return "file already exists", 403
    with open(path, 'wb') as fp:
    	fp.write(f.read())
    return f"/{path}"


@app.route("/")
def index():
    return send_from_directory('templates', 'index.html')

import datetime
t = datetime.datetime.now()
@app.route("/time")
def tt():
    return str(t)



