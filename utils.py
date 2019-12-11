
from functools import wraps
from flask import abort, redirect, request, session, url_for
import re
from html.parser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def get_object_or_404(cls, object_id):
  try:
    return cls.get(cls.id==object_id)
  except:
    abort(404)

def get_object_or_None(cls, object_id):
  try:
    return cls.get(cls.id==object_id)
  except:
    return None
    
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not(session.get('is_authenticated')):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def cleanhtml(raw_html):
  """clean the html tags from a string"""
  cleanr = re.compile('<.*?>')
  cleantext = re.sub(cleanr, '', raw_html)
  return cleantext

def slugify(s):
  """
  Simplifies ugly strings into something URL-friendly.
  >>> print slugify("[Some] _ Article's Title--")
  some-articles-title
  CREDIT - Dolph Mathews (http://blog.dolphm.com/slugify-a-string-in-python/)
  
  My modification, allow slashes as pseudo directory.
  slug=/people/dirk-gently => people/dirk-gently
  """

  # "[Some] _ Article's Title--"
  # "[some] _ article's title--"
  s = s.lower()

  # "[some] _ article's_title--"
  # "[some]___article's_title__"
  for c in [' ', '-', '.']:
    s = s.replace(c, '_')

  # "[some]___article's_title__"
  # "some___articles_title__"
  #s = re.sub('\W', '', s)
  s = re.sub('[^a-zA-Z0-9_/]','',s)
  
  # multiple slashew replaced with single slash
  s = re.sub('[/]+', '/', s)
  
  # remove leading slash
  s = re.sub('^/','', s)
  
  # remove trailing slash
  s = re.sub('/$','', s)

  # "some___articles_title__"
  # "some   articles title  "
  s = s.replace('_', ' ')

  # "some   articles title  "
  # "some articles title "
  s = re.sub('\s+', ' ', s)

  # "some articles title "
  # "some articles title"
  s = s.strip()

  # "some articles title"
  # "some-articles-title"
  s = s.replace(' ', '-')
  
  # a local addition, protects against someone trying to mess with slugless url
  s = re.sub('^page/','page-',s)

  return s