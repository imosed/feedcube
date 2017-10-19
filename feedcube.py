from flask import Flask, request, render_template, url_for
from flask_mongoalchemy import MongoAlchemy
from forms import addfeed, loginform
from functions import get_fields_from_form
from xml.dom.minidom import parseString
from datetime import datetime
from requests import get
from re import match


app = Flask(__name__)
app.config.from_object('config')


app.config['MONGOALCHEMY_DATABASE'] = 'feedcube'
app.config['MONGOALCHEMY_SERVER_AUTH'] = False
app.config['MONGOALCHEMY_PORT'] = 27018


db = MongoAlchemy(app)


class User(db.Document):
    username = db.StringField(max_length=20)
    password = db.StringField(max_length=20)
    email = db.StringField(max_length=40)
    date_registered = db.DateTimeField(default=datetime.utcnow())


class Feed(db.Document):
    feed_name = db.StringField(max_length=80)
    feed_location = db.StringField()
    feed_content = db.ListField(db.TupleField(db.StringField(), db.StringField()))
    date_added = db.DateTimeField(default=datetime.utcnow())


class AssignedFeed(db.Document):
    assigned_to = db.DocumentField(User)
    for_feed = db.DocumentField(Feed)
    max_links = db.IntField(min_value=1, max_value=40)


@app.route('/')
def home():
    return "This is the homepage"


@app.route('/login', methods=('GET', 'POST'))
def login():
    form_fields = get_fields_from_form(loginform.Login())
    return render_template('login.html', form=form_fields)


@app.route('/addfeed', methods=('GET', 'POST'))
def add_feed():
    if request.method == 'POST':
        if match('https?://(?:[\w-]+\.)+(?:[a-zA-Z]{2,6})/.+', request.form['feed_location']):
            rss_req = get(request.form['feed_location'])
            if rss_req.status_code == 200:
                feed_content = []
                rss_xml = parseString(rss_req.content)
                rss_items = rss_xml.getElementsByTagName('item')
                for items in list(rss_items)[:10]:
                    feed_content += [(x.childNodes[0].data, y.childNodes[0].data)
                                    for x, y in zip(items.getElementsByTagName('title'), items.getElementsByTagName('guid'))]
                new_feed = Feed(feed_name=request.form['feed_name'],
                                feed_location=request.form['feed_location'], feed_content=feed_content)
                new_feed.save()
        else:
            print('Invalid URL!')
    form_fields = get_fields_from_form(addfeed.AddFeed())
    return render_template('addfeed.html', form=form_fields)


@app.route('/viewfeed/<feed_id>')
def view_feed(feed_id):
    requested_feed = Feed.query.filter(Feed.mongo_id == feed_id).one()
    return render_template('viewfeed.html', feed=requested_feed)


if __name__ == '__main__':
    app.run()
