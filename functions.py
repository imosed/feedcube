from re import sub
from datetime import datetime as dt


def df(date_str):
    #  Date d(isplay) f(ormat)
    if not date_str[0].isdigit():
        return dt.strptime(date_str, '%a, %d %b %Y %H:%M:%S GMT')
    else:
        return dt.strptime(date_str.split('+')[0], '%Y-%m-%dT%H:%M:%S')


def get_fields_from_form(form):
    #  Exclude csrf token
    return [field for field in form][1:]


def find_data(parent_node):
    #  Find descendant text node
    node = parent_node
    while node.childNodes and node.childNodes[0].nodeType not in [3, 4]:
        node = node.childNodes[0]
    return node.data


def xml_to_dict(element):
    #  Map XML values to a dictionary
    vals = []
    attrs = []
    for child in element.childNodes:
        if child.nodeType == 1 and child.childNodes and child.childNodes[0].nodeType in [3, 4]:
            vals += [(child.tagName, find_data(child.childNodes[0]))]
        if child.nodeType == 1 and child.hasAttributes():
            attrs += child.attributes.items()
    vals = dict(vals)
    attrs = dict(attrs)
    vals.update(attrs)
    return vals


def rescue_value(v, *rv):
    #  If v doesn't exist, return the first rv that does
    if v:
        return v
    for val in rv:
        if val:
            return val
        else:
            continue


def gen_title(s):
    #  Prepare a title from another string
    if s:
        title = ' '.join(s.split(' ')[:18])
        title = ' '.join(title[:130].split(' ')[:-1])
        return '%s...' % title
    else:
        return None


def format_description(desc, max_chars=500):
    #  Remove HTML tags and ensure only full words are displayed
    if desc:
        return ' '.join(sub('<\S[^>]*(>|$)', '', desc)[:max_chars].split(' ')[:-1])
    else:
        return None
