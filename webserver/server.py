import os
import time
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from flask import Flask, request, render_template, g, redirect, Response, session, url_for, flash
from datetime import date
from flask.ext.cache import Cache
from flask import send_from_directory
from werkzeug import secure_filename

import random

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

app = Flask(__name__, template_folder=tmpl_dir)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
cache = Cache(app,config={'CACHE_TYPE': 'simple'})

DATABASEURI = "postgresql://postgres:abcd@localhost/postgres"
engine = create_engine(DATABASEURI)


@app.before_request
def before_request():

  g.start=time.time();
  try:
    g.conn = engine.connect()
  except:
    print "Not able to connect"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):

  elapse = time.time()-g.start;
  print elapse;
  try:
    g.conn.close()
  except Exception as e:
    pass

@cache.cached(timeout=5)
@app.route('/login', methods=['GET', 'POST'])
def login():
    print('request login')
    error = None
    if request.method == 'POST':
        print('requested POST login')
        session['rand'] = False
        if(request.form['username']=='sudo'):
          cur = g.conn.execute("SELECT * FROM users u, admin a WHERE u.u_id=a.u_id ORDER BY random() limit 1;")
          identity = cur.fetchone()
          session['username'] = identity[1]
          session['userId'] = identity[0]
          session['logged_in'] = True
          session['rand'] = True
          session['isadmin'] = True
          return redirect('/all')
        if(request.form['username']=='admin'):
          cur = g.conn.execute("SELECT * FROM users u, admin a WHERE u.u_id=a.u_id ORDER BY random() limit 1;")
          identity = cur.fetchone()
          session['username'] = identity[1]
          session['userId'] = identity[0]
          session['logged_in'] = True
          session['isadmin'] = True
          return redirect('/all')
        if(request.form['username']=='user'):
          cur = g.conn.execute("SELECT * FROM users u WHERE u.u_id not in (SELECT * FROM admin) AND u.u_id not in (SELECT u_id from ban) ORDER BY random() limit 1;")
          identity = cur.fetchone()
          session['username'] = identity[1]
          session['userId'] = identity[0]
          session['logged_in'] = True
          session['isadmin'] = False
          return redirect('/all')
        query =  "SELECT * FROM users WHERE u_name=%s and u_password=%s;"
        cursor = g.conn.execute(query,(request.form['username'],request.form['password']))
        number = 0
        username = ''
        userId = 0
        for result in cursor:
          print('found')
          number=number+1
          username = result[1]
          userId = result[0] 
        cursor.close()
        print(number)
        if number==0:
            error = 'User not found'
            flash(error)
        elif number>1:
            error = 'Multiple users found'
            flash(error)
        else:
            query = "SELECT count(*) FROM ban WHERE u_id=%s"
            data = (userId,)
            cursor = g.conn.execute(query,data)
            record = cursor.fetchone()
            if(record[0] != 0):
             error = 'User banned'
             flash(error)
            else:
              #Check if admin
              query =  "SELECT COUNT(*) FROM admin WHERE u_id=%s;"
              data = (userId,)
              cursor = g.conn.execute(query,data)
              record = cursor.fetchone()
              if(record[0] != 0):
               session['isadmin'] = True
              else:
               session['isadmin'] = False
              #end check admin
              session['username'] = username
              session['userId'] = userId
              session['logged_in'] = True
              flash('You were logged in')
              return redirect('/all')
              
    return render_template('login.html', error=error,time=time)

#upload begins

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    print('upload pic')
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file', filename=filename))
    return 
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
       
#upload ends


@app.route('/logout')
def logout():
    print('logging out')
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect('/login')

def CommentUnfold(Tree,Hashlist,CommentList,deepness):
    for i in Tree:
      CommentList.append((i,deepness))
      CommentUnfold(Hashlist[str(i[0])],Hashlist,CommentList,deepness+1)

def getRandomUser():
  cur = g.conn.execute("SELECT * FROM users ORDER BY random() limit 1")
  return(cur.fetchone())

def getRandomDate(start=None):
  end = date.today().toordinal()
  if start==None:
    start = end-360
  return(str(date.fromordinal(random.randint(start,end))))

@app.route('/all')
def all():
    print(not session.get('logged_in'))
    if(not session.get('logged_in')):
        return redirect('/login')
    query =  'SELECT * \
                FROM question_posted ORDER BY q_date DESC;'
    cursor = g.conn.execute(query)
    questions=[]
    for result in cursor:
        questions.append(result)  
    cursor.close()
    t=time.time();
    return(render_template('all.html', questions=questions))
    elapsed = time.time()-t;
    print elapsed;

@app.route('/post')
def post():
    print('loading post')
    if(not session.get('logged_in')):
        return redirect('/login')
    info = request.args#id is passed in the request arguments in the URL
    pid = info['id']
    print "####";
    print pid;
    t = time.time();
    #get excited for question and text 
    query =  'SELECT count(*) \
              FROM question_posted q, excited e \
              WHERE q.q_id=%s AND q.q_id=e.q_id;'
    cursor = g.conn.execute(query,(pid,))
    record = cursor.fetchone()
    excite = record[0]
    cursor.close()

    #has the user liked it before
    query =  'SELECT count(*) \
              FROM question_posted q, excited e \
              WHERE q.q_id=%s AND q.q_id=e.q_id AND e.u_id=%s;'
    cursor = g.conn.execute(query,(pid,session['userId'],))
    record = cursor.fetchone()
    userExcited = (record[0]==1)
    cursor.close()

    #get the text for the question
    query =  'SELECT * \
              FROM question_posted q, users u \
              WHERE q.q_id=%s AND q.u_id=u.u_id;'
    cursor = g.conn.execute(query,(pid,))
    record = cursor.fetchone()
    question = {'text':record['q_text'],'date':record['q_date'],'excite':excite,'id':pid, 'u_id':record['u_id'], 'u_name':record['u_name']}
    cursor.close()

    #get the answers text and votes for the question
    query =  'select agg.q_id,agg.a_text,agg.a_id,count(v.a_id) c,agg.a_date,agg.u_id,agg.u_name\
              FROM vote v\
              RIGHT JOIN\
              (SELECT a.a_id,a.q_id,a.u_id,a.a_text,a.a_date,u.u_name FROM question_posted q, answer_proposed a, users u\
              WHERE q.q_id=%s AND q.q_id=a.q_id AND u.u_id=a.u_id) agg\
              ON agg.a_id=v.a_id\
              GROUP BY agg.a_id,agg.q_id,agg.u_id,agg.a_text,agg.a_date,agg.u_name\
              ORDER BY c DESC;'
    cursor = g.conn.execute(query,(pid,))
    answers = []
    total = 0.
    for result in cursor:
      answers.append((result[1],result[3],result[2],result[4], result[5],result[6]))  
      total += result[3]
    cursor.close()

    #get the user's vote choice
    query =  'SELECT a.a_id, v.v_date\
              FROM question_posted q, answer_proposed a, vote v\
              WHERE q.q_id=%s AND q.q_id=a.q_id AND a.a_id=v.a_id AND v.u_id=%s;'
    cursor = g.conn.execute(query,(pid,session['userId']))
    record = cursor.fetchone()
    print(record!=None)
    print(record)
    print((pid,session['userId']))
    vote = [record!=None,0]
    if(vote[0]):
      vote[1]=tuple(record)
    cursor.close()

    #get the comments for the question, displayed in Chronological per deepness order
    query =  'SELECT BIG.c_id,BIG.c_parent_id,BIG.u_id,BIG.c_text,BIG.c_date,BIG.u_name,BIG.c,count(P.u_id) b FROM\
              (SELECT agg.c_id,agg.c_parent_id,agg.u_id,agg.c_text,agg.c_date,agg.u_name,count(L.u_id) c FROM\
              (SELECT c.c_id,c.c_parent_id,c.u_id,c.c_text,c.c_date, u.u_name\
              FROM question_posted q, comment_added c, users u\
              WHERE c.q_id=q.q_id AND q.q_id=%s AND c.u_id=u.u_id) agg\
              LEFT JOIN\
              (SELECT * FROM LIKES WHERE u_id=%s) L\
              ON agg.c_id=L.c_id\
              GROUP BY agg.c_id,agg.c_parent_id,agg.u_id,agg.c_text,agg.c_date,agg.u_name) big\
              LEFT JOIN\
              LIKES P\
              ON big.c_id=P.c_id\
              GROUP BY BIG.c_id,BIG.c_parent_id,BIG.u_id,BIG.c_text,BIG.c_date,BIG.u_name,BIG.c\
              ORDER BY big.c_date ASC, c_id ASC;'
    cursor = g.conn.execute(query,(pid,session['userId']))
    commentsTree = []
    commentHash = {'root':commentsTree}
    for result in cursor:#chronological order assumed from the query 
      selfId=result[0]
      parentId=result[1]
      newTree=[]
      parent=commentsTree
      if(parentId!=1):
        parent=commentHash[str(parentId)]
      parent.append(result)
      commentHash[str(selfId)]=newTree
    commentsList=[]
    CommentUnfold(commentsTree,commentHash,commentsList,0)
    cursor.close()
    elapsed = time.time()-t;
    print elapsed;
    return render_template('Jin.html', vote=vote, userExcited=userExcited, comments=commentsList, total=total, answers=answers, question=question)


# Example of adding new data to the database
@app.route('/likePost')
def likePost():
  print('liking post')
  pid = request.args['pid']
  g.conn.execute('INSERT INTO excited VALUES (%s,%s)', (session['userId'],pid,))
  return redirect('/post?id='+str(pid))

@app.route('/UnlikePost')
def UnlikePost():
  print('Unliking post')
  pid = request.args['pid']
  g.conn.execute('DELETE FROM excited WHERE u_id=%s AND q_id=%s;', (session['userId'],pid,))
  return redirect('/post?id='+str(pid))

@app.route('/votePost')
def votePost():
  print('Voting post')
  aid = request.args['aid']
  g.conn.execute('INSERT INTO vote VALUES (%s,%s,now())', (session['userId'],aid,))
  return redirect('/post?id='+str(request.args['pid']))

@app.route('/unvotePost')
def unvotePost():
  print('Unvoting post')
  aid = request.args['aid']
  g.conn.execute('DELETE FROM vote WHERE u_id=%s AND a_id=%s;', (session['userId'],aid,))
  return redirect('/post?id='+str(request.args['pid']))

@app.route('/addCommentRoot', methods=['GET', 'POST'])
def addCommentRoot():
  print('Commenting or reply')
  pid = request.args['pid']
  text = request.form['text']
  if 'random' in request.form:
    cur = g.conn.execute("select q_date from Question_posted where q_id=%s",(pid,))
    start = cur.fetchone()[0]
    cur.close()
    query = "INSERT INTO comment_added (c_parent_id,u_id,q_id,c_text,c_date) VALUES (1,%s,%s,%s,%s)"
    data = (getRandomUser()[0],pid,text,getRandomDate(start.toordinal()))
  else:
    query = "INSERT INTO comment_added (c_parent_id,u_id,q_id,c_text,c_date) VALUES (1,%s,%s,%s,now())"
    data = (session['userId'],pid,text)
  g.conn.execute(query,data)
  return redirect('/post?id='+str(pid))

@app.route('/addCommentForm')
def addCommentForm():
  return render_template('comment.html',cid=request.args['cid'],pid=request.args['pid'])

@app.route('/addComment', methods=['GET', 'POST'])
def addComment():
  pid = request.args['pid']
  cid = request.args['cid']
  text = request.form['text']
  if 'random' in request.form:
    cur = g.conn.execute("select c_date from comment_added where c_id=%s",(cid,))
    start = cur.fetchone()[0]
    cur.close()
    query = "INSERT INTO comment_added (c_parent_id,u_id,q_id,c_text,c_date) VALUES (%s,%s,%s,%s,%s)"
    data = (cid,getRandomUser()[0],pid,text,getRandomDate(start.toordinal()))
  else:
    query = "INSERT INTO comment_added (c_parent_id,u_id,q_id,c_text,c_date) VALUES (%s,%s,%s,%s,now())"
    data = (cid,session['userId'],pid,text)
  g.conn.execute(query,data)
  return redirect('/post?id='+str(pid))

@app.route('/likeComment')
def likeComment():
  print('liking comment')
  cid = request.args['cid']
  pid = request.args['pid']
  g.conn.execute('INSERT INTO likes VALUES (%s,%s)', (session['userId'],cid,))
  return redirect('/post?id='+str(pid))

@app.route('/UnlikeComment')
def UnlikeComment():
  print('unliking comment')
  cid = request.args['cid']
  pid = request.args['pid']
  g.conn.execute('DELETE FROM likes WHERE u_id=%s AND c_id=%s;', (session['userId'],cid,))
  return redirect('/post?id='+str(pid))

@app.route('/')
def index():
   return redirect('/all')

@app.route('/signup')
def signup():
   print('request signu page')
   return render_template('signup.html')

@app.route('/signupclick', methods=['GET', 'POST'])
def signupclick():
   print('sign up user')
   u_name = request.form['User name']
   u_password = request.form['Password']
   print "there"
   cursor = g.conn.execute("SELECT * FROM Users")
   print "here"
   exists = false
   for row in cursor:
    if(row[1] == u_name):
      exists = true
   if (u_name == ""):
     message = "No user name entered, cannot sign up"
     return message
   if (u_password == ""):
     message = "No password entered, cannot sign up"
     return message;
   if (exists == false): 
    query = "INSERT INTO Users (U_NAME,U_PASSWORD) VALUES (%s,%s)"
    data = (u_name,u_password,)
    g.conn.execute(query,data)
    message = "Signed up successfully"
   else:
    message = "This user name already exists, try a different one"
   return message
  

@app.route('/ban', methods=['GET', 'POST'])
def ban():
    print('ban user')
    cursor = g.conn.execute("SELECT * FROM Users")
    user_name = []
    user_id = []
    for row in cursor:
      
      alreadybanned = false;
      cursor1 = g.conn.execute("SELECT * FROM Ban")
      for row1 in cursor1:
        if (row1[0] == row[0]):
          alreadybanned = true

      query =  "SELECT COUNT(*) FROM admin WHERE u_id=%s;"
      data = (row[0],)
      cursor2 = g.conn.execute(query,data)
      record1 = cursor2.fetchone()

      isadm = false
      if(record1[0] != 0):
          isadm = true
      if (alreadybanned == false and isadm == false):
        user_id.append(row[0]);
        user_name.append(row[1]);
      
    return render_template('ban.html', user_name = user_name, user_id = user_id); 
    
@app.route('/banuser', methods=['GET', 'POST'])
def banuser():
   arg = request.args
   ban_id = arg['id']
   ban_name = arg['name']
   admin_id = session['userId'];

   query = "INSERT INTO BAN (u_id,admin_id) VALUES (%s,%s)"
   data = (ban_id,admin_id,)
   g.conn.execute(query,data)
   str1 =  ban_name
   str2 = "banned successfully by" 
   str3 = session['username']
   message = str1 + " " + str2 + " " + str3;
   return message;

@app.route('/addAnswer', methods=['GET', 'POST'])
def addAnswer():
  print('add answer')
  pid = request.args['pid']
  text = request.form['text']
  if 'random' in request.form:
    cur = g.conn.execute("select q_date from Question_posted where q_id=%s",(pid,))
    start = cur.fetchone()[0]
    cur.close()
    query = "INSERT INTO answer_proposed (q_id,u_id,a_text,a_date) VALUES (%s,%s,%s,%s)"
    data = (pid,getRandomUser()[0],text,getRandomDate(start.toordinal()))
  else:
    query = "INSERT INTO answer_proposed (q_id,u_id,a_text,a_date) VALUES (%s,%s,%s,now())"
    data = (pid,session['userId'],text)
  g.conn.execute(query,data)
  return redirect('/post?id='+str(pid))

@app.route('/addQuestion', methods=['GET','POST'])
def addQuestion():
  print('add question')
  text = request.form['text']
  if 'random' in request.form:
    query = "INSERT INTO question_posted (u_id, q_text,q_date) VALUES (%s,%s,%s)"
    data = (getRandomUser()[0],text,getRandomDate())
  else:
    query = "INSERT INTO question_posted (u_id, q_text,q_date) VALUES (%s,%s,now())"
    data = (session['userId'],text)
  g.conn.execute(query,data)
  return redirect('/all')

@app.route('/initialise')
def initialise():
  import names
  import random
  import string
  #initialise 50 users
  g.conn.execute("CREATE TABLE USERS\
       (U_ID bigserial PRIMARY KEY,\
       U_NAME TEXT NOT NULL,\
       U_PASSWORD TEXT NOT NULL);")
  for i in range(50): 
    U_NAME = names.get_full_name()
    U_PASSWORD = "".join( [random.choice(string.letters[:26]) for i in xrange(15)] )
    query=("INSERT INTO USERS (U_NAME,U_PASSWORD) VALUES (%s,%s);")
    data=(U_NAME,U_PASSWORD)
    g.conn.execute(query,data)
  #initialise 20% users (stochastic) as admins
  g.conn.execute("CREATE TABLE ADMIN\
       (U_ID INT PRIMARY KEY NOT NULL,\
       FOREIGN KEY (U_ID) REFERENCES USERS);")
  cur = g.conn.execute("SELECT U_ID from USERS;")
  for row in cur:
    if(random.random()>0.8):
      U_ID = row[0]
      query=("INSERT INTO ADMIN (U_ID) \
      VALUES (%s);")
      data=(U_ID,)
      g.conn.execute(query,data)

  #create questions
  g.conn.execute("CREATE TABLE Question_posted(\
  q_id bigserial PRIMARY KEY,\
  u_id int NOT NULL,\
  q_text text,\
  q_date date,\
  FOREIGN KEY (u_id) REFERENCES Users);")
  #create answers
  g.conn.execute("CREATE TABLE Answer_proposed(\
  a_id bigserial PRIMARY KEY,\
  q_id int NOT NULL,\
  u_id int NOT NULL,\
  a_text text,\
  a_date date,\
  FOREIGN KEY (u_id) REFERENCES Users,\
  FOREIGN KEY (q_id) REFERENCES Question_posted);")
  #create comments
  g.conn.execute("CREATE TABLE Comment_added(\
  c_id bigserial PRIMARY KEY,\
  c_parent_id int,\
  u_id int,\
  q_id int,\
  c_text text,\
  c_date date,\
  FOREIGN KEY (u_id) REFERENCES Users,\
  FOREIGN KEY (q_id) REFERENCES Question_posted,\
  FOREIGN KEY (c_parent_id) REFERENCES Comment_added);")
  g.conn.execute("INSERT INTO comment_added (c_parent_id) VALUES (1)")
  #create vote
  g.conn.execute("CREATE TABLE VOTE\
  (u_id int,\
  a_id int,\
  v_date date,\
  PRIMARY KEY (u_id,a_id),\
  FOREIGN KEY (u_id) REFERENCES Users,\
  FOREIGN KEY (a_id) REFERENCES Answer_proposed);")
  #create likes
  g.conn.execute("CREATE TABLE LIKES\
  (u_id int,\
  c_id int,\
  PRIMARY KEY (u_id,c_id),\
  FOREIGN KEY (u_id) REFERENCES Users,\
  FOREIGN KEY (c_id) REFERENCES Comment_added );")
  #create excited
  g.conn.execute("CREATE TABLE EXCITED\
  (u_id int,\
  q_id int,\
  PRIMARY KEY (u_id,q_id),\
  FOREIGN KEY (u_id) REFERENCES Users,\
  FOREIGN KEY (q_id) REFERENCES Question_posted );")
  #create ban
  g.conn.execute("CREATE TABLE BAN(\
  u_id int,\
  admin_id int NOT NULL,\
  PRIMARY KEY (u_id),\
  FOREIGN KEY (u_id) REFERENCES Users,\
  FOREIGN KEY (admin_id) REFERENCES Admin);")
  return redirect('/all')


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
  
    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=True, threaded=threaded)


  run()
