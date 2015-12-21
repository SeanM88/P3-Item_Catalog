from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, send_from_directory
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from db_models import Base, Item, Category, User

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

import os
import httplib2
import json
from flask import make_response
import requests
from werkzeug import secure_filename

GOOGLE_CLIENT_ID = json.loads( open('google_client_secret.json', 'r').read() )['web']['client_id']
APPLICATION_NAME = "Catalog App"
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['jpg', 'gif', 'png', 'pdf', 'txt', 'jpeg'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#Connect to Database and create database session
engine = create_engine('sqlite:///catalogapp.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
def indexHandler():
    is_user = checkUserStatus(login_session)
    categories = session.query(Category).order_by(asc(Category.name)).all()
    items = session.query(Item).order_by(desc(Item.created_on)).limit(10)
    return render_template('home_screen.html', items=items, cats=categories, user=is_user)

# ----------------------------------
# Item Handlers
# ----------------------------------

@app.route('/items/')
def itemListHandler():
    is_user = checkUserStatus(login_session)
    items = session.query(Item).order_by(desc(Item.created_on)).all()
    return render_template('item_list.html', items=items, user=is_user)

@app.route('/item/new/', methods=['GET','POST'])
def newItemHandler():
    is_user = checkUserStatus(login_session)
    if not is_user:
        return redirect('/login')
    if 'POST' == request.method:
        newItem = Item(
            name           = request.form['item-name'],
            description    = request.form['item-description'],
            price          = request.form['item-price'],
            category_id    = request.form['category-select'],
            category_name  = getCatNameByID(request.form['category-select']),
            image          = upload_file('item-image'),
            user_id        = is_user.id
        )
        session.add(newItem)
        session.commit()
        return redirect(url_for('indexHandler'))
    else:
        cats = session.query(Category).order_by(asc(Category.name))
        return render_template('edit_item.html', cats=cats)

@app.route('/item/<int:item_id>/')
def viewItemHandler(item_id):
    is_user = checkUserStatus(login_session)
    item = getItemByID(item_id)
    return render_template('single_item.html', item=item, user=is_user)
    
@app.route('/item/<int:item_id>/edit', methods=['GET','POST'])
def editItemHandler(item_id):
    editItem = getItemByID(item_id)
    if editItem.user_id != getUserID(login_session['email']):
        return redirect('/login')
    if 'POST' == request.method:
        editItem.name = request.form['item-name']
        editItem.description = request.form['item-description']
        editItem.price = request.form['item-price']
        editItem.category_id = request.form['category-select']
        editItem.category_name = getCatNameByID(request.form['category-select'])
        if request.files['item-image']:
            editItem.image = upload_file('item-image')
        session.add(editItem)
        session.commit()
        return redirect(url_for('viewItemHandler', item_id=item_id))
    else:
        cats = session.query(Category).order_by(asc(Category.name))
        return render_template('edit_item.html', cats=cats, editItem = editItem)
    
@app.route('/item/<int:item_id>/delete', methods=['GET','POST'])
def deleteItemHandler(item_id):
    deleteItem = getItemByID(item_id)
    if deleteItem.user_id != getUserID(login_session['email']):
        return redirect('/login')
    if 'POST' == request.method:
        session.delete(deleteItem)
        flash('%s Successfully Deleted' % deleteItem.name)
        session.commit()
        return redirect(url_for('indexHandler'))
    else:
        return render_template('delete_item.html', deleteItem = deleteItem)

# ----------------------------------
# Category Handlers
# ----------------------------------

@app.route('/categories/')
def categoryListHandler():
    is_user = checkUserStatus(login_session)
    cats = session.query(Category).order_by(asc(Category.name))
    return render_template('category_list.html', cats=cats, user=is_user)

@app.route('/category/<int:cat_id>/items')
def itemsByCategoryHandler(cat_id):
    is_user = checkUserStatus(login_session)
    category = getCatByID(cat_id)
    items = session.query(Item).filter_by(category_id = cat_id).order_by(desc(Item.created_on))
    return render_template('category_archive.html', items=items, category=category, user=is_user)

@app.route('/category/new/', methods=['GET','POST'])
def newCategoryHandler():
    is_user = checkUserStatus(login_session)
    if not is_user:
        return redirect('/login')
    if 'POST' == request.method:
        newCategory = Category(name = request.form['category-name'], description = request.form['category-description'], user_id = is_user.id)
        session.add(newCategory)
        session.commit()
        return redirect(url_for('indexHandler'))
    else:
        return render_template('edit_category.html')
    
@app.route('/category/<int:cat_id>/')
def viewCategoryHandler(cat_id):
    is_user = checkUserStatus(login_session)
    category = getCatByID(cat_id)
    return render_template('single_category.html', category=category, user=is_user)

@app.route('/category/<int:cat_id>/edit', methods=['GET','POST'])
def editCategoryHandler(cat_id):
    editCategory = getCatByID(cat_id)
    if editCategory.user_id != getUserID(login_session['email']):
        return redirect('/login')
    if 'POST' == request.method:
        editCategory.name = request.form['category-name']
        editCategory.description = request.form['category-description']
        session.add(editCategory)
        session.commit()
        return redirect(url_for('viewCategoryHandler', cat_id=cat_id))
    else:
        return render_template('edit_category.html', editCategory = editCategory)

@app.route('/category/<int:cat_id>/delete', methods=['GET','POST'])
def deleteCategoryHandler(cat_id):
    deleteCategory = getCatByID(cat_id)
    if deleteCategory.user_id != getUserID(login_session['email']):
        return redirect('/login')
    if 'POST' == request.method:
        session.delete(deleteCategory)
        flash('%s Successfully Deleted' % deleteCategory.name)
        session.commit()
        return redirect(url_for('indexHandler'))
    else:
        return render_template('delete_category.html', deleteCategory = deleteCategory)

# ----------------------------------
# JSON Endpoints
# ----------------------------------

@app.route('/items/JSON')
def allItemsJSON():
    items = session.query(Item).all()
    return jsonify(items = [item.serialize for item in items])

# ----------------------------------
# Login Handlers
# ----------------------------------

@app.route('/login')
def loginHandler():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/logout')
def logoutHandler():
    if 'provider' in login_session:
        if 'google' == login_session['provider']:
            gdisconnect()
        if 'facebook' == login_session['provider']:
            fbdisconnect()
        del login_session['provider']
        return redirect(url_for('indexHandler'))
    else:
        return redirect(url_for('indexHandler'))
        
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    # Obtain authorization code
    code = request.data
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('google_client_secret.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != GOOGLE_CLIENT_ID:
        response = make_response(json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()
    
    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    
    user_id = getUserID(login_session['email'])
    if not user_id:
        login_session['user_id'] = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "GConnect function finished!"
    return output
        
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('facebook_client_secret.json', 'r').read())['web']['app_id']
    app_secret = json.loads(open('facebook_client_secret.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.5/me"
    # strip expire tag from access token
    token = result.split("&")[0]


    url = 'https://graph.facebook.com/v2.5/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['facebook_id'] = data["id"]
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]

    # The token must be stored in the login_session in order to properly logout, let's strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.5/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output

# ----------------------------------
# Disconnect functions
# ----------------------------------
def gdisconnect():
    access_token = login_session.get('credentials')
    if access_token is None:
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    del login_session['facebook_id']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    return "you have been logged out"

# ----------------------------------
# Functional routing
# ----------------------------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

# ----------------------------------
# Utility Functions
# ----------------------------------

def getItemByID(item_id):
    item = session.query(Item).filter_by(id = item_id).one()
    return item

def getCatByID(cat_id):
    category = session.query(Category).filter_by(id = cat_id).one()
    return category

def getCatNameByID(cat_id):
    category = session.query(Category).filter_by(id = cat_id).one()
    return category.name

def createUser(login_session):
    newUser = User(name = login_session['username'], email = login_session['email'], picture = login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email = login_session['email']).one()
    return user.id

def getUserInfo(user_id):
    user = session.query(User).filter_by(id = user_id).one()
    return user

def getUserID(email):
    try:
        user = session.query(User).filter_by(email = email).one()
        return user.id
    except:
        return None
    
def checkUserStatus(login_session):
    if 'username' in login_session:
        user_id = getUserID(login_session['email'])
        return getUserInfo(user_id)
    else:
        return None
    
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def upload_file(input_name):
    file = request.files[input_name]
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return request.url_root + filepath
    return


# ----------------------------------
# App Config
# ----------------------------------

if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 8000)