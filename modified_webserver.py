# By default, starts the webserver listening
# on localhost at:
# 
#   http://localhost:8080/
#
# To start server:
# python webserver.py


from wsgiref import util        # simple python web server
from string  import Template    # basic template engine
import random
import sqlite3                  # database
import urlparse
import Cookie                   # parsing HTTP cookies
import traceback
import time
import re
import urllib
from bs4 import BeautifulSoup

DBFN = "database.sqlite3"

link_finder = re.compile(r"(.*?)@(\w+)(.*)")

# Functions for creating and populating a new database.
def create_database():
    conn = sqlite3.connect(DBFN)
    c    = conn.cursor()
    c.execute("CREATE TABLE accounts (username string primary key, password string, public boolean default 'f');")
    c.execute("CREATE TABLE squigs (username string, body text, time datetime);")
    c.execute("CREATE TABLE sessions (session_id primary key, username string, time datetime);")
    conn.commit()
    c.close()

# Ignore this function
def populate_with_storyline():
    f = open("storyline.txt").readlines()
    for l in f:
        u,s = l.split(":")
        u = u.strip()
        s = s.strip()
        post_squig(u, s)
    time.sleep(1.1) # wait 1.1 seconds between posts

# Controllers for interacting with web application
def get_all_public_users():
    conn = sqlite3.connect(DBFN)
    c    = conn.cursor()
    
    # Patch 8 starts
    
    temp2 = """SELECT username FROM accounts WHERE public = 't';"""
    users = c.execute(temp2).fetchall() 
    
    # Patch 8 ends
    
    c.close()
    return users if users else []

# Get user based on the session id (cookie)
def get_user(session_id):
    if not session_id: return None
    conn = sqlite3.connect(DBFN)
    c    = conn.cursor()
    
    # Patch 7 starts
    
    sql_getuser_query = """SELECT username FROM sessions WHERE session_id = ?;"""
    getuser_data = (session_id,)
    user = c.execute(sql_getuser_query, getuser_data).fetchone() 
    
    # Patch 7 ends
    
    user = user[0] if user else None
    c.close()
    return user if user else None

# Ignore this function
def is_private(user):
    if not user: return False
    conn = sqlite3.connect(DBFN)
    c    = conn.cursor()
    public = c.execute("SELECT public from accounts where username='%s'" % user).fetchone()
    if public:
        public = public[0]
        public = True if public == 't' else False
        c.close()
        return not public
    else:
        return False

# Logout the user and delete their cookie
def logout_user(user):
    if not user: return None
    conn = sqlite3.connect(DBFN)
    c    = conn.cursor()
    
    # Patch 4 starts
    
    sql_logout_query = """DELETE FROM sessions WHERE username = ?;"""
    logout_data = (user,)
    c.execute(sql_logout_query, logout_data) 
    
    # Patch 4 ends
    
    conn.commit()
    c.close()
    return None

# Check if a valid password is being entered
def test_password(user, password):
    if not user: return False
    conn = sqlite3.connect(DBFN)
    
    c    = conn.cursor() 
    
    # Patch 1 starts
    
    sql_select_query = """SELECT password from accounts where username = ?;"""
    select_data = (user,)
    db_password = c.execute(sql_select_query, select_data).fetchone() 
    
    # Patch 1 ends
     
    db_password = db_password[0] if db_password else None
    c.close()
    return password == db_password

# Login user and create new session id
def login_user(user):
    if not user: return None
    logout_user(user)
    r    = str(random.randint(0,10**9))
    conn = sqlite3.connect(DBFN)
    c    = conn.cursor()
    
    # Patch 5 starts
    
    sql_login_query = """INSERT INTO sessions VALUES (?, ?, datetime('now', 'localtime'));"""
    login_data = (r, user)
    c.execute(sql_login_query, login_data) 
    
    # Patch 5 ends
    
    conn.commit()
    c.close()
    return r

# Return top 10 posts of users for displaying
def get_squigs(user):
    if not user: return []
    conn = sqlite3.connect(DBFN)
    c    = conn.cursor()
    
    # Patch 6 starts
    
    sql_getsquigs_query = """SELECT body, time FROM squigs WHERE username = ? ORDER BY time DESC LIMIT 10;"""
    getsquigs_data = (user,)
    squigs = c.execute(sql_getsquigs_query, getsquigs_data).fetchall() 
    
    # Patch 6 ends
    
    c.close()
    return squigs

# Sanitizing/Validating user input
def sanitize(value):
    VALID_TAGS = ['strong', 'em', 'p', 'ul', 'li', 'br']
    soup = BeautifulSoup(value, features='html.parser')

    for tag in soup.findAll(True):
        if tag.name not in VALID_TAGS:
            tag.hidden = True

    return soup.renderContents()

# For posting a squig
def post_squig(user, squig):
    if not user or not squig: return
    conn = sqlite3.connect(DBFN)
    c    = conn.cursor()
    
    # Patch 2 starts
    
    squig = sanitize(squig)
    
    sql_insert_query = """INSERT INTO squigs VALUES (?, ?, datetime('now', 'localtime'));"""
    insert_tuple = (user, squig)
    c.execute(sql_insert_query, insert_tuple)
    
    # Patch 2 ends
    
    conn.commit()
    c.close()

# For deleing a squig
def del_squig(user, time):
    if not user or not time: return
    conn = sqlite3.connect(DBFN)
    c    = conn.cursor()
    
    # Patch 3 starts
    
    sql_delete_query = """DELETE FROM squigs WHERE username = ? and time = ?;"""
    delete_tuple = (user, time)
    c.execute(sql_delete_query, delete_tuple)
    
    # Patch 3 ends
    
    conn.commit()
    c.close()

# Using the search bar
def search_squigs(query):
    if not query: return []
    conn = sqlite3.connect(DBFN)
    c    = conn.cursor()
    
    # Patch 4 starts
    
    query = sanitize(query)
    
    temp = "%" + query + "%" # wild card
    
    sql_search_query = """SELECT squigs.username, squigs.body, squigs.time FROM squigs, accounts WHERE squigs.username == accounts.username AND (body LIKE ? OR squigs.username = ?) AND accounts.public = 't' ORDER BY squigs.time DESC LIMIT 10;"""
    search_tuple = (temp, query.strip(),)
    squigs = c.execute(sql_search_query, search_tuple).fetchall()
    
    # Patch 4 ends
    
    c.close()
    return squigs

def add_links(squigR):
    squigL = ""
    m = link_finder.match(squigR)
    while m:
        if is_private(m.group(2)):
            # do not link to private usernames
            squigL = squigL + m.group(1) + "@" + m.group(2)
            squigR = m.group(3)
        else:
            squigL = squigL + m.group(1) + ('<a href="/userpage?user=%s">@%s</a>' % (m.group(2), m.group(2)))
            squigR = m.group(3)
            
        m = link_finder.match(squigR)
    return squigL + squigR
        
# HTML Templates for each page construction
index_page = Template("""
<html><head><title>$title</title></head><body style="font-family: helvetica;background:#5599bb;color:#ddeeff;margin:50px 0px; padding:0px; text-align:center;">
<style type="text/css">
A:link {text-decoration: none; color:#333}
A:visited {text-decoration: none; color:#333}
A:active {text-decoration: none}
A:hover {text-decoration: underline;}
</style>

<img src="images/logo.png" style="margin:0px auto;" />

<div style="padding:4em;">

<form action="search" method="get" id="searchbar">
    <input name="q" id="q" type="text" size=40 style="font-size:150%;" />
    <input type="submit" value="Search!" style="font-size:250%;" />
</form>

<script type="text/javascript">
    document.getElementById('q').focus();
</script>
$body

</div>

</body></html>
""")

user_page = Template("""
<html><head><title>My Squig Page</title></head><body style="font-family: helvetica;background:#5599bb;color:#ddeeff;margin:0px 0px; padding:0px;">
<style type="text/css">
A:link {text-decoration: none; color:#ddeeff}
A:visited {text-decoration: none; color:#ddeeff}
A:active {text-decoration: none}
A:hover {text-decoration: underline;}
A:link.asquig {text-decoration: none; color:#ffffff}
A:visited.asquig {text-decoration: none; color:#ffffff}
</style>

<a href="/"><img border="0" src="images/logo_small.png" style="padding:16px;margin:0px auto;" /></a>

<div style="font-size:250%; padding:0px; text-align:center"><b>$username</b> $lock</div>

<div style="padding:4em; text-align:center;">
    $form
    $squigs
</div>

</body></html>
""")

list_user_page = Template("""
<html><head><title>List of Public Users</title></head><body style="font-family: helvetica;background:#5599bb;color:#ddeeff;margin:0px 0px; padding:0px;">
<style type="text/css">
A:link {text-decoration: none; color:#ddeeff}
A:visited {text-decoration: none; color:#ddeeff}
A:active {text-decoration: none}
A:hover {text-decoration: underline;}
</style>

<a href="/"><img border="0" src="images/logo_small.png" style="padding:16px;margin:0px auto;" /></a>

<div style="padding:4em; text-align:center;">

$users

</div>

</body></html>
""")

search_results_page = Template("""
<html><head><title>Search results</title></head><body style="font-family: helvetica;background:#5599bb;color:#ddeeff;margin:0px 0px; padding:0px;">
<style type="text/css">
A:link {text-decoration: none; color:#ddeeff}
A:visited {text-decoration: none; color:#ddeeff}
A:active {text-decoration: none}
A:hover {text-decoration: underline;}
</style>

<a href="/"><img border="0" src="images/logo_small.png" style="padding:16px;margin:0px auto;" /></a>

<div style="padding:4em; text-align:center;">

$results

<a href="/">Go back</a>

</div>



</body></html>
""")

login_page = Template("""
<html><head><title>Log in</title></head><body style="font-family: helvetica;background:#5599bb;color:#ddeeff;margin:0px 0px; padding:0px;">
<style type="text/css">
A:link {text-decoration: none; color:#ddeeff}
A:visited {text-decoration: none; color:#ddeeff}
A:active {text-decoration: none}
A:hover {text-decoration: underline;}
</style>

<a href="/"><img border="0" src="images/logo_small.png" style="padding:16px;margin:0px auto;" /></a>

<div style="padding:4em; text-align:center;">

<form action="do_login" method="get" id="loginform">
    <div><input name="user"      id="user" type="text" size=40 style="font-size:150%;" /></div>
    <div><input name="password"  id="password" type="password" size=40 style="font-size:150%;" /></div>
    <div><input type="submit" value="Log in!" style="font-size:250%;" /></div>
</form>

<script type="text/javascript">
    document.getElementById('user').focus();
</script>
</div>

</body></html>
""")

redirect = Template("""
<html><head>
  <meta http-equiv="Refresh" content="0; url=$URL" />
</head><body style="font-family: helvetica;background:#5599bb;color:#ddeeff;margin:0px 0px; padding:0px;">
</body></html>

""")
 
four_oh_four = Template("""
<html><body>
  <h1>404-ed!</h1>
  The requested URL <i>$url</i> was not found.
</body></html>""")
 
# Template Variables for each page (not really used)
pages = {
    'index': { 'title': "Hello There",
               'body':  
               """This is a test of the WSGI system.
                Perhaps you would also be interested in
                <a href="this_page">this page</a>?""",
                'text': ""
              },
    'this_page': { 'title': "You're at this page",
                   'body': 
                   """Hey, you're at this page.
                   <a href="/">Go back</a>?"""
                   },
    'login': {}
        
    }

# Request handler. This is called for every time a URL is requested from this web application.
# based on http://probablyprogramming.com/2008/06/26/building-a-python-web-application-part-1/
def handle_request(environment, start_response):
    response = ""
    try:
        # get the file name from the requested URL
        fn = environment.get("PATH_INFO")[1:]
        
        # get any query variables from the requested URL (e.g., http://.../?squig=the_message)
        query = urlparse.parse_qs(environment.get("QUERY_STRING"))
        
        # get session_id value from cookie
        C = Cookie.SimpleCookie(environment.get("HTTP_COOKIE"))
        session_id = C.get('session_id').value if C.get('session_id') else None
        
        # look up user given session_id
        user = get_user(session_id)
        print "USER", user, environment.get("HTTP_COOKIE")        
        
        # Image handling approach: anything in "images/" is treated as a PNG file.
        # Beware path traversal!
        if not fn:
            fn = 'index'
        if fn.startswith("images/"):
            start_response('200 OK', [('content-type', 'image/png')])
            return [open(fn).read()]
        
        # Code for handling page requests and actions.
        if fn == 'index':
            context = pages[fn]
            links = []
            if user:
                links.append('Welcome <b>%s</b>' % user)
                links.append('<a href="userpage?user=%s">My squigs</a>' % user)
                links.append('<a href="logout?redirect=/">Logout</a>')
                links.append('<a href="public_users">Browse users</a>')
            else:
                links.append('<a href="login">Login</a>')
                links.append('<a href="public_users">Browse users</a>')
            context['body'] = " | ".join(links)
            response = index_page.substitute(**context)

        elif fn == 'redirect':
            u = query.get("url")[0]
            start_response('200 OK', [('location', str(u))])
            return [redirect.substitute({"URL":u})]

        elif fn == 'login':
            response = login_page.substitute()
            
        elif fn == 'logout':
            next = query.get("redirect", ["/"])[0]
            logout_user(user)            
            cookie = "session_id=-1"
            start_response('200 OK', [('location', next),('set-cookie', cookie)]) # clear cookie...
            return [redirect.substitute({"URL":next})]
            
        elif fn == 'do_squig':
            print "REDIRECT:", query.get("redirect")

            next = query.get("redirect", ["/"])[0]
            if user not in next:
                next = '/userpage?user=' + str(user)
            s = query.get("squig", [""])[0]
            post_squig(user,s)
            print "REDIRECT TO", next
            start_response('200 OK', [('location', next)])
            return [redirect.substitute({"URL":next})]
            
        elif fn == 'do_delete_squig':
            print "REDIRECT:", query.get("redirect")
            next = query.get("redirect", ["/"])[0]
            u = query.get("user", [""])[0]
            t = query.get("time", [""])[0]
            
            # Test that only logged in user is deleting their own squig...
            if u == user:
                del_squig(u,t)
            print "REDIRECT TO", next
            start_response('200 OK', [('location', next)])
            return [redirect.substitute({"URL":next})]
            
        elif fn == 'do_login':
            next = query.get("redirect", ["/"])[0]
            u = query.get("user", [""])[0]
            p = query.get("password", [""])[0]
            
            # test password.
            if test_password(u,p):
                # create session object and login user.
                sid=login_user(u)
                cookie = "session_id=" + sid
                
                start_response('200 OK', [('location', next), ('set-cookie', cookie)])
                return [redirect.substitute({"URL":next})]
            else:
                start_response('200 OK', [('location', '/login')])
                return [redirect.substitute({"URL":"/login"})]
                
        elif fn == "userpage":
            u = query.get("user", [""])[0]
            squigs = get_squigs(u)

            form = ""
            if u == user:
                form = """
                    <form action="do_squig" method="get" id="squigform">
                        <input type="hidden" name="redirect" id="redirect" value="/userpage?user=%s" />
                        <div><textarea rows="2" cols="20" name="squig" id="squig" style="padding:0em; margin:0em auto; width:500px; font-size:150%%;"></textarea></div>
                        <div><input type="submit" value="Squig it!" style="font-size:250%%;" /></div>
                    </form>
                    <script type="text/javascript">
                        document.getElementById('squig').focus();
                    </script>
                """ % (u)

            output = ""
            for sq in squigs:
                # make delete button if necessary
                delbutton = ""
                if u == user:
                    delbutton = '<div style="float:right; margin=0px; padding=0px; padding-left:.5em;"><a href="do_delete_squig?user=%s&time=%s&redirect=userpage?user=%s"><img src="images/ex.png" width="20" height="20" /></a></div>' % (user, sq[1], user)
                # build html...
                output += ' <div class="asquig" style="position:relative;text-align:left;width:500px; padding:1em; margin:8px auto; background:#224466"> %s <b>%s</b> %s </div> ' % (delbutton, sq[1], add_links(sq[0]))

            lock = ""
            if is_private(u):
                lock = """<img src="images/lock.png" width=32 height=32 /> """
            response = user_page.substitute({"squigs":output, "form":form, "username":u, "lock":lock})
            
        elif fn == "public_users":
            users = get_all_public_users()
            output = ""
            for u in users:
                output += ' <div style="width:500px; padding:4px; margin:4px auto; background:#224466"><a href="userpage?user=%s">%s</a></div> ' % (str(u[0]),str(u[0]))
            response = list_user_page.substitute({"users":output})
            
        elif fn == "search":
            s = query.get("q", [""])[0]
            results = search_squigs(s)
            output = ""
            for sq in results:
                output += '<div  class="asquig" style="text-align:left;width:500px; padding:1em; margin:1em auto; background:#224466"><a href="userpage?user=%s"><b>%s %s</b> says...</a> %s </div>' % (sq[0],sq[2], sq[0], add_links(sq[1]))
            response = search_results_page.substitute({"results":str(output)})
        
        elif fn.startswith("favicon.ico"):
            # no favicon.
            pass
            
        else:
            raise BaseException("not found")

        start_response('200 OK', [('content-type', 'text/html')])
    except:
        start_response('404 Not Found', [('content-type', 'text/html')])
        # response = four_oh_four.substitute(url=util.request_uri(environment))
        response = four_oh_four.substitute(url=urllib.unquote(util.request_uri(environment)))
        traceback.print_exc()
    response = str(response)
    return [response]
 
if __name__ == '__main__':

    from wsgiref import simple_server
 
    print("Starting server on port 8080...")
    try:
        simple_server.make_server('', 8080, handle_request).serve_forever()
    except KeyboardInterrupt:
        print("Ctrl-C caught, Server exiting...")
