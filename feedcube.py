from datetime import datetime as dt
from datetime import timedelta
from re import match
from xml.dom.minidom import parseString

from flask import Flask, request, render_template
from flask_mongoalchemy import MongoAlchemy
from requests import get

from forms import addfeed, loginform
from functions import get_fields_from_form, xml_to_dict, format_description, df

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
    date_registered = db.CreatedField()


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
                rss_xml = parseString(rss_req.content)
                rss_items = rss_xml.getElementsByTagName('item')
                new_feed = Feed(feed_name=request.form['feed_name'],
                                feed_location=request.form['feed_location'], last_updated=dt.utcnow())
                new_feed.save()
                for items in list(rss_items):
                    item_details = xml_to_dict(items)
                    feed_content = \
                        FeedContent(for_feed=new_feed, source_author=item_details['dc:creator'],
                                    source_title=item_details['title'], source_location=item_details['guid'],
                                    source_content=format_description(item_details['description']),
                                    source_added=dt.strptime(item_details['pubDate'], df()), feed_added=dt.utcnow())
                    feed_content.save()
        else:
            print('Invalid URL!')
    form_fields = get_fields_from_form(addfeed.AddFeed())
    return render_template('addfeed.html', form=form_fields)


@app.route('/viewfeed/<feed_id>')
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
                    feed_content = \
                        FeedContent(for_feed=feed_obj, source_author=item_details['dc:creator'],
                                    source_title=item_details['title'], source_location=item_details['guid'],
                                    source_content=format_description(item_details['description']),
                                    source_added=dt.strptime(item_details['pubDate'], df()), feed_added=dt.utcnow())
                    feed_content.save()
                else:
                    break
    feed_content_obj = FeedContent.query.filter(FeedContent.for_feed == feed_obj)
    requested_feed_content = feed_content_obj.all()[:10]  # TODO: change to max_links later
    return render_template('viewfeed.html', feed_content=requested_feed_content)


if __name__ == '__main__':
    app.run()
