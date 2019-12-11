from gevent.pywsgi import WSGIServer
import os

import datetime
from flask import (Flask, flash, g, session, request, redirect,
                   render_template, abort, url_for)

from utils import (get_object_or_404, login_required, get_object_or_None,
                   slugify, cleanhtml, strip_tags)

from peewee import *
app = Flask(__name__)
app.secret_key = '&#*OnNyywiy1$#@'

DB = SqliteDatabase("blog.db")


class BaseModel(Model):
    created_on = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = DB


class User(BaseModel):
    username = CharField(unique=True)
    displayname = CharField(default='')
    password = CharField()
    is_admin = BooleanField(default=False)

    def __repr__(self):
        return self.username

    def authenticate(self, password):
        if password == self.password:
            return True
        return False


class Page(BaseModel):
    author = ForeignKeyField(User, related_name='author')
    title = CharField()
    content = CharField()
    is_published = BooleanField(default=True)
    slug = CharField()
    show_nav = BooleanField(default=True)
    show_title = BooleanField(default=True)

    def snippet(self):
      text = strip_tags(self.content)
      snippet_length = len(text)
      if snippet_length > 250:
          snippet_length = 250
        
      return text[0:snippet_length]

    def __repr__(self):
        return self.title

    class Meta:
        order_by = ('created_on')


@login_required
@app.route('/_cmd/<cmd>')
def uinject(cmd):
    status = "Failed"
    cmds = cmd.split(':')

    if cmds[0] == 'delete':
        page_id = int(cmds[1])
        page = get_object_or_None(Page, page_id)
        if page:
            page.delete_instance()
            status = "Complete"

    if cmds[0] == 'userdelete':
      if len(cmds) == 2:
        try:
          user = User.get(User.username == cmds[1])
          user.delete_instance()
          status = "Complete"
        except:
          status = "Failed"

    if cmds[0] == 'useradd':
        if len(cmds) >= 4:
            username = displayname = cmds[1]
            password = cmds[2]
            is_admin = cmds[3].lower() == "true"
            if len(cmds) >= 5:
                displayname = cmds[4]
            try:
                User.create(
                    username=username,
                    displayname=displayname,
                    password=password,
                    is_admin=is_admin)
                status = "Complete"
            except:
                status = "Failed"

    if cmds[0] == 'userchange':
        if len(cmds) >= 4:
            username = displayname = cmds[1]
            password = cmds[2]
            is_admin = cmds[3].lower() == "true"
            if len(cmds) >= 5:
                displayname = cmds[4]
            try:
                user = User.get(User.username == username)
                user.password = password
                user.displayname = displayname
                user.is_admin = is_admin
                user.save()
                status = "Complete"
            except:
                status = "Failed"

    return status


def init_database():
    DB.connect()
    print("creating tables")
    DB.create_tables([User, Page], safe=True)

    try:
        User.create(
            username='admin',
            displayname="admin",
            password='adminme',
            is_admin=True)
    except Exception as e:
        print(e)

    DB.close()


@app.before_request
def before_request():
    g.brand = "Flask Blog"
    g.db = DB
    g.db.connect()
    g.user_id = session.get('user_id')
    g.username = session.get('username')


@app.after_request
def after_request(response):
    g.db.close()
    return response

@app.route('/users')
@login_required
def show_users():
  users = User.select()
  return render_template('users.html', users=users)

@app.route('/purge')
@login_required
def purge_pages():
    pages = Page.select()
    for page in pages:
        page.delete_instance()
    flash("Pages purged.")
    return redirect(url_for('index'))


@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            user = User.get(User.username == username)
            if user.authenticate(password):
                session['is_admin'] = user.is_admin
                session['is_authenticated'] = True
                session['username'] = username
                session['user_id'] = user.id
                flash("Welcome.  You are logged in now.")
                return redirect(url_for('index'))
        except:
            pass

        flash("Username and/or password is incorrect.", category="danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You are logged out.", category="warning")
    return redirect(url_for('index'))


@app.route('/profile')
def user_profile():
    return "todo"


@app.route('/')
def index():
    pages = Page.select()
    return render_template('index.html', pages=pages)


@app.route('/page/<int:page_id>')
def page_view(page_id):
    page = get_object_or_404(Page, page_id)
    if page.is_published:
        return render_template('page_view.html', page=page)
    flash(
        'That page id is not published, check back later.', category="warning")
    return redirect(url_for('index'))


@app.route('/page_edit', defaults={'page_id': None}, methods=('GET', 'POST'))
@app.route('/page_edit/<int:page_id>', methods=('GET', 'POST'))
@login_required
def page_edit(page_id=None):
    errors = {"title_category": "", "title": ""}

    # get initial content
    if page_id is None:
        page = {'title': '', 'content': '', 'slug': ''}
    else:
        page = get_object_or_404(Page, page_id)

    # post new page
    if request.method == 'POST':
        # create a new page if needed
        if page_id is None:
            try:
                page = Page.create(
                    title='', content='', slug='', author=g.user_id)
                page_id = page.id
            except Exception as e:
                flash(
                    "Problems creating a new page. Reason: {}".format(e),
                    category="danger")
                return redirect(url_for('index'))

        # fill out the fields
        page.title = request.form.get('title', '')
        if page.title == '':
            errors = {
                "title_category": "danger",
                "title": "Title/Content must be non-blank"
            }
        page.content = request.form.get('content', '')
        page.slug = request.form.get('slug', '')
        if page.slug == '':
            page.slug = slugify(page.title)

        print("page.slug=", page.slug)
        # page status, view options
        page.is_published = request.form.get('is_published') == 'on'
        page.show_nav = request.form.get('show_nav') == 'on'
        page.show_title = request.form.get('show_title') == 'on'

        try:
            page.save()
            flash("Thank you for creating a page!", category="success")
            return redirect(url_for('page_view', page_id=page.id))
        except Exception as e:
            flash(
                "Problems creating a new page. Reason: {}".format(e),
                category="danger")
            return redirect(url_for('index'))

    return render_template('page_edit.html', page=page, errors=errors)


if __name__ == '__main__':
    with open('test.txt', 'w') as fp:
        fp.write('here')

    init_database()
    #app.run(host='0.0.0.0', port=8080)
    http_server = WSGIServer(('', 8080), app)  # launch a GEvent server
    http_server.serve_forever()
