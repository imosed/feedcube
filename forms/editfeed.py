from flask_wtf import Form
from wtforms import IntegerField, BooleanField
from wtforms.validators import DataRequired


class EditFeed(Form):
    max_links = IntegerField('Max links', validators=[DataRequired()])
    display_order = IntegerField('Display order', validators=[DataRequired()])
    assign_feed = BooleanField('Assign feed', validators=[DataRequired()])
