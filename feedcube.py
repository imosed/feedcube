from datetime import datetime as dt
from datetime import timedelta
from re import match
from xml.dom.minidom import parseString

from flask import Flask, request, render_template, redirect, url_for
from flask_login import LoginManager, login_user, login_required, current_user
from flask_mongoalchemy import MongoAlchemy
from passlib.hash import argon2
from requests import get

from forms import addfeed, loginform, registerform, editfeed
from functions import get_fields_from_form, xml_to_dict, format_description, df, rescue_value, gen_title

app = Flask(__name__)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
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
        if not User.query.filter(User.username == register_data.get('username')).first():
            new_user = User(
                username=register_data.get('username'),
                password=argon2.hash(register_data.get('password')),
                email=register_data.get('email_address'),
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
        login_request = User.query.filter(User.username == login_data.get('username'))
        if argon2.verify(login_data.get('password'), login_request.one().password):
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
        if match('https?://(?:[\w-]+\.)+(?:[a-zA-Z]{2,6})/.+', request.form.get('feed_location')):
            if not Feed.query.filter(Feed.feed_location == request.form.get('feed_location')).all():
                print('Making request')
                rss_req = get(request.form.get('feed_location'))
                if rss_req.status_code == 200:
                    rss_xml = parseString(rss_req.content)
                    rss_items = rss_xml.getElementsByTagName('item') + rss_xml.getElementsByTagName('entry')
                    new_feed = Feed(
                        feed_name=request.form.get('feed_name'),
                        feed_location=request.form.get('feed_location'),
                        last_updated=dt.utcnow()
                    )
                    new_feed.save()
                    af_query = AssignedFeed.query.filter(AssignedFeed.assigned_to.mongo_id == current_user.mongo_id)
                    new_assigned_feed = AssignedFeed(
                        assigned_to=User.query.filter(User.mongo_id == current_user.mongo_id).one(),
                        for_feed=new_feed,
                        display_order=len(af_query.all()) + 1,
                        max_links=10,
                        date_assigned=dt.utcnow()
                    )
                    new_assigned_feed.save()
                    latest_feed_content = FeedContent.query.descending('source_added').first()
                    if latest_feed_content:
                        prev_pub_date = latest_feed_content.source_added
                    else:
                        prev_pub_date = 'Thu, 01 Jan 1970 00:00:00 GMT'
                    for items in list(rss_items):
                        item_details = xml_to_dict(items)
                        feed_content = FeedContent(
                            for_feed=new_feed,
                            source_author=rescue_value(
                                item_details.get('dc:creator'),
                                item_details.get('author'),
                                request.form.get('feed_name')
                            ),
                            source_title=rescue_value(
                                item_details.get('title'),
                                gen_title(format_description(item_details.get('description'))),
                                gen_title(format_description(item_details.get('content')))
                            ),
                            source_location=rescue_value(
                                item_details.get('guid'),
                                item_details.get('href'),
                                request.host
                            ),
                            source_content=rescue_value(
                                format_description(item_details.get('description')),
                                format_description(item_details.get('content'))
                            ),
                            source_added=df(rescue_value(
                                item_details.get('pubDate'),
                                item_details.get('updated'),
                                prev_pub_date)
                            ),
                            feed_added=dt.utcnow()
                        )
                        feed_content.save()
                        if 'pubDate' in item_details or 'updated' in item_details:
                            prev_pub_date = rescue_value(item_details.get('pubDate'), item_details.get('updated'))
                        else:
                            continue
                    return redirect('/dashboard')
            else:
                feed_to_add = Feed.query.filter(Feed.feed_location == request.form.get('feed_location'))
                af_query = AssignedFeed.query.filter(AssignedFeed.assigned_to.mongo_id == current_user.mongo_id)
                assign_feed = AssignedFeed(
                    assigned_to=User.query.filter(User.mongo_id == current_user.mongo_id).one(),
                    for_feed=feed_to_add.one(),
                    display_order=len(af_query.all()) + 1,
                    max_links=10,
                    date_assigned=dt.utcnow()
                )
                assign_feed.save()
                return redirect('/dashboard')
        else:
            return 'Invalid URL!'
    form_fields = get_fields_from_form(addfeed.AddFeed())
    return render_template('addfeed.html', form=form_fields)


@app.route('/viewfeed/<feed_id>')
@login_required
def view_feed(feed_id):
    feed_query = Feed.query.filter(Feed.mongo_id == feed_id)
    feed_obj = feed_query.one()
    if feed_obj.last_updated + timedelta(minutes=15) < dt.utcnow():
        feed_query.set(Feed.last_updated, dt.utcnow()).execute()
        if FeedContent.query.all():
            latest_entry = FeedContent.query.descending('source_added').first().source_added
        else:
            latest_entry = dt(1970, 1, 1, 0, 0, 0)
        rss_req = get(feed_obj.feed_location)
        if rss_req.status_code == 200:
            rss_xml = parseString(rss_req.content)
            rss_items = rss_xml.getElementsByTagName('item') + rss_xml.getElementsByTagName('entry')
            for items in list(rss_items):
                item_details = xml_to_dict(items)
                if df(rescue_value(item_details.get('pubDate'), item_details.get('updated'))) > latest_entry:
                    feed_content = FeedContent(
                        for_feed=feed_obj,
                        source_author=rescue_value(
                            item_details.get('dc:creator'),
                            item_details.get('author'),
                            feed_obj.feed_name
                        ),
                        source_title=rescue_value(
                            item_details.get('title'),
                            gen_title(format_description(item_details.get('description'))),
                            gen_title(format_description(item_details.get('content')))
                        ),
                        source_location=rescue_value(
                            item_details.get('guid'),
                            item_details.get('href'),
                            request.host
                        ),
                        source_content=rescue_value(
                            format_description(item_details.get('description')),
                            format_description(item_details.get('content'))
                        ),
                        source_added=df(rescue_value(
                            item_details.get('pubDate'),
                            item_details.get('updated'))
                        ),
                        feed_added=dt.utcnow()
                    )
                    feed_content.save()
                else:
                    break
    feed_content_obj = FeedContent.query.filter(FeedContent.for_feed.mongo_id == feed_id)
    assigned_feed_query = AssignedFeed.query.filter(
        AssignedFeed.for_feed.mongo_id == feed_id
    ).filter(
        AssignedFeed.assigned_to.mongo_id == current_user.mongo_id
    ).first()
    if assigned_feed_query:
        num_max_links = assigned_feed_query.max_links
    else:
        num_max_links = 10
    requested_feed_content = feed_content_obj.descending('source_added').all()[:int(num_max_links)]
    if request.is_xhr:
        content_list = ''
        for link in requested_feed_content:
            content_list += '<li><a href="%s" target="_blank">%s</a></li>' % (link.source_location, link.source_title)
        return '<ul class="rss-link-list">' + content_list + '</ul>'
    else:
        return render_template('viewfeed.html', feed=feed_obj, feed_content=requested_feed_content)


@app.route('/allfeeds')
def all_feeds():
    global_feeds = Feed.query.descending('date_added').all()
    user_assigned_feeds = AssignedFeed.query.filter(AssignedFeed.assigned_to.mongo_id == current_user.mongo_id).all()
    user_assigned_feed_ids = [x.for_feed.mongo_id for x in user_assigned_feeds]
    return render_template('allfeeds.html', feeds=global_feeds, assigned_feed_ids=user_assigned_feed_ids)


@app.route('/dashboard')
@login_required
def dashboard():
    all_feeds = AssignedFeed.query.ascending('display_order').all()
    return render_template('dashboard.html', feeds=all_feeds)


@app.route('/editfeed/<feed_id>', methods=('GET', 'POST'))
@login_required
def edit_feed(feed_id):
    queried_feed = AssignedFeed.query.filter(AssignedFeed.for_feed.mongo_id == feed_id)
    if request.method == 'GET':
        max_links = queried_feed.first().max_links
        display_order = queried_feed.first().display_order
        assigned = bool(queried_feed.all())
        items = zip(get_fields_from_form(editfeed.EditFeed()), [max_links, display_order, assigned])
        return render_template('editfeed.html', form=items)
    elif request.method == 'POST':
        form_data = request.form
        if form_data.get('max_links').isdigit() and form_data.get('display_order').isdigit():
            feeds_to_change = queried_feed.filter(AssignedFeed.display_order >= form_data.get('display_order')).all()
            for feed in feeds_to_change:
                ftc_query = AssignedFeed.query.filter(AssignedFeed.mongo_id == feed.mongo_id)
                ftc_query.set(AssignedFeed.display_order, ftc_query.display_order + 1).execute()
            queried_feed.set(AssignedFeed.max_links, int(form_data.get('max_links'))).execute()
            queried_feed.set(AssignedFeed.display_order, int(form_data.get('display_order'))).execute()
        else:
            return redirect('/editfeed/' + feed_id)
        if not form_data.get('assign_feed'):
            af_to_remove = AssignedFeed.query.filter(AssignedFeed.for_feed.mongo_id == feed_id).first()
            if af_to_remove:
                AssignedFeed.remove(af_to_remove)
        return redirect(url_for('dashboard'))


@app.route('/unassignfeed/<feed_id>')
@login_required
def unassign_feed(feed_id):
    assigned_feed = AssignedFeed.query.filter(
        AssignedFeed.assigned_to.mongo_id == current_user.mongo_id
    ).filter(
        AssignedFeed.for_feed.mongo_id == feed_id
    ).one()
    AssignedFeed.remove(assigned_feed)
    feeds_assigned = AssignedFeed.query.filter(
        AssignedFeed.assigned_to.mongo_id == current_user.mongo_id
    ).ascending('display_order').all()
    for feed in enumerate(feeds_assigned):
        af_to_update = AssignedFeed.query.filter(
            AssignedFeed.assigned_to.mongo_id == current_user.mongo_id
        ).filter(
            AssignedFeed.display_order == feed[1].display_order
        )
        af_to_update.set(AssignedFeed.display_order, feed[0] + 1).execute()
    return '1'


@app.route('/assignfeed/<feed_id>')
@login_required
def assign_feed(feed_id):
    assigned_feed_query = AssignedFeed.query.filter(AssignedFeed.assigned_to.mongo_id == current_user.mongo_id).all()
    feed_to_assign = AssignedFeed(
        assigned_to=User.query.filter(User.mongo_id == current_user.mongo_id).one(),
        for_feed=Feed.query.filter(Feed.mongo_id == feed_id).one(),
        display_order=len(assigned_feed_query) + 1,
        max_links=10
    )
    feed_to_assign.save()
    return '1'


if __name__ == '__main__':
    app.run()
