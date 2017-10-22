from wtforms import StringField
from wtforms.validators import DataRequired
from .loginform import Login


class Register(Login):
    email_address = StringField('Email Address', validators=[DataRequired()])
