from datetime import datetime as dt
from datetime import timedelta
from re import match
from xml.dom.minidom import parseString

from flask import Flask, request, render_template, redirect, url_for
from flask_login import LoginManager, login_user, login_required, current_user
from flask_mongoalchemy import MongoAlchemy
from passlib.hash import argon2
from requests import get

from forms import addfeed, loginform, registerform
from functions import get_fields_from_form, xml_to_dict, format_description, df

app = Flask(__name__)
app.config.from_object('config')

app.config['MONGOALCHEMY_DATABASE'] = 'feedcube'
app.config['MONGOALCHEMY_SERVER_AUTH'] = False
app.config['MONGOALCHEMY_PORT'] = 27018

login_manager = LoginManager(app)
UserLoader = login_manager.user_loader

db = MongoAlchemy(app)


class User(db.Document):
    username = db.StringField(max_length=20)
    password = db.StringField(max_length=150)
    email = db.StringField(max_length=40)
    is_active = db.BoolField()
    is_authenticated = db.BoolField()
    is_anonymous = db.BoolField()
    date_registered = db.CreatedField()

    def get_id(self):
        return u'%s' % self.mongo_id


class Feed(db.Document):
    feed_name = db.StringField(max_length=80)
    feed_location = db.StringField()
    date_added = db.CreatedField()
    last_updated = db.DateTimeField()


class FeedContent(db.Document):
    for_feed = db.DocumentField(Feed)
    source_author = db.StringField(max_length=40)
    source_title = db.StringField(max_length=120)
    source_location = db.StringField()
    source_content = db.StringField()
    source_added = db.DateTimeField()
    feed_added = db.DateTimeField()


class AssignedFeed(db.Document):
    assigned_to = db.DocumentField(User)
    for_feed = db.DocumentField(Feed)
    display_order = db.IntField(min_value=1)
    max_links = db.IntField(min_value=1, max_value=40)
    date_assigned = db.CreatedField()


@UserLoader
def load_user(user_id):
    return User.query.filter(User.mongo_id == user_id).first()


@app.route('/')
def home():
    return "This is the homepage"


@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'GET':
        form_fields = get_fields_from_form(registerform.Register())
        return render_template('register.html', form=form_fields)
    elif request.method == 'POST':
        register_data = request.form
        if not User.query.filter(User.username == register_data['username']).first():
            new_user = User(
                username=register_data['username'],
                password=argon2.hash(register_data['password']),
                email=register_data['email_address'],
                is_active=True,
                is_authenticated=False,
                is_anonymous=False,
                date_registered=dt.utcnow()
            )
            new_user.save()
            return redirect('/login')
        else:
            return redirect('/register')


@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'GET':
        form_fields = get_fields_from_form(loginform.Login())
        return render_template('login.html', form=form_fields)
    elif request.method == 'POST':
        login_data = request.form
        login_request = User.query.filter(User.username == login_data['username'])
        if argon2.verify(login_data['password'], login_request.one().password):
            user = login_request.one()
            login_request.set(User.is_authenticated, True).execute()
            login_user(user)
            return redirect(url_for('dashboard'))
    else:
        return 'Something went wrong!'


@app.route('/addfeed', methods=('GET', 'POST'))
@login_required
def add_feed():
    if request.method == 'POST':
        if match('https?://(?:[\w-]+\.)+(?:[a-zA-Z]{2,6})/.+', request.form['feed_location']):
            if not Feed.query.filter(Feed.feed_location == request.form['feed_location']).all():
                rss_req = get(request.form['feed_location'])
                if rss_req.status_code == 200:
                    rss_xml = parseString(rss_req.content)
                    rss_items = rss_xml.getElementsByTagName('item')
                    new_feed = Feed(
                        feed_name=request.form['feed_name'],
                        feed_location=request.form['feed_location'],
                        last_updated=dt.utcnow()
                    )
                    new_feed.save()
                    af_query = AssignedFeed.query.filter(AssignedFeed.assigned_to.mongo_id == current_user.mongo_id)
                    assign_feed = AssignedFeed(
                        assigned_to=User.query.filter(User.mongo_id == current_user.mongo_id).one(),
                        for_feed=new_feed,
                        display_order=len(af_query.all()) + 1,
                        max_links=10,
                        date_assigned=dt.utcnow()
                    )
                    assign_feed.save()
                    for items in list(rss_items):
                        item_details = xml_to_dict(items)
                        feed_content = FeedContent(
                            for_feed=new_feed,
                            source_author=item_details['dc:creator'],
                            source_title=item_details['title'],
                            source_location=item_details['guid'],
                            source_content=format_description(item_details['description']),
                            source_added=dt.strptime(item_details['pubDate'], df()),
                            feed_added=dt.utcnow()
                        )
                        feed_content.save()
        else:
            print('Invalid URL!')
    form_fields = get_fields_from_form(addfeed.AddFeed())
    return render_template('addfeed.html', form=form_fields)


@app.route('/viewfeed/<feed_id>')
@login_required
def view_feed(feed_id):
    feed_obj = Feed.query.filter(Feed.mongo_id == feed_id).one()
    if feed_obj.last_updated + timedelta(minutes=15) < dt.utcnow():
        latest_entry = FeedContent.query.descending('source_added').first()
        rss_req = get(feed_obj.feed_location)
        if rss_req.status_code == 200:
            rss_xml = parseString(rss_req.content)
            rss_items = rss_xml.getElementsByTagName('item')
            for items in list(rss_items):
                item_details = xml_to_dict(items)
                if dt.strptime(item_details['pubDate'], df()) > latest_entry.source_added:
                    feed_content = FeedContent(
                        for_feed=feed_obj,
                        source_author=item_details['dc:creator'],
                        source_title=item_details['title'],
                        source_location=item_details['guid'],
                        source_content=format_description(item_details['description']),
                        source_added=dt.strptime(item_details['pubDate'], df()),
                        feed_added=dt.utcnow()
                    )
                    feed_content.save()
                else:
                    break
    feed_content_obj = FeedContent.query.filter(FeedContent.for_feed.mongo_id == feed_id)
    num_max_links = AssignedFeed.query.filter(
        AssignedFeed.assigned_to.mongo_id == current_user.mongo_id
    ).first().max_links
    requested_feed_content = feed_content_obj.descending('source_added').all()[:int(num_max_links)]
    return render_template('viewfeed.html', feed_content=requested_feed_content)


@app.route('/allfeeds')
def all_feeds():
    global_feeds = Feed.query.descending('date_added').all()
    return render_template('allfeeds.html', feeds=global_feeds)


@app.route('/dashboard')
@login_required
def dashboard():
    all_feeds = AssignedFeed.query.ascending('display_order').all()
    return render_template('dashboard.html', feeds=all_feeds)


if __name__ == '__main__':
    app.run()
