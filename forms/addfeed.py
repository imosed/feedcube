from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import DataRequired


class AddFeed(Form):
    feed_name = StringField('Feed name', validators=[DataRequired()])
    feed_location = StringField('Feed location', validators=[DataRequired()])
