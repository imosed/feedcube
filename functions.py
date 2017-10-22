from re import sub


def df():
    #  Date d(isplay) f(ormat)
    return '%a, %d %b %Y %H:%M:%S GMT'


def get_fields_from_form(form):
    #  Exclude csrf token
    return [field for field in form][1:]


def xml_to_dict(element):
    #  Map XML values to a dictionary
    return dict([(child.tagName, child.childNodes[0].data) for child in element.childNodes if child.nodeType == 1])


def format_description(desc, max_chars=500):
    #  Remove HTML tags and ensure only full words are displayed
    return ' '.join(sub('<[^>]+(>|$)', '', desc)[:max_chars].split(' ')[:-1])

