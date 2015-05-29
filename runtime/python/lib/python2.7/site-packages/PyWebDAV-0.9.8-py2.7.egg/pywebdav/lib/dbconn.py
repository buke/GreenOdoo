import logging

log = logging.getLogger(__name__)

try:
    import MySQLdb
except ImportError:
    log.info('No SQL support - MySQLdb missing...')
    pass

import sys

class Mconn:
    def connect(self,username,userpasswd,host,port,db):
        try: connection = MySQLdb.connect(host=host, port=int(port), user=username, passwd=userpasswd,db=db)
        except MySQLdb.OperationalError, message:
            log.error("%d:\n%s" % (message[ 0 ], message[ 1 ] ))
            return 0
        else:
            self.db = connection.cursor()

            return 1

    def execute(self,qry):
        if self.db:
            try: res=self.db.execute(qry)
            except MySQLdb.OperationalError, message:
                log.error("Error %d:\n%s" % (message[ 0 ], message[ 1 ] ))
                return 0

            except MySQLdb.ProgrammingError, message:
                log.error("Error %d:\n%s" % (message[ 0 ], message[ 1 ] ))
                return 0

            else:
                log.debug('Query Returned '+str(res)+' results')
                return self.db.fetchall()

    def create_user(self,user,passwd):
        qry="select * from Users where User='%s'"%(user)
        res=self.execute(qry)
        if not res or len(res) ==0:
            qry="insert into Users (User,Pass) values('%s','%s')"%(user,passwd)
            res=self.execute(qry)
        else:
            log.debug("Username already in use")

    def create_table(self):
        qry="""CREATE TABLE `Users` (
                  `uid` int(10) NOT NULL auto_increment,
                  `User` varchar(60) default NULL,
                  `Pass` varchar(60) default NULL,
            `Write` tinyint(1) default '0',
                  PRIMARY KEY  (`uid`)
                ) ENGINE=MyISAM DEFAULT CHARSET=latin1"""
        self.execute(qry)


    def first_run(self,user,passwd):
        res= self.execute('select * from Users')
        if res or type(res)==type(()) :
            pass
        else:
            self.create_table()
            self.create_user(user,passwd)


    def __init__(self,user,password,host,port,db):
        self.db=0
        self.connect(user,password,host,port,db)

