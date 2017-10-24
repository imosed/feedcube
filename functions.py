from re import sub


def df():
    #  Date d(isplay) f(ormat)
    return '%a, %d %b %Y %H:%M:%S GMT'


def get_fields_from_form(form):
    #  Exclude csrf token
    return [field for field in form][1:]


def xml_to_dict(element):
    #  Map XML values to a dictionary
    return dict([(child.tagName, child.childNodes[0].data)
                 for child in element.childNodes
                 if child.nodeType == 1 and child.childNodes and child.childNodes[0].nodeType in [3, 4]])


def rescue_value(d, v, r):
    if v in d:
        return d[v]
    else:
        return r


def gen_title(s):
    title = ' '.join(s.split(' ')[:18])
    title = ' '.join(title[:130].split(' ')[:-1])
    return '%s...' % title


def format_description(desc, max_chars=500):
    #  Remove HTML tags and ensure only full words are displayed
    return ' '.join(sub('<\S[^>]*(>|$)', '', desc)[:max_chars].split(' ')[:-1])
