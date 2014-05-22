#Copyright (c) 1999 Christian Scholz (ruebe@aachen.heimat.de)
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Library General Public
#License as published by the Free Software Foundation; either
#version 2 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#Library General Public License for more details.
#
#You should have received a copy of the GNU Library General Public
#License along with this library; if not, write to the Free
#Software Foundation, Inc., 59 Temple Place - Suite 330, Boston,
#MA 02111-1307, USA

from fileauth import DAVAuthHandler

class MySQLAuthHandler(DAVAuthHandler):
    """
    Provides authentication based on a mysql table
    """

    def get_userinfo(self,user,pw,command):
        """ authenticate user """

        # Commands that need write access
        nowrite=['OPTIONS','PROPFIND','GET']

        Mysql=self._config.MySQL
        DB=Mconn(Mysql.user,Mysql.passwd,Mysql.host,Mysql.port,Mysql.dbtable)
        if self.verbose:
            print >>sys.stderr,user,command

        qry="select * from %s.Users where User='%s' and Pass='%s'"%(Mysql.dbtable,user,pw)
        Auth=DB.execute(qry)

        if len(Auth) == 1:
            can_write=Auth[0][3]
            if not can_write and not command in nowrite:
                self._log('Authentication failed for user %s using command %s' %(user,command))
                return 0
            else:
                self._log('Successfully authenticated user %s writable=%s' % (user,can_write))
                return 1
        else:
            self._log('Authentication failed for user %s' % user)
            return 0

        self._log('Authentication failed for user %s' % user)
        return 0

